"""Checks that decide whether an uploaded file is an acceptable image."""

from dataclasses import dataclass  # a simple way to define a small group of related values
from io import BytesIO  # lets Pillow read an image from bytes held in memory instead of from a file

from PIL import Image, UnidentifiedImageError  # Pillow: looks inside the file to find out what it really is

from app.config import MEGABYTE, Settings  # the limits and allowed types from Step 60

FORMAT_SUFFIXES = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}  # the file ending to use for each image format


class UploadError(Exception):  # the one error type for every rejected upload
    """A rejected upload: carries the web status code and a message safe to show to the user."""

    def __init__(self, status_code: int, message: str) -> None:  # create the error with a code and a message
        super().__init__(message)  # also store the message in the standard way
        self.status_code = status_code  # the HTTP status code the API should answer with
        self.message = message  # the text to show to the user


@dataclass(frozen=True)  # frozen means the values cannot be changed after they are created
class ValidatedImage:  # what we learn about an upload that passed every check
    """Facts about an image that passed validation."""

    image_format: str  # the real format found inside the file: JPEG, PNG or WEBP
    width: int  # width in pixels
    height: int  # height in pixels

    @property  # lets us write image.suffix instead of image.suffix()
    def suffix(self) -> str:  # the file ending that matches the real format
        return FORMAT_SUFFIXES.get(self.image_format, ".img")  # for example ".png", or ".img" for an unknown format


def validate_content_type(content_type: str | None, settings: Settings) -> None:  # checks the type announced by the client
    """Reject a announced file type that is not allowed. A missing type is accepted; the content check decides."""
    if not content_type:  # the client did not announce a type
        return  # nothing to check here
    announced = content_type.split(";")[0].strip().lower()  # drop extras like "; charset=..." and ignore capital letters
    if announced not in settings.allowed_mime_types:  # the type is not on the allowed list
        raise UploadError(415, "Unsupported file type. Please upload a JPG, PNG or WEBP image.")  # reject with a clear message


def validate_image(data: bytes, settings: Settings) -> ValidatedImage:  # checks the file content itself
    """Check the bytes of an upload and return facts about the image, or raise UploadError."""
    if not data:  # no bytes at all
        raise UploadError(400, "The uploaded file is empty.")  # reject with a clear message
    if len(data) > settings.max_upload_bytes:  # more bytes than the limit allows
        limit_mb = settings.max_upload_bytes / MEGABYTE  # the limit expressed in megabytes
        raise UploadError(413, f"The file is larger than the {limit_mb:g} MB limit.")  # reject with the limit in the message

    try:  # try to open the file as an image; this reads only the header, not all the pixels
        image = Image.open(BytesIO(data))  # let Pillow look inside the bytes
    except Image.DecompressionBombError as error:  # Pillow's own protection against absurdly large pictures
        raise UploadError(413, "The image has too many pixels.") from error  # reject with a clear message
    except UnidentifiedImageError as error:  # Pillow could not recognise the content as an image at all
        raise UploadError(415, "The file is not a supported image. Please upload a JPG, PNG or WEBP image.") from error  # for example text or a PDF
    except (OSError, ValueError, SyntaxError) as error:  # the header was recognised but is broken
        raise UploadError(400, "The image file is damaged and cannot be read.") from error  # reject with a clear message

    with image:  # make sure the image is closed when we are finished with it
        image_format = image.format  # the real format found inside the file, such as "JPEG" or "GIF"
        if image_format not in settings.allowed_image_formats:  # a real image, but not an allowed format
            raise UploadError(415, f"Unsupported image format ({image_format}). Please upload a JPG, PNG or WEBP image.")  # name the format in the message
        width, height = image.size  # the size in pixels, read from the header
        if width * height > settings.max_image_pixels:  # too many pixels for us to process safely
            raise UploadError(413, "The image has too many pixels.")  # reject before decoding anything
        try:  # now read every pixel, which also reveals damaged or cut-short files
            image.load()  # decode the whole image
        except Image.DecompressionBombError as error:  # the picture turned out to be absurdly large
            raise UploadError(413, "The image has too many pixels.") from error  # reject with a clear message
        except Exception as error:  # any other decoding problem means the file is damaged
            raise UploadError(400, "The image file is damaged and cannot be read.") from error  # reject with a clear message

    return ValidatedImage(image_format=image_format, width=width, height=height)  # everything passed


def validate_upload(data: bytes, content_type: str | None, settings: Settings) -> ValidatedImage:  # runs every check in order
    """Run the announced-type check, then the content checks, and return facts about the image."""
    validate_content_type(content_type, settings)  # first the cheap check on the announced type
    return validate_image(data, settings)  # then the checks on the real content