from fastapi import FastAPI

from app.brief import build_owner_brief
from app.demo_data import synthetic_signals
from app.models import BusinessSignal, OwnerBrief

app = FastAPI(
    title="Project 7 — Owner Intelligence",
    version="0.1.0",
    description="Evidence-linked owner/operator intelligence API.",
)


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
def analyze(signals: list[BusinessSignal]) -> OwnerBrief:
    return build_owner_brief(signals)
