"""The web routes of the OCR backend."""

import logging  # Python's standard way to write log messages
import tempfile  # makes private temporary folders that are deleted automatically
import time  # used to measure how long a request takes
from pathlib import Path  # makes working with file paths simple and safe

from fastapi import APIRouter, File, Request, UploadFile  # APIRouter groups routes; File and UploadFile receive uploaded files
from fastapi.concurrency import run_in_threadpool  # runs slow, blocking work in a separate thread

from app.ocr_engine import OcrEngine  # the type of engine this module expects
from app.validators import UploadError, validate_content_type, validate_image  # the upload checks from Step 62

logger = logging.getLogger(__name__)  # a logger named after this file
router = APIRouter()  # the group of routes that main.py adds to the application

LANGUAGE = "Kannada"  # the language this service reads
NO_TEXT_MESSAGE = "No text was found in this image."  # shown when the engine finds nothing


@router.get("/health")  # answers GET requests sent to /health
async def health(request: Request) -> dict[str, object]:  # returns a small dictionary, which FastAPI turns into JSON
    """Report that the service is running and whether the OCR models are loaded yet."""
    engine = request.app.state.engine  # the OCR engine that create_app stored on the application
    return {"status": "ok", "model_loaded": engine.is_loaded}  # is_loaded never waits, so this answers at once


def _read_image_text(engine: OcrEngine, data: bytes, suffix: str) -> str:  # writes the upload to a temporary file and reads it
    """Write the upload to a private temporary file, read it with the engine, and always delete the file."""
    with tempfile.TemporaryDirectory(prefix="kannada-ocr-") as folder:  # a new private folder, removed when this block ends, even after an error
        path = Path(folder) / f"upload{suffix}"  # the file name uses the real image format, never the name the client sent
        path.write_bytes(data)  # save the uploaded bytes into the temporary file
        return engine.read_text(path)  # let the engine read it; the folder is deleted right after this line finishes


@router.post("/api/ocr")  # answers POST requests sent to /api/ocr
async def extract_text(request: Request, file: UploadFile | None = File(default=None)) -> dict[str, object]:  # receives one uploaded file in the form field "file"
    """Check the uploaded image, read its text with the OCR engine, and return the text."""
    settings = request.app.state.settings  # the settings that create_app stored on the application
    engine = request.app.state.engine  # the OCR engine that create_app stored on the application
    if file is None:  # the request had no file in the "file" field
        raise UploadError(400, "No file was uploaded. Send an image in the form field named 'file'.")  # reject with a clear message

    started = time.perf_counter()  # note the time when we begin
    validate_content_type(file.content_type, settings)  # cheap check on the announced type, before reading the body
    data = await file.read(settings.max_upload_bytes + 1)  # read at most one byte more than the limit, so huge uploads are never read in full
    await file.close()  # release the uploaded file's resources
    validated = await run_in_threadpool(validate_image, data, settings)  # check the real content in a separate thread, because decoding takes a moment
    text = await run_in_threadpool(_read_image_text, engine, data, validated.suffix)  # read the text in a separate thread, so /health keeps answering
    seconds = round(time.perf_counter() - started, 2)  # how long the whole request took, in seconds

    logger.info("OCR finished in %.2f s, %d characters", seconds, len(text))  # log only numbers, never the image or the text
    response: dict[str, object] = {  # the answer in the shape your spec asks for
        "success": True,  # the request worked
        "extracted_text": text,  # the text found, exactly as the engine returned it
        "processing_time": seconds,  # seconds the request took
        "language": LANGUAGE,  # the language this service reads
    }
    if not text.strip():  # the engine found nothing, or only blanks
        response["message"] = NO_TEXT_MESSAGE  # say so honestly instead of leaving the user guessing
    return response  # FastAPI turns this dictionary into JSON