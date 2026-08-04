from typing import list
from uuid import UUID

from pydantic import BaseModel, Field


class TimedCaption(BaseModel):
    word: str
    start: float
    end: float


class SceneSchema(BaseModel):
    scene_number: int
    text: str = Field(..., description="Narration voiceover line")
    visual_description: str = Field(
        ...,
        description="Prompt or cue for visual overlays / stock footage",
    )
    duration_seconds: float = Field(
        ..., description="Estimated duration of this scene"
    )
    captions: list[TimedCaption] | None = Field(
        default=None,
        description="Word-level timestamps added post audio synthesis",
    )


class ScriptGenerateRequest(BaseModel):
    user_id: UUID
    topic: str = Field(
        ..., example="5 Mind-Blowing AI Tools Changing the World"
    )
    tone: str = Field(
        default="dramatic & engaging", example="dramatic & engaging"
    )
    target_duration_seconds: int = Field(default=30, ge=15, le=60)


class ScriptResponse(BaseModel):
    hook: str = Field(..., description="Attention-grabbing intro line")
    topic: str
    tone: str
    total_estimated_duration: float
    scenes: list[SceneSchema]
