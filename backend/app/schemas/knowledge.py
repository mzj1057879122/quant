from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeSubmitRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str | None = None
    content: str = Field(..., min_length=10)
    source: str | None = None
    sourceUrl: str | None = None
    category: str | None = None


class KnowledgeUrlRequest(BaseModel):
    url: str = Field(..., min_length=10)
    category: str | None = None


class KnowledgeUpdateRequest(BaseModel):
    title: str | None = None
    author: str | None = None
    content: str | None = None
    category: str | None = None


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    author: str | None = None
    content: str
    source: str | None = None
    sourceUrl: str | None = None
    category: str | None = None
    status: str
    extractedPrinciples: str | None = None
    errorMessage: str | None = None
    processDuration: int | None = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    total: int
    items: list[KnowledgeResponse]


class KnowledgeStatusResponse(BaseModel):
    id: int
    status: str
    extractedPrinciples: str | None = None
    errorMessage: str | None = None
    processDuration: int | None = None

    class Config:
        from_attributes = True


class FrameworkResponse(BaseModel):
    id: int
    version: int
    status: str
    knowledgeCount: int
    frameworkContent: str | None = None
    rawOutput: str | None = None
    errorMessage: str | None = None
    processDuration: int | None = None
    createdAt: datetime

    class Config:
        from_attributes = True


class FrameworkListResponse(BaseModel):
    total: int
    items: list[FrameworkResponse]
