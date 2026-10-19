from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["tiktok", "instagram", "xiaohongshu", "upload"]
Category = Literal[
    "restaurant", "cafe", "bar", "bakery", "attraction", "nature", "museum",
    "hotel", "shop", "market", "neighbourhood", "other",
]
Stage = Literal["queued", "fetching", "transcribing", "analysing", "geocoding", "done", "error"]


# --- LLM output schema (kept free of numeric/length constraints so it maps cleanly
# onto structured outputs) ---

class Evidence(BaseModel):
    source: Literal["caption", "audio", "frame", "image"]
    detail: str = Field(description="Short quote or description of what showed/said the place")
    timestamp: str | None = Field(default=None, description="m:ss for audio/frame evidence, else null")


class ExtractedPlace(BaseModel):
    name: str = Field(description="Best-known name of the place, in English/Latin script if one exists")
    name_local: str | None = Field(default=None, description="Name in original script (e.g. Chinese, Japanese), if seen or said")
    category: Category
    address_hint: str | None = Field(default=None, description="Street, district or landmark clues, verbatim if possible")
    city: str | None = None
    country: str | None = None
    description: str = Field(description="One sentence: what the post says about it (dish, vibe, tip)")
    evidence: list[Evidence]
    confidence: Literal["high", "medium", "low"]


class Extraction(BaseModel):
    places: list[ExtractedPlace]
    notes: str | None = Field(default=None, description="Anything ambiguous worth telling the user, else null")


# --- API response schema ---

class Geo(BaseModel):
    place_id: str
    lat: float
    lng: float
    address: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    matched_name: str | None = None


class Place(ExtractedPlace):
    geo: Geo | None = None
    maps_url: str


class SourceInfo(BaseModel):
    platform: Platform
    url: str | None = None
    author: str | None = None
    caption: str = ""
    kind: Literal["video", "images", "text"]


class Result(BaseModel):
    source: SourceInfo
    transcript_language: str | None = None
    places: list[Place]
    notes: str | None = None


class Job(BaseModel):
    id: str
    stage: Stage = "queued"
    error: str | None = None
    # Which stage failed, so the UI can suggest the upload fallback for fetch errors.
    failed_stage: Stage | None = None
    result: Result | None = None
    cached: bool = False
