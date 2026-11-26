"""Settings for the OCR backend: safe defaults that environment variables can override."""

import os  # reads environment variables, which are settings given from outside the program
from dataclasses import dataclass  # a simple way to define a group of related settings

MEGABYTE = 1024 * 1024  # the number of bytes in one megabyte


@dataclass(frozen=True)  # frozen means the settings cannot be changed after they are created
class Settings:  # one object that holds every setting
    """All backend settings in one place."""

    max_upload_bytes: int = 10 * MEGABYTE  # the largest file we accept: 10 MB unless changed
    max_image_pixels: int = 40_000_000  # the largest picture we accept, as width x height (guards against huge files)
    allowed_mime_types: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})  # the file types a browser may announce
    allowed_image_formats: frozenset[str] = frozenset({"JPEG", "PNG", "WEBP"})  # the formats Pillow may find inside the file (no PDF)
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)  # websites allowed to call this backend (CORS)


def _positive_int_from_env(name: str, default: int) -> int:  # reads one environment variable as a positive whole number
    """Return the environment variable as a positive integer, or the default if it is not set."""
    raw = os.environ.get(name, "").strip()  # the variable's text, or an empty string if it is not set
    if not raw:  # not set, or set to nothing
        return default  # use the default value
    try:  # try to turn the text into a whole number
        value = int(raw)  # for example "3" becomes 3
    except ValueError as error:  # the text was not a whole number, for example "abc" or "2.5"
        raise ValueError(f"{name} must be a positive whole number") from error  # stop with a clear message
    if value <= 0:  # zero or negative makes no sense for a limit
        raise ValueError(f"{name} must be a positive whole number")  # stop with a clear message
    return value  # the value is valid, so hand it back


def get_settings() -> Settings:  # builds the settings from the defaults plus any environment variables
    """Create the settings, applying MAX_UPLOAD_MB and ALLOWED_ORIGINS if they are set."""
    max_mb = _positive_int_from_env("MAX_UPLOAD_MB", 10)  # the upload limit in megabytes, default 10
    raw_origins = os.environ.get("ALLOWED_ORIGINS", "")  # a comma-separated list of website addresses, or empty
    origins = tuple(item.strip() for item in raw_origins.split(",") if item.strip())  # split on commas, trim spaces, drop empty pieces
    if not origins:  # nothing usable was given
        origins = Settings().allowed_origins  # fall back to the default list
    return Settings(max_upload_bytes=max_mb * MEGABYTE, allowed_origins=origins)  # build the settings; everything else keeps its default