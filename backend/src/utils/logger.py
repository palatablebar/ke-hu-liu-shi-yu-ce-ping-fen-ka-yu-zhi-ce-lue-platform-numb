import json
import logging
import sys
from datetime import datetime, timezone

logger = logging.getLogger("churnmod")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def log_event(event: str, **fields) -> None:
    record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event}
    record.update(fields)
    logger.info(json.dumps(record, ensure_ascii=False, default=str))
