from datetime import date, datetime

from pydantic import BaseModel, Field


class ArticleSubmitRequest(BaseModel):
    title: str | None = None
    author: str | None = None
    content: str = Field(..., min_length=10)
    source: str | None = None
    articleDate: date | None = None


class ArticleUrlRequest(BaseModel):
    url: str = Field(..., min_length=10)
    articleDate: date | None = None


class BatchUpdateDateRequest(BaseModel):
    articleIds: list[int] = Field(..., min_items=1)
    articleDate: date


class ArticleResponse(BaseModel):
    id: int
    title: str | None = None
    author: str | None = None
    content: str
    source: str | None = None
    sourceUrl: str | None = None
    articleDate: date
    status: str
    resultSummary: str | None = None
    updatedFiles: str | None = None
    errorMessage: str | None = None
    processDuration: int | None = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    total: int
    items: list[ArticleResponse]


class ArticleStatusResponse(BaseModel):
    id: int
    status: str
    resultSummary: str | None = None
    updatedFiles: str | None = None
    errorMessage: str | None = None
    processDuration: int | None = None

    class Config:
        from_attributes = True
