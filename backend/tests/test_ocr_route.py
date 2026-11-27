"""Tests for POST /api/ocr. They use a fake engine, so no models are loaded."""
import logging  # lets the test look at the log messages the service writes
import io  # gives us BytesIO, a file that lives in memory
import tempfile  # lets us point temporary files at a folder the test controls
from pathlib import Path  # makes working with file paths simple and safe

import numpy as np  # numpy: used to build noisy test images that do not compress to almost nothing
import pytest  # the testing framework
from fastapi.testclient import TestClient  # a fake browser that calls the application directly
from PIL import Image  # Pillow: used to create small test images

from app.config import Settings  # the settings object we pass to the application
from app.main import create_app  # the function that builds the application
from app.ocr_engine import OcrEngineError  # the error our engine raises when it fails


class RecordingEngine:  # a fake engine that records what it was given
    def __init__(self, text: str = "ಕನ್ನಡ ಪಠ್ಯ", error: Exception | None = None) -> None:  # what to return, and what to raise
        self.text = text  # the text the fake "reads"
        self.error = error  # an error to raise, or None
        self.paths: list[Path] = []  # every path the engine was asked to read
        self.existed_during_read: list[bool] = []  # whether each file existed while being read
        self.contents: list[bytes] = []  # the bytes found in each file while being read

    @property  # lets us write engine.is_loaded instead of engine.is_loaded()
    def is_loaded(self) -> bool:  # tells whether the fake models are loaded
        return True  # always ready

    def load(self) -> None:  # pretends to load the models
        return None  # nothing to do

    def read_text(self, image_path: Path) -> str:  # pretends to read an image
        self.paths.append(image_path)  # remember the path
        self.existed_during_read.append(image_path.exists())  # was the file really there?
        self.contents.append(image_path.read_bytes())  # remember what was inside it
        if self.error is not None:  # the test wants a failure
            raise self.error  # raise it
        return self.text  # hand back the prepared text


def make_image_bytes(image_format: str = "PNG", size: tuple[int, int] = (30, 20), noisy: bool = False) -> bytes:  # builds a small image file in memory
    if noisy:  # a random-noise picture, which gives a larger file
        rng = np.random.default_rng(0)  # a random number generator with a fixed seed, so the test is repeatable
        pixels = rng.integers(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)  # random colours: height rows, width columns
        image = Image.fromarray(pixels)  # turn the numbers into a Pillow image
    else:  # a plain picture
        image = Image.new("RGB", size, (10, 200, 30))  # one flat green colour
    buffer = io.BytesIO()  # an empty in-memory file
    image.save(buffer, format=image_format)  # write the image into it in the requested format
    return buffer.getvalue()  # hand back the raw bytes


def make_client(engine: RecordingEngine, settings: Settings | None = None) -> TestClient:  # builds a test client around a fresh application
    app = create_app(settings=settings or Settings(), engine=engine, preload=False)  # no background loading in these tests
    return TestClient(app)  # wrap it in the fake browser


def post_file(client: TestClient, data: bytes, filename: str = "photo.png", content_type: str = "image/png", field: str = "file"):  # sends one upload
    return client.post("/api/ocr", files={field: (filename, data, content_type)})  # a multipart form with one file in it


@pytest.fixture()  # a helper that tests can ask for by name
def temp_dir(tmp_path, monkeypatch) -> Path:  # makes the application put its temporary files into a folder the test can inspect
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))  # tell Python to create temporary folders inside tmp_path
    return tmp_path  # hand the folder to the test


def test_successful_upload_returns_the_spec_shape():  # the normal case
    client = make_client(RecordingEngine(text="ಕರ್ನಾಟಕ"))  # an engine that "reads" this text
    response = post_file(client, make_image_bytes())  # upload a valid image
    assert response.status_code == 200  # the request worked
    body = response.json()  # the JSON answer
    assert body["success"] is True  # success is true
    assert body["extracted_text"] == "ಕರ್ನಾಟಕ"  # the text is returned
    assert body["language"] == "Kannada"  # the language is named
    assert isinstance(body["processing_time"], float) and body["processing_time"] >= 0  # a time in seconds
    assert "message" not in body  # no warning when text was found


def test_kannada_text_comes_back_exactly(temp_dir):  # conjuncts and invisible joiners must not be altered
    text = "ಕರ್ನಾಟಕ ಎಲೆಕ್ಷನ್\u200c ಸತ್ಯುಲಂ\nಎರಡನೇ ಸಾಲು"  # conjuncts, a ZWNJ character and a line break
    client = make_client(RecordingEngine(text=text))  # an engine that "reads" this text
    response = post_file(client, make_image_bytes())  # upload a valid image
    assert response.json()["extracted_text"] == text  # the text is identical, character for character


def test_temporary_file_exists_while_reading_and_is_deleted_afterwards(temp_dir):  # the spec says uploads are never kept
    engine = RecordingEngine()  # a fake engine that records what it saw
    client = make_client(engine)  # an application using it
    data = make_image_bytes("PNG")  # a real PNG
    post_file(client, data, filename="holiday.jpg", content_type="image/png")  # the client calls it a .jpg, but the content is a PNG
    assert engine.existed_during_read == [True]  # the file was there while the engine read it
    assert engine.contents == [data]  # and it held exactly the uploaded bytes
    assert engine.paths[0].suffix == ".png"  # the suffix follows the real format, not the name the client sent
    assert "holiday" not in engine.paths[0].name  # the client's file name is never used
    assert not engine.paths[0].exists()  # the file is gone afterwards
    assert list(temp_dir.iterdir()) == []  # and no temporary folder is left behind


