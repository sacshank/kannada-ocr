"""Tests for backend/app/image_processor.py."""

import pytest  # the testing framework, used here to check that errors are raised
from PIL import Image  # Pillow: used to create small test images

from app.image_processor import load_image  # the function we are testing


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