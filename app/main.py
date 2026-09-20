from typing import Annotated

from fastapi import Body, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.brief import build_owner_brief
from app.demo_data import synthetic_signals
from app.episodes import EpisodeNotFound, list_episodes, reconcile_brief, resolve_episode
from app.evidence import ConflictingObservation
from app.feedback import FeedbackConflict, get_episode_feedback, record_disposition, record_outcome
from app.models import (
    BusinessSignal,
    EpisodeFeedback,
    OperatorDisposition,
    OperatorDispositionRequest,
    OutcomeObservation,
    OutcomeObservationRequest,
    FindingEpisode,
    OwnerBrief,
    ResolveEpisodeRequest,
)

app = FastAPI(
    title="Project 7 — Owner Intelligence",
    version="0.4.0",
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


@app.post("/analyze/episodes", response_model=OwnerBrief)
def analyze_with_episode_memory(
    signals: Annotated[list[BusinessSignal], Body(max_length=1000)],
) -> OwnerBrief:
    """Analyze signals and reconcile non-blocked findings into durable episodes."""
    try:
        return reconcile_brief(build_owner_brief(signals))
    except ConflictingObservation as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/episodes", response_model=list[FindingEpisode])
def get_episodes() -> list[FindingEpisode]:
    return list_episodes()


@app.post("/episodes/{episode_id}/resolve", response_model=FindingEpisode)
def resolve_finding_episode(
    episode_id: str, request: ResolveEpisodeRequest
) -> FindingEpisode:
    try:
        return resolve_episode(episode_id, request.reason_code)
    except EpisodeNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


# This API remains local/demo-only. No production authentication or tenant model exists.
@app.get("/episodes/{episode_id}/feedback", response_model=EpisodeFeedback)
def episode_feedback(episode_id: str) -> EpisodeFeedback:
    try:
        return get_episode_feedback(episode_id)
    except EpisodeNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/episodes/{episode_id}/dispositions", response_model=OperatorDisposition, status_code=201)
def add_episode_disposition(
    episode_id: str, request: OperatorDispositionRequest
) -> OperatorDisposition:
    try:
        return record_disposition(episode_id, request)
    except EpisodeNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/episodes/{episode_id}/outcomes", response_model=OutcomeObservation, status_code=201)
def add_episode_outcome(
    episode_id: str, request: OutcomeObservationRequest
) -> OutcomeObservation:
    try:
        return record_outcome(episode_id, request)
    except EpisodeNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FeedbackConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
