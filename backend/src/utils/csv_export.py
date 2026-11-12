import csv
import io
from collections.abc import Iterable, Sequence


def to_csv(columns: Sequence[str], rows: Iterable[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(list(columns))
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    return "\ufeff" + buffer.getvalue()
