from pydantic import BaseModel, Field


class ScoreCreateRequest(BaseModel):
    model_run_id: int | None = None
    threshold: float = Field(default=0.35, ge=0.05, le=0.95)
    budget_total: float = Field(default=12500.0, gt=0, le=10_000_000)
    cost_per_account: float = Field(default=500.0, gt=0, le=1_000_000)
    retention_lift: float = Field(default=0.35, gt=0, le=1.0)
