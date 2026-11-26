"""The web routes of the OCR backend."""

from fastapi import APIRouter, Request  # APIRouter groups routes together; Request gives access to the running application

router = APIRouter()  # the group of routes that main.py adds to the application


@router.get("/health")  # answers GET requests sent to /health
async def health(request: Request) -> dict[str, object]:  # returns a small dictionary, which FastAPI turns into JSON
    """Report that the service is running and whether the OCR models are loaded yet."""
    engine = request.app.state.engine  # the OCR engine that create_app stored on the application
    return {"status": "ok", "model_loaded": engine.is_loaded}  # is_loaded never waits, so this answers at once