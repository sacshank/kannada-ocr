"""Tests for backend/app/image_processor.py."""

import numpy as np  # numpy: used to build small test images as arrays
import pytest  # the testing framework, used here to check that errors are raised
from PIL import Image  # Pillow: used to create small test images

from app.image_processor import load_image, resize_image  # the functions we are testing


def test_load_image_returns_bgr_array(tmp_path):  # tmp_path is a temporary folder that pytest creates and deletes
    path = tmp_path / "red.png"  # where the test image will be saved
    Image.new("RGB", (40, 20), (255, 0, 0)).save(path)  # create a 40 wide, 20 tall, pure red image and save it
    image = load_image(path)  # load it with our function
    assert image.shape == (20, 40, 3)  # numpy shape is (height, width, colours)
    assert tuple(image[0, 0]) == (0, 0, 255)  # red in OpenCV's blue-green-red order is (0, 0, 255)


def test_load_image_applies_exif_rotation(tmp_path):  # a sideways photo must come out upright
    path = tmp_path / "sideways.jpg"  # where the test image will be saved
    exif = Image.Exif()  # an empty metadata block
    exif[0x0112] = 6  # tag 0x0112 is "orientation"; value 6 means "rotate a quarter turn to show it upright"
    Image.new("RGB", (40, 20), (255, 255, 255)).save(path, exif=exif)  # save a 40x20 image with that tag
    image = load_image(path)  # load it with our function
    assert image.shape[:2] == (40, 20)  # after the turn, the height is 40 and the width is 20


def test_load_image_rejects_non_image_file(tmp_path):  # a file that is not an image must raise an error
    path = tmp_path / "broken.jpg"  # a file with an image extension but no image inside
    path.write_bytes(b"this is not an image")  # fill it with plain text bytes
    with pytest.raises(ValueError):  # the test passes only if a ValueError is raised
        load_image(path)  # try to load the broken file


def test_load_image_rejects_missing_file(tmp_path):  # a path that does not exist must raise an error
    with pytest.raises(ValueError):  # the test passes only if a ValueError is raised
        load_image(tmp_path / "missing.png")  # try to load a file that was never created


def test_resize_doubles_dimensions():  # a factor of 2.0 must double both sides
    image = np.zeros((20, 40, 3), dtype=np.uint8)  # a black image: 20 tall, 40 wide, 3 colours
    result = resize_image(image, 2.0)  # enlarge it to twice the size
    assert result.shape == (40, 80, 3)  # height and width are both doubled, colours unchanged


def test_resize_halves_dimensions():  # a factor of 0.5 must halve both sides
    image = np.zeros((20, 40, 3), dtype=np.uint8)  # a black image: 20 tall, 40 wide, 3 colours
    result = resize_image(image, 0.5)  # shrink it to half the size
    assert result.shape == (10, 20, 3)  # height and width are both halved


def test_resize_keeps_pixel_type():  # resizing must not change the kind of numbers stored in the image
    image = np.full((10, 10, 3), 200, dtype=np.uint8)  # a flat grey image with 8-bit pixels
    result = resize_image(image, 3.0)  # enlarge it three times
    assert result.dtype == np.uint8  # the pixels must still be 8-bit numbers


def test_resize_rejects_invalid_factor():  # zero and negative factors must raise an error
    image = np.zeros((10, 10, 3), dtype=np.uint8)  # a small black image
    with pytest.raises(ValueError):  # the test passes only if a ValueError is raised
        resize_image(image, 0)  # a factor of zero is not allowed
    with pytest.raises(ValueError):  # the same check for a negative factor
        resize_image(image, -1.5)  # a negative factor is not allowed