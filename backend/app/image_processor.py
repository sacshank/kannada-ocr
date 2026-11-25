"""Image preprocessing helpers for the OCR pipeline."""

from pathlib import Path  # makes working with file paths simple and safe

import cv2  # OpenCV: the library for image operations
import numpy as np  # numpy: images are stored as arrays of numbers
from PIL import Image, ImageOps, UnidentifiedImageError  # Pillow: opens images and reads their metadata


def load_image(path: str | Path) -> np.ndarray:  # takes a file path, returns an OpenCV image array
    """Open an image file, fix its rotation, and return it as an OpenCV (BGR) array."""
    try:  # try to open the file; anything that goes wrong is handled below
        with Image.open(path) as pil_image:  # open the file with Pillow (closes automatically afterwards)
            upright = ImageOps.exif_transpose(pil_image)  # rotate the picture according to its EXIF orientation tag
            rgb = upright.convert("RGB")  # make sure the image has exactly three colour channels
            array = np.array(rgb)  # copy the pixels into a numpy array (rows, columns, colours)
    except (UnidentifiedImageError, OSError) as error:  # the file is missing, damaged, or not an image
        raise ValueError(f"Cannot read image: {path}") from error  # report one clear error type for all of these cases
    return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)  # OpenCV expects blue-green-red order, so swap the channels

    

def resize_image(image: np.ndarray, factor: float) -> np.ndarray:  # takes an image and a scale factor, returns a resized copy
    """Scale an image by a factor: 2.0 doubles its size, 0.5 halves it."""
    if factor <= 0:  # a zero or negative factor makes no sense
        raise ValueError("factor must be greater than 0")  # stop with a clear message
    height, width = image.shape[:2]  # read the current height and width in pixels
    new_width = max(1, round(width * factor))  # the new width, never less than 1 pixel
    new_height = max(1, round(height * factor))  # the new height, never less than 1 pixel
    method = cv2.INTER_CUBIC if factor > 1 else cv2.INTER_AREA  # cubic smoothing for enlarging, area averaging for shrinking
    return cv2.resize(image, (new_width, new_height), interpolation=method)  # OpenCV expects (width, height) order here



def read_dpi(path: str | Path) -> tuple[float, float] | None:  # takes a file path, returns (horizontal, vertical) DPI or None
    """Return the DPI stored in an image file, or None if the file has none."""
    try:  # try to open the file; anything that goes wrong is handled below
        with Image.open(path) as pil_image:  # open the file with Pillow (closes automatically afterwards)
            dpi = pil_image.info.get("dpi")  # the DPI pair stored in the file's metadata, if there is one
    except (UnidentifiedImageError, OSError) as error:  # the file is missing, damaged, or not an image
        raise ValueError(f"Cannot read image: {path}") from error  # report one clear error type for all of these cases
    if not dpi or len(dpi) != 2:  # nothing stored, or not a pair of numbers
        return None  # tell the caller there is no DPI information
    horizontal, vertical = float(dpi[0]), float(dpi[1])  # turn both values into plain numbers
    if horizontal <= 0 or vertical <= 0:  # a zero or negative DPI is meaningless
        return None  # treat it as missing
    return (horizontal, vertical)  # return the DPI pair


def save_image(image: np.ndarray, path: str | Path, dpi: tuple[float, float] | None = None) -> None:  # saves an OpenCV image, optionally with DPI
    """Save an OpenCV (BGR) image to a file, storing the DPI if one is given. Use a .png path."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Pillow expects red-green-blue order, so swap the channels back
    pil_image = Image.fromarray(rgb)  # turn the numpy array into a Pillow image
    if dpi is None:  # no DPI to store
        pil_image.save(path)  # save the picture as it is
    else:  # a DPI was given
        pil_image.save(path, dpi=dpi)  # save the picture and store the DPI in the file