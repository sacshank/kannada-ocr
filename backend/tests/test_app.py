"""Tests for backend/app/main.py and the /health route. They use a fake engine, so no models are loaded."""

import time  # used to wait a moment for the background loading thread
from pathlib import Path  # type hint for the fake engine's method

from fastapi.testclient import TestClient  # a fake browser that calls the application directly

from app.config import Settings  # the settings object we pass to the application
from app.main import create_app  # the function we are testing


class FakeEngine:  # a stand-in for the real OCR engine
    def __init__(self) -> None:  # create the fake in its "not loaded" state
        self.loaded = False  # the fake starts without models

    @property  # lets us write engine.is_loaded instead of engine.is_loaded()
    def is_loaded(self) -> bool:  # tells whether the fake models are loaded
        return self.loaded  # the stored state

    def load(self) -> None:  # pretends to load the models
        self.loaded = True  # now they are loaded

    def read_text(self, image_path: Path) -> str:  # pretends to read an image
        return ""  # not used in this step


def make_client(engine=None, settings=None, preload=False) -> TestClient:  # builds a test client around a fresh application
    app = create_app(settings=settings or Settings(), engine=engine or FakeEngine(), preload=preload)  # background loading is off unless a test asks for it
    return TestClient(app)  # wrap it in the fake browser


def test_health_reports_ok_and_model_not_loaded():  # a fresh service is up but has no models yet
    response = make_client().get("/health")  # ask the health route
    assert response.status_code == 200  # the request succeeded
    assert response.json() == {"status": "ok", "model_loaded": False}  # up, but not loaded


def test_health_reports_model_loaded():  # once the engine is loaded, health says so
    engine = FakeEngine()  # a fake engine
    engine.load()  # load it
    response = make_client(engine=engine).get("/health")  # ask the health route
    assert response.json() == {"status": "ok", "model_loaded": True}  # up and loaded


def test_cors_allows_the_configured_origin():  # the default frontend address may call us
    response = make_client().get("/health", headers={"Origin": "http://localhost:3000"})  # pretend to be a page on that address
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"  # the browser is told it may read the answer


def test_cors_does_not_allow_other_origins():  # any other website must not be allowed
    response = make_client().get("/health", headers={"Origin": "https://evil.example.com"})  # pretend to be a page on another site
    assert "access-control-allow-origin" not in response.headers  # the browser is not given permission


def test_cors_origins_come_from_settings():  # a changed setting must change who is allowed
    settings = Settings(allowed_origins=("https://ocr.example.com",))  # a different allowed address
    client = make_client(settings=settings)  # build the application with it
    allowed = client.get("/health", headers={"Origin": "https://ocr.example.com"})  # the configured address
    refused = client.get("/health", headers={"Origin": "http://localhost:3000"})  # the old default address
    assert allowed.headers.get("access-control-allow-origin") == "https://ocr.example.com"  # the new address is allowed
    assert "access-control-allow-origin" not in refused.headers  # the old default is no longer allowed


def test_models_are_preloaded_in_the_background():  # starting the server must start loading the models
    engine = FakeEngine()  # a fake engine that is not loaded
    with make_client(engine=engine, preload=True):  # the "with" block runs the application's startup code
        for _ in range(50):  # wait up to about 2.5 seconds for the background thread
            if engine.is_loaded:  # the thread has finished loading
                break  # stop waiting
            time.sleep(0.05)  # wait a little and check again
        assert engine.is_loaded  # the models were loaded without any request


def test_preload_can_be_switched_off():  # with preload off, nothing is loaded at startup
    engine = FakeEngine()  # a fake engine that is not loaded
    with make_client(engine=engine, preload=False):  # run the startup code
        assert engine.is_loaded is False  # nothing was loaded


def test_unknown_path_returns_404():  # a path that does not exist must not crash the service
    response = make_client().get("/does-not-exist")  # ask for a path we never defined
    assert response.status_code == 404  # not found