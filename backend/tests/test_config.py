"""Tests for backend/app/config.py."""

import dataclasses  # used to check that the settings cannot be changed

import pytest  # the testing framework, used here for error checks and repeated cases

from app.config import MEGABYTE, Settings, get_settings  # the code we are testing


@pytest.fixture(autouse=True)  # runs before every test in this file, automatically
def clean_environment(monkeypatch):  # monkeypatch lets a test change environment variables safely
    monkeypatch.delenv("MAX_UPLOAD_MB", raising=False)  # make sure the upload limit variable is not set
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)  # make sure the origins variable is not set


def test_defaults():  # with nothing set, the safe defaults must be used
    settings = get_settings()  # build the settings
    assert settings.max_upload_bytes == 10 * MEGABYTE  # the default limit is 10 MB
    assert settings.allowed_origins == ("http://localhost:3000",)  # the default allowed website
    assert "image/jpeg" in settings.allowed_mime_types  # JPEG is accepted
    assert "application/pdf" not in settings.allowed_mime_types  # PDF is not accepted, as the spec says
    assert "PDF" not in settings.allowed_image_formats  # PDF is not accepted as a format either


def test_max_upload_can_be_changed(monkeypatch):  # the environment variable must change the limit
    monkeypatch.setenv("MAX_UPLOAD_MB", "3")  # pretend the variable is set to 3
    assert get_settings().max_upload_bytes == 3 * MEGABYTE  # the limit is now 3 MB


@pytest.mark.parametrize("bad_value", ["abc", "0", "-5", "2.5"])  # run this test once for each bad value
def test_invalid_upload_limit_is_rejected(monkeypatch, bad_value):  # bad values must stop the program
    monkeypatch.setenv("MAX_UPLOAD_MB", bad_value)  # set the variable to the bad value
    with pytest.raises(ValueError, match="MAX_UPLOAD_MB"):  # the test passes only if an error naming the variable is raised
        get_settings()  # try to build the settings


def test_empty_upload_limit_falls_back_to_default(monkeypatch):  # an empty variable counts as not set
    monkeypatch.setenv("MAX_UPLOAD_MB", "")  # set the variable to an empty string
    assert get_settings().max_upload_bytes == 10 * MEGABYTE  # the default limit is used


def test_origins_are_split_and_trimmed(monkeypatch):  # a comma-separated list must become a clean tuple
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example.com, https://b.example.com ,")  # two addresses, with stray spaces and a trailing comma
    assert get_settings().allowed_origins == ("https://a.example.com", "https://b.example.com")  # spaces and the empty piece are gone


def test_empty_origins_fall_back_to_default(monkeypatch):  # a list with nothing usable must use the default
    monkeypatch.setenv("ALLOWED_ORIGINS", " , ,")  # only spaces and commas
    assert get_settings().allowed_origins == ("http://localhost:3000",)  # the default list is used


def test_settings_cannot_be_changed_after_creation():  # frozen settings must refuse changes
    settings = Settings()  # create the default settings
    with pytest.raises(dataclasses.FrozenInstanceError):  # the test passes only if this error is raised
        settings.max_upload_bytes = 1  # try to change a setting