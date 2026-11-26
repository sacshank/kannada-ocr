"""Wrapper around the Arjuna-OCR engine: loads the models once and reads one image at a time."""

import threading  # gives us a lock, so only one image is processed at a time
from pathlib import Path  # makes working with file paths simple and safe
from typing import Any, Callable, Protocol  # type hints that describe what our functions accept and return


class OcrEngineError(Exception):  # the one error type for every OCR failure
    """Raised when the OCR engine cannot be started or fails to read an image."""


class OcrEngine(Protocol):  # describes what any OCR engine must offer, real or fake
    """The interface the rest of the backend relies on."""

    @property  # lets us write engine.is_loaded instead of engine.is_loaded()
    def is_loaded(self) -> bool:  # tells whether the models are in memory yet
        ...  # the real work is done by the classes that follow this interface

    def load(self) -> None:  # loads the models into memory
        ...  # the real work is done by the classes that follow this interface

    def read_text(self, image_path: Path) -> str:  # reads the text from one image file
        ...  # the real work is done by the classes that follow this interface


def _load_arjuna() -> Any:  # the default way to start Arjuna
    """Import and start the real Arjuna engine. This is the slow step (about 90 seconds on a weak laptop)."""
    from kanen_infer import KanEnOCR  # import name from the Arjuna model card; imported here so the tests never need it

    return KanEnOCR()  # load the models into memory and hand back the engine


class ArjunaEngine:  # our wrapper around Arjuna
    """Loads Arjuna once, on first use, and reads one image at a time."""

    def __init__(self, loader: Callable[[], Any] = _load_arjuna) -> None:  # the loader can be replaced in tests
        self._loader = loader  # the function that starts the engine
        self._ocr: Any = None  # the loaded engine; None means not loaded yet
        self._lock = threading.Lock()  # only one thread may use the engine at a time

    @property  # lets us write engine.is_loaded instead of engine.is_loaded()
    def is_loaded(self) -> bool:  # tells whether the models are in memory yet
        return self._ocr is not None  # True once the engine has been started

    def load(self) -> None:  # starts the engine now, instead of waiting for the first image
        """Load the models if they are not loaded yet."""
        with self._lock:  # wait for any image that is being read, and block others while loading
            self._ensure_loaded()  # start the engine only if it is not already running

    def _ensure_loaded(self) -> None:  # starts the engine; the caller must already hold the lock
        if self._ocr is not None:  # already loaded
            return  # nothing to do
        try:  # try to start the engine
            self._ocr = self._loader()  # run the loader and keep the engine it returns
        except Exception as error:  # anything that goes wrong while starting
            raise OcrEngineError("The OCR engine could not be started.") from error  # plain message, details kept out of it

    def read_text(self, image_path: Path) -> str:  # reads the text from one image file
        """Read one image file and return the text Arjuna found (it may be an empty string)."""
        with self._lock:  # only one image is processed at a time
            self._ensure_loaded()  # load the models first if this is the first image
            try:  # try to read the image
                doc = self._ocr.page(str(image_path))  # Arjuna wants the path as plain text
                text = doc.get("text") if isinstance(doc, dict) else None  # take the plain text from the structured result
                if text is None:  # the result had no "text" entry
                    text = self._ocr.render(doc, "txt")  # ask Arjuna to turn the result into plain text instead
            except Exception as error:  # anything that goes wrong while reading
                raise OcrEngineError("The OCR engine failed to read the image.") from error  # plain message, details kept out of it
        if not isinstance(text, str):  # the engine returned something that is not text
            raise OcrEngineError("The OCR engine returned an unexpected result.")  # refuse to pass it on
        return text  # the text found, possibly empty