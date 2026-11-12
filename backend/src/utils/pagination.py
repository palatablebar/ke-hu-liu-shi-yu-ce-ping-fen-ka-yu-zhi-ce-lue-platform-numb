from dataclasses import dataclass


@dataclass
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination(page: int = 1, page_size: int = 20) -> Pagination:
    page = max(1, int(page or 1))
    page_size = min(200, max(1, int(page_size or 20)))
    return Pagination(page=page, page_size=page_size)


def as_page(items: list, total: int, pagination: Pagination) -> dict:
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(1, (total + pagination.page_size - 1) // pagination.page_size),
    }
