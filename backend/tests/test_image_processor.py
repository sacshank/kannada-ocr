"""Tests for backend/app/image_processor.py."""

import cv2  # OpenCV: used here to measure contrast in the tests
import numpy as np  # numpy: used to build small test images as arrays
import pytest  # the testing framework, used here to check that errors are raised
from PIL import Image  # Pillow: used to create small test images
from app.image_processor import enhance_contrast, load_image, read_dpi, resize_image, save_image  # the functions we are testing

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



def test_read_dpi_returns_stored_value(tmp_path):  # a file saved with a DPI must report it
    path = tmp_path / "with_dpi.png"  # where the test image will be saved
    Image.new("RGB", (10, 10)).save(path, dpi=(96, 96))  # save a small image with 96 DPI stored
    dpi = read_dpi(path)  # read the DPI back
    assert dpi is not None  # a value must be found
    assert dpi[0] == pytest.approx(96, abs=1)  # PNG stores DPI in rounded units, so allow a tiny difference
    assert dpi[1] == pytest.approx(96, abs=1)  # the same check for the vertical value


def test_read_dpi_returns_none_when_missing(tmp_path):  # a file saved without DPI must report None
    path = tmp_path / "no_dpi.png"  # where the test image will be saved
    Image.new("RGB", (10, 10)).save(path)  # save a small image with no DPI information
    assert read_dpi(path) is None  # nothing stored, so None is expected


def test_read_dpi_rejects_missing_file(tmp_path):  # a path that does not exist must raise an error
    with pytest.raises(ValueError):  # the test passes only if a ValueError is raised
        read_dpi(tmp_path / "missing.png")  # try to read a file that was never created


def test_save_image_round_trip_keeps_pixels_and_dpi(tmp_path):  # saving then loading must change nothing
    original = np.zeros((20, 30, 3), dtype=np.uint8)  # a black image: 20 tall, 30 wide, 3 colours
    original[5, 7] = (10, 20, 30)  # one pixel with distinct blue, green and red values
    path = tmp_path / "saved.png"  # where the image will be saved
    save_image(original, path, dpi=(150, 150))  # save it with 150 DPI
    assert np.array_equal(load_image(path), original)  # the pixels must come back exactly the same
    dpi = read_dpi(path)  # read the DPI back
    assert dpi is not None  # a value must be found
    assert dpi[0] == pytest.approx(150, abs=1)  # PNG stores DPI in rounded units, so allow a tiny difference


def test_save_image_without_dpi_stores_none(tmp_path):  # no DPI given means none stored
    path = tmp_path / "saved.png"  # where the image will be saved
    save_image(np.zeros((10, 10, 3), dtype=np.uint8), path)  # save a small black image without DPI
    assert read_dpi(path) is None  # nothing was stored, so None is expected



def test_enhance_contrast_keeps_shape_and_type():  # the output must have the same size and pixel type as the input
    image = np.full((30, 40, 3), 128, dtype=np.uint8)  # a flat grey image: 30 tall, 40 wide, 3 colours
    result = enhance_contrast(image)  # boost its contrast
    assert result.shape == image.shape  # same height, width and colour channels
    assert result.dtype == np.uint8  # pixels are still 8-bit numbers


def test_enhance_contrast_increases_contrast_of_flat_image():  # a dull image must become more contrasty
    rng = np.random.default_rng(0)  # a random number generator with a fixed seed, so the test gives the same result every time
    image = rng.integers(100, 140, size=(64, 64, 3), dtype=np.uint8)  # noise with all values squeezed between 100 and 140
    before = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).std()  # how spread out the brightness values are before
    after = cv2.cvtColor(enhance_contrast(image), cv2.COLOR_BGR2GRAY).std()  # and after the boost
    assert after > before  # a larger spread means higher contrast


def test_enhance_contrast_does_not_modify_input():  # the original image array must stay untouched
    rng = np.random.default_rng(1)  # a random number generator with a fixed seed
    image = rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)  # a random colour image
    copy = image.copy()  # keep a copy to compare against afterwards
    enhance_contrast(image)  # run the function and ignore its result
    assert np.array_equal(image, copy)  # the input must be exactly as before


def test_enhance_contrast_rejects_invalid_input():  # bad arguments must raise an error
    colour = np.zeros((10, 10, 3), dtype=np.uint8)  # a small black colour image
    with pytest.raises(ValueError):  # the test passes only if a ValueError is raised
        enhance_contrast(np.zeros((10, 10), dtype=np.uint8))  # a grayscale image has no third channel
    with pytest.raises(ValueError):  # the same kind of check
        enhance_contrast(colour, clip_limit=0)  # a zero clip limit is not allowed
    with pytest.raises(ValueError):  # the same kind of check
        enhance_contrast(colour, tile_size=0)  # a tile size of zero is not allowed