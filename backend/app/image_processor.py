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