def test_temporary_file_is_deleted_even_when_the_engine_fails(temp_dir):  # a failure must not leave the upload on disk
    engine = RecordingEngine(error=OcrEngineError("The OCR engine failed to read the image."))  # an engine that always fails
    response = post_file(make_client(engine), make_image_bytes())  # upload a valid image
    assert response.status_code == 500  # the failure is reported
    assert engine.existed_during_read == [True]  # the engine did receive the file
    assert list(temp_dir.iterdir()) == []  # but nothing is left behind


@pytest.mark.parametrize("empty_text", ["", "  \n "])  # run once for each kind of "nothing found"
def test_no_text_found_is_reported_honestly(empty_text):  # an empty result must not be dressed up as text
    response = post_file(make_client(RecordingEngine(text=empty_text)), make_image_bytes())  # the engine finds nothing
    body = response.json()  # the JSON answer
    assert response.status_code == 200  # the request itself worked
    assert body["success"] is True  # the OCR ran
    assert body["extracted_text"] == empty_text  # nothing is invented
    assert body["message"] == "No text was found in this image."  # and the user is told


def test_engine_failure_returns_a_plain_error():  # internal details must not reach the user
    engine = RecordingEngine(error=OcrEngineError("The OCR engine failed to read the image."))  # an engine that always fails
    response = post_file(make_client(engine), make_image_bytes())  # upload a valid image
    assert response.status_code == 500  # server error
    assert response.json() == {"success": False, "error": "The OCR engine failed to read the image."}  # the usual error shape


def test_missing_file_is_rejected():  # a request with no file at all
    engine = RecordingEngine()  # a fake engine that records its calls
    response = make_client(engine).post("/api/ocr")  # send a request with no body
    assert response.status_code == 400  # bad request
    assert response.json()["success"] is False  # the usual error shape
    assert engine.paths == []  # the engine was never used


def test_file_in_the_wrong_form_field_is_rejected():  # the file must be in the field named "file"
    engine = RecordingEngine()  # a fake engine that records its calls
    response = post_file(make_client(engine), make_image_bytes(), field="image")  # the file is sent under another name
    assert response.status_code == 400  # bad request
    assert engine.paths == []  # the engine was never used


def test_empty_file_is_rejected():  # zero bytes
    engine = RecordingEngine()  # a fake engine that records its calls
    response = post_file(make_client(engine), b"")  # upload an empty file
    assert response.status_code == 400  # bad request
    assert engine.paths == []  # the engine was never used


def test_pdf_is_rejected():  # the spec says no PDFs
    engine = RecordingEngine()  # a fake engine that records its calls
    response = post_file(make_client(engine), b"%PDF-1.4\n%fake\n", filename="paper.pdf", content_type="application/pdf")  # upload a PDF
    assert response.status_code == 415  # unsupported type
    assert response.json()["success"] is False  # the usual error shape
    assert engine.paths == []  # the engine was never used


def test_text_file_pretending_to_be_an_image_is_rejected():  # the content decides, not the announced type
    engine = RecordingEngine()  # a fake engine that records its calls
    response = post_file(make_client(engine), b"this is just text", filename="photo.png", content_type="image/png")  # text announced as a PNG
    assert response.status_code == 415  # unsupported type
    assert engine.paths == []  # the engine was never used


def test_oversized_upload_is_rejected():  # a file over the limit
    engine = RecordingEngine()  # a fake engine that records its calls
    client = make_client(engine, settings=Settings(max_upload_bytes=1000))  # a limit of only 1000 bytes
    response = post_file(client, make_image_bytes(noisy=True, size=(50, 50)))  # upload a noisy image of several kilobytes
    assert response.status_code == 413  # too large
    assert engine.paths == []  # the engine was never used


def test_gif_is_rejected():  # a real image, but not an allowed format
    engine = RecordingEngine()  # a fake engine that records its calls
    response = post_file(make_client(engine), make_image_bytes("GIF"), filename="a.gif", content_type="image/png")  # a GIF announced as a PNG
    assert response.status_code == 415  # unsupported format
    assert engine.paths == []  # the engine was never used


def test_truncated_image_is_rejected():  # a damaged file
    engine = RecordingEngine()  # a fake engine that records its calls
    data = make_image_bytes(noisy=True, size=(64, 64))  # a valid PNG with plenty of data
    response = post_file(make_client(engine), data[: len(data) // 2])  # keep only the first half
    assert response.status_code == 400  # bad request
    assert engine.paths == []  # the engine was never used


def test_get_is_not_allowed_on_the_ocr_route():  # only POST is accepted
    response = make_client(RecordingEngine()).get("/api/ocr")  # try a GET request
    assert response.status_code == 405  # method not allowed


def test_plain_text_in_the_file_field_gets_a_consistent_error():  # a malformed request must not produce a differently shaped error
    response = make_client(RecordingEngine()).post("/api/ocr", data={"file": "just text"})  # send ordinary text in the "file" field
    assert response.status_code in (400, 422)  # either kind of "bad request" is acceptable
    assert response.json()["success"] is False  # and the error has our usual shape



def test_log_line_has_the_timing_but_never_the_text(caplog):  # logs must never contain what the user uploaded
    secret = "ರಹಸ್ಯ ಪಠ್ಯ"  # a recognisable piece of "extracted" text
    client = make_client(RecordingEngine(text=secret))  # an engine that "reads" it
    with caplog.at_level(logging.INFO, logger="app.routes"):  # record the messages written by routes.py
        post_file(client, make_image_bytes())  # upload a valid image
    messages = [record.getMessage() for record in caplog.records if record.name == "app.routes"]  # the texts of those messages
    assert any("OCR finished" in message for message in messages)  # the timing line was written
    assert all(secret not in message for message in messages)  # and the extracted text never appears in a log line