import pytest

from app.middleware import BodyLimitMiddleware, safe_correlation_id


def test_correlation_identifier_rejects_log_injection_and_pii():
    supplied = "alice@example.com\nforged=true"
    generated = safe_correlation_id(supplied)
    assert supplied not in generated
    assert len(generated) == 36


@pytest.mark.asyncio
async def test_chunked_body_without_content_length_is_bounded_before_parsing():
    called = False
    incoming = iter(
        [
            {"type": "http.request", "body": b"12345678", "more_body": True},
            {"type": "http.request", "body": b"abcdefgh", "more_body": False},
        ]
    )
    sent: list[dict] = []

    async def downstream(_scope, _receive, _send):
        nonlocal called
        called = True

    async def receive():
        return next(incoming)

    async def send(message):
        sent.append(message)

    middleware = BodyLimitMiddleware(downstream, max_bytes=10)
    await middleware(
        {"type": "http", "headers": [], "method": "POST", "path": "/v1/protect"},
        receive,
        send,
    )

    assert called is False
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413
    headers = dict(sent[0]["headers"])
    assert headers[b"cache-control"] == b"no-store"
