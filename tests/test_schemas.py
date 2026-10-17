import pytest
from pydantic import ValidationError

from app.schemas import QueryRequest, FeedbackRequest, IngestRequest


def test_query_request_trims_question():
    request = QueryRequest(question="  How does FastAPI validate request bodies?  ")
    assert request.question == "How does FastAPI validate request bodies?"


def test_query_request_rejects_blank_question():
    with pytest.raises(ValidationError):
        QueryRequest(question="   ")


def test_feedback_rating_is_limited():
    request = FeedbackRequest(question="Q", answer="A", rating="up")
    assert request.rating == "up"
    with pytest.raises(ValidationError):
        FeedbackRequest(question="Q", answer="A", rating="neutral")


def test_ingest_request_accepts_empty_url_list():
    assert IngestRequest().urls == []


def test_ingest_request_validates_url():
    with pytest.raises(ValidationError):
        IngestRequest(urls=["not-a-url"])
