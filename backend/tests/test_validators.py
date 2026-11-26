"""Tests for backend/app/validators.py."""

import io  # gives us BytesIO, a file that lives in memory

import numpy as np  # numpy: used to build noisy test images that do not compress to almost nothing
import pytest  # the testing framework
from PIL import Image  # Pillow: used to create small test images

from app.config import Settings  # the settings object we pass to the validators
from app.validators import UploadError, validate_content_type, validate_image, validate_upload  # the code we are testing


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


@pytest.mark.parametrize("image_format, suffix", [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")])  # run once for each allowed format
def test_valid_images_are_accepted(image_format, suffix):  # every allowed format must pass
    result = validate_image(make_image_bytes(image_format), Settings())  # validate a real image of this format
    assert result.image_format == image_format  # the real format is reported
    assert (result.width, result.height) == (30, 20)  # the size is reported
    assert result.suffix == suffix  # the matching file ending is reported


def test_empty_file_is_rejected():  # zero bytes must be refused
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(b"", Settings())  # validate an empty upload
    assert info.value.status_code == 400  # empty means a bad request


def test_oversized_file_is_rejected():  # a file over the byte limit must be refused
    data = make_image_bytes(noisy=True, size=(50, 50))  # a noisy image of several kilobytes
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(data, Settings(max_upload_bytes=1000))  # a limit of only 1000 bytes
    assert info.value.status_code == 413  # too large


def test_too_many_pixels_is_rejected():  # a picture with too many pixels must be refused
    data = make_image_bytes(size=(20, 20))  # a 400-pixel image
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(data, Settings(max_image_pixels=100))  # a limit of only 100 pixels
    assert info.value.status_code == 413  # too large


def test_pdf_is_rejected():  # a PDF must be refused, as the spec says
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(b"%PDF-1.4\n%fake pdf content\n", Settings())  # bytes that start like a PDF
    assert info.value.status_code == 415  # unsupported type


def test_plain_text_is_rejected():  # a text file renamed to .jpg must be refused
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(b"hello, this is not an image", Settings())  # plain text bytes
    assert info.value.status_code == 415  # unsupported type


def test_other_image_format_is_rejected():  # a real GIF is an image, but not an allowed format
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(make_image_bytes("GIF"), Settings())  # a genuine GIF file
    assert info.value.status_code == 415  # unsupported format
    assert "GIF" in info.value.message  # the message names the format


def test_truncated_image_is_rejected():  # a file cut off halfway must be refused as damaged
    data = make_image_bytes(noisy=True, size=(64, 64))  # a valid PNG with plenty of data
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_image(data[: len(data) // 2], Settings())  # keep only the first half of the file
    assert info.value.status_code == 400  # damaged means a bad request


@pytest.mark.parametrize("content_type", ["image/jpeg", "image/png", "image/webp", None, "image/PNG; charset=binary"])  # run once for each acceptable value
def test_acceptable_content_types_pass(content_type):  # these announced types must not raise
    validate_content_type(content_type, Settings())  # no error means the check passed


@pytest.mark.parametrize("content_type", ["application/pdf", "text/plain", "application/octet-stream"])  # run once for each rejected value
def test_unacceptable_content_types_are_rejected(content_type):  # these announced types must raise
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_content_type(content_type, Settings())  # check the announced type
    assert info.value.status_code == 415  # unsupported type


def test_validate_upload_accepts_a_good_upload():  # the full check must accept a normal image
    result = validate_upload(make_image_bytes("PNG"), "image/png", Settings())  # a real PNG announced as a PNG
    assert result.image_format == "PNG"  # the real format is reported


def test_validate_upload_rejects_bad_content_type_first():  # a wrong announced type is refused even for a good image
    with pytest.raises(UploadError) as info:  # the test passes only if an UploadError is raised
        validate_upload(make_image_bytes("PNG"), "application/pdf", Settings())  # a real PNG announced as a PDF
    assert info.value.status_code == 415  # unsupported type