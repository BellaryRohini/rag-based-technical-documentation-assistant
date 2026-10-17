from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000, description="Question about the indexed documentation")
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank")
        return value


class SourceItem(BaseModel):
    source: str
    chunk_id: str | None = None
    preview: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceItem]
    retries: int = Field(ge=0)
    status: Literal["answered", "insufficient_context"]


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("question", "answer")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class IngestRequest(BaseModel):
    urls: list[HttpUrl] = Field(default_factory=list, max_length=20, description="Public documentation pages to index")
