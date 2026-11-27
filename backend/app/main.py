"""Creates the FastAPI application and wires its parts together."""
import os  # reads environment variables, which are settings given from outside the program
import logging  # Python's standard way to write log messages
import threading  # lets us load the models in the background
from contextlib import asynccontextmanager  # helps define what happens when the server starts and stops
from typing import AsyncIterator  # a type hint for the start-and-stop function below

from fastapi import FastAPI, Request  # the web framework, and the type of an incoming request
from fastapi.exceptions import RequestValidationError  # the error FastAPI raises when a request is malformed
from fastapi.middleware.cors import CORSMiddleware  # the part that decides which websites may call this backend
from fastapi.responses import JSONResponse  # lets us send our own JSON answers

from app.config import Settings, get_settings  # the settings from Step 60
from app.ocr_engine import ArjunaEngine, OcrEngine, OcrEngineError  # the engine wrapper from Step 64
from app.routes import router  # the group of routes from routes.py
from app.validators import UploadError  # the error used for rejected uploads

logger = logging.getLogger(__name__)  # a logger named after this file


def _error_response(status_code: int, message: str) -> JSONResponse:  # builds an error answer in one consistent shape
    """Build the JSON answer for any error: success is false and the message says what went wrong."""
    return JSONResponse(status_code=status_code, content={"success": False, "error": message})  # the same shape every time, so the frontend can rely on it


def _preload_models(engine: OcrEngine) -> None:  # runs in a background thread when the server starts
    """Load the OCR models, and log the result instead of crashing the server."""
    try:  # try to load the models
        engine.load()  # this is the slow step, about 90 seconds on a weak laptop
    except OcrEngineError:  # the models could not be loaded
        logger.exception("Could not load the OCR models in the background; the first request will try again.")  # log the problem with its details
    else:  # no error happened
        logger.info("The OCR models are loaded.")  # log that we are ready


def create_app(settings: Settings | None = None, engine: OcrEngine | None = None, preload: bool = True) -> FastAPI:  # builds the application
    """Build the application. Tests pass a fake engine; the real server uses the defaults."""
    settings = get_settings() if settings is None else settings  # use the given settings, or read them from the environment
    engine = ArjunaEngine() if engine is None else engine  # use the given engine, or create the real one (it loads nothing yet)

    @asynccontextmanager  # turns the function below into a start-and-stop handler
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:  # code before yield runs at startup, code after it at shutdown
        if preload:  # only when background loading is switched on
            threading.Thread(target=_preload_models, args=(engine,), daemon=True, name="ocr-preload").start()  # start loading without blocking the server
        yield  # the server runs while we are paused here

    app = FastAPI(title="Kannada OCR", version="0.1.0", lifespan=lifespan)  # create the application
    app.state.settings = settings  # store the settings where the routes can reach them
    app.state.engine = engine  # store the engine where the routes can reach them
    app.add_middleware(  # add the CORS rules
        CORSMiddleware,  # the part that checks which website is calling
        allow_origins=list(settings.allowed_origins),  # only these website addresses may call us from a browser
        allow_methods=["GET", "POST"],  # the only request types we need
        allow_headers=["*"],  # allow any request headers
    )

    @app.exception_handler(UploadError)  # runs whenever a route raises UploadError
    async def handle_upload_error(_request: Request, error: UploadError) -> JSONResponse:  # turns the error into an answer
        return _error_response(error.status_code, error.message)  # use the status code and message the validator chose

    @app.exception_handler(OcrEngineError)  # runs whenever the OCR engine fails
    async def handle_engine_error(_request: Request, error: OcrEngineError) -> JSONResponse:  # turns the error into an answer
        logger.error("OCR engine error: %s (cause: %r)", error, error.__cause__)  # log the details for the developer
        return _error_response(500, str(error))  # the message is plain and leaks no internal details

    @app.exception_handler(RequestValidationError)  # runs when a request does not match what a route expects
    async def handle_bad_request(_request: Request, _error: RequestValidationError) -> JSONResponse:  # turns the error into an answer
        return _error_response(422, "The request is not valid.")  # a short message in our usual shape

    app.include_router(router)  # add the routes from routes.py
    return app  # hand back the finished application

def configure_logging() -> None:  # switches on log messages for the whole backend
    """Show log messages at the level in LOG_LEVEL (default INFO); an unknown level falls back to INFO."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()  # the level from the environment, or INFO if it is not set
    level = getattr(logging, level_name, None)  # look the name up in Python's logging module, for example "DEBUG"
    if not isinstance(level, int):  # the name was not a real level
        level = logging.INFO  # fall back to INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")  # print each message with its time, level and source


def configure_logging() -> None:  # switches on log messages for the whole backend
    """Show log messages at the level in LOG_LEVEL (default INFO); an unknown level falls back to INFO."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()  # the level from the environment, or INFO if it is not set
    level = getattr(logging, level_name, None)  # look the name up in Python's logging module, for example "DEBUG"
    if not isinstance(level, int):  # the name was not a real level
        level = logging.INFO  # fall back to INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")  # print each message with its time, level and source


configure_logging()  # switch logging on when the server starts
app = create_app()  # the application that the server runs: uvicorn app.main:app