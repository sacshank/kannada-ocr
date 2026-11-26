"""Tests for backend/app/ocr_engine.py. They use a fake Arjuna, so no models are loaded."""

import threading  # used to run several reads at the same time in one test
import time  # used to make the fake engine take a little while
from pathlib import Path  # makes working with file paths simple and safe

import pytest  # the testing framework

from app.ocr_engine import ArjunaEngine, OcrEngineError  # the code we are testing


class FakeOcr:  # a stand-in for the real Arjuna engine
    def __init__(self, result=None, error=None, delay=0.0):  # what to return, what to raise, how long to take
        self.result = {"text": "ಕನ್ನಡ"} if result is None else result  # the structured result that page() returns
        self.error = error  # an error to raise from page(), or None
        self.delay = delay  # seconds to wait inside page()
        self.calls = []  # the paths that page() was called with
        self.active = 0  # how many page() calls are running right now
        self.max_active = 0  # the highest number of page() calls running at the same time
        self._guard = threading.Lock()  # protects the counters above

    def page(self, path):  # pretends to read an image
        with self._guard:  # update the counters safely
            self.active += 1  # one more read is running
            self.max_active = max(self.max_active, self.active)  # remember the highest number seen
        try:  # make sure the counter always goes back down
            time.sleep(self.delay)  # pretend the reading takes time
            if self.error is not None:  # the test wants a failure
                raise self.error  # raise it
            self.calls.append(path)  # remember which path we were asked to read
            return self.result  # hand back the prepared result
        finally:  # runs whether or not an error happened
            with self._guard:  # update the counters safely
                self.active -= 1  # this read has finished

    def render(self, doc, fmt):  # pretends to turn a result into plain text
        return f"rendered:{fmt}"  # a recognisable marker, so the test can see this path was used


def counting_loader(fake):  # builds a loader that counts how often it is called
    calls = {"n": 0}  # a counter kept in a dictionary so the inner function can change it

    def loader():  # the loader the engine will call
        calls["n"] += 1  # count this call
        return fake  # hand back the fake engine

    return loader, calls  # give back the loader and its counter


def test_engine_is_not_loaded_until_used():  # creating the engine must not start the models
    loader, calls = counting_loader(FakeOcr())  # a loader with a counter
    engine = ArjunaEngine(loader=loader)  # create the engine
    assert calls["n"] == 0  # the loader has not been called
    assert engine.is_loaded is False  # and the engine reports that it is not loaded


def test_models_are_loaded_only_once():  # load() and read_text() must not start the engine twice
    loader, calls = counting_loader(FakeOcr())  # a loader with a counter
    engine = ArjunaEngine(loader=loader)  # create the engine
    engine.load()  # load explicitly
    engine.load()  # load again, which must do nothing
    engine.read_text(Path("a.png"))  # read an image
    engine.read_text(Path("b.png"))  # read another image
    assert calls["n"] == 1  # the loader was called exactly once
    assert engine.is_loaded is True  # and the engine reports that it is loaded


def test_read_text_returns_the_text_from_the_result():  # the normal case
    engine = ArjunaEngine(loader=lambda: FakeOcr({"text": "ಕರ್ನಾಟಕ"}))  # a fake that returns this text
    assert engine.read_text(Path("a.png")) == "ಕರ್ನಾಟಕ"  # the same text comes back


def test_read_text_passes_the_path_as_a_string():  # Arjuna expects plain text paths
    fake = FakeOcr()  # a fake engine that records its calls
    engine = ArjunaEngine(loader=lambda: fake)  # create the engine with it
    engine.read_text(Path("some/image.png"))  # read an image
    assert fake.calls == ["some/image.png"]  # the fake received the path as a string


def test_read_text_falls_back_to_render_when_there_is_no_text_entry():  # the result has no "text" key
    engine = ArjunaEngine(loader=lambda: FakeOcr({"lines": []}))  # a fake whose result has no "text"
    assert engine.read_text(Path("a.png")) == "rendered:txt"  # the text came from render()


def test_empty_text_is_returned_as_it_is():  # the engine does not judge what an empty result means
    engine = ArjunaEngine(loader=lambda: FakeOcr({"text": ""}))  # a fake that finds no text
    assert engine.read_text(Path("a.png")) == ""  # an empty string comes back


def test_failure_while_reading_becomes_an_engine_error():  # any failure inside Arjuna must be wrapped
    engine = ArjunaEngine(loader=lambda: FakeOcr(error=RuntimeError("secret internal detail")))  # a fake that always fails
    with pytest.raises(OcrEngineError) as info:  # the test passes only if an OcrEngineError is raised
        engine.read_text(Path("a.png"))  # try to read an image
    assert "secret internal detail" not in str(info.value)  # internal details must not leak into the message


def test_failure_while_loading_is_wrapped_and_can_be_retried():  # a failed start must not leave a half-loaded engine
    state = {"fail": True}  # the first attempt will fail

    def loader():  # a loader that fails once and then works
        if state["fail"]:  # the first time
            raise RuntimeError("models missing")  # simulate a failed start
        return FakeOcr()  # the second time, return a working fake

    engine = ArjunaEngine(loader=loader)  # create the engine
    with pytest.raises(OcrEngineError):  # the first load must fail with our error type
        engine.load()  # try to load
    assert engine.is_loaded is False  # nothing is marked as loaded
    state["fail"] = False  # now let the loader succeed
    engine.load()  # try again
    assert engine.is_loaded is True  # this time it worked


def test_non_text_result_is_rejected():  # a result that is not a string must not be passed on
    engine = ArjunaEngine(loader=lambda: FakeOcr({"text": 123}))  # a fake that returns a number as text
    with pytest.raises(OcrEngineError):  # the test passes only if an OcrEngineError is raised
        engine.read_text(Path("a.png"))  # try to read an image


def test_only_one_image_is_processed_at_a_time():  # the lock must stop reads from overlapping
    fake = FakeOcr(delay=0.05)  # a fake whose reads take a short while
    engine = ArjunaEngine(loader=lambda: fake)  # create the engine with it
    results = []  # the texts returned by each thread

    def worker():  # what each thread does
        results.append(engine.read_text(Path("a.png")))  # read an image and remember the text

    threads = [threading.Thread(target=worker) for _ in range(4)]  # four threads that all read at once
    for thread in threads:  # start every thread
        thread.start()  # begin running
    for thread in threads:  # wait for every thread
        thread.join()  # block until it has finished
    assert len(results) == 4  # all four reads completed
    assert fake.max_active == 1  # but never more than one at the same moment