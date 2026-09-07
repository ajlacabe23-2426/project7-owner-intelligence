from typing import Annotated
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fastapi import Body, FastAPI, HTTPException

from app.brief import build_owner_brief
from app.demo_data import synthetic_signals
from app.models import BusinessSignal, OwnerBrief
from app.evidence import ConflictingObservation

app = FastAPI(
    title="Project 7 — Owner Intelligence",
    version="0.1.0",
    description="Evidence-linked owner/operator intelligence API.",
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request, error: RequestValidationError) -> JSONResponse:
    # Never echo raw input (PII or non-finite floats) into the JSON error response.
    details = [
        {key: item[key] for key in ("loc", "msg", "type")}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo/signals", response_model=list[BusinessSignal])
def demo_signals() -> list[BusinessSignal]:
    return synthetic_signals()


@app.get("/demo/brief", response_model=OwnerBrief)
def demo_brief() -> OwnerBrief:
    return build_owner_brief(synthetic_signals())


@app.post("/analyze", response_model=OwnerBrief)
def analyze(signals: Annotated[list[BusinessSignal], Body(max_length=1000)]) -> OwnerBrief:
    try:
        return build_owner_brief(signals)
    except ConflictingObservation as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
