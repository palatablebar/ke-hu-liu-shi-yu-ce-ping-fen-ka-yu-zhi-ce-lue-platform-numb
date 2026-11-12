from pydantic import BaseModel


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
