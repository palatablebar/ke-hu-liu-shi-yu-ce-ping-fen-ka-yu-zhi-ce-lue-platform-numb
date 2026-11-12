from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    label: str | None = Field(default=None, max_length=60)
    learning_rate: float = Field(default=0.15, gt=0.001, le=2.0)
    l2: float = Field(default=0.02, ge=0.0, le=1.0)
    epochs: int = Field(default=1800, ge=100, le=6000)
