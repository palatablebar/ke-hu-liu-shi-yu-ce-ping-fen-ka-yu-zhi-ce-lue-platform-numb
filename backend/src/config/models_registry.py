"""Import every model so Base.metadata is complete before create_all()."""
from src.models import (  # noqa: F401
    account,
    account_feature,
    audit_log,
    feature_set,
    model_run,
    score_batch,
    user,
)
