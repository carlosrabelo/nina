"""Tests for Gmail From header normalization."""

import pytest

from nina.integrations.google.gmail.parse_sender import normalize_sender


@pytest.mark.parametrize(
    "header,expected",
    [
        ("", ""),
        ("shop@amazon.com.br", "shop@amazon.com.br"),
        ('Amazon <store-news@amazon.com.br>', "store-news@amazon.com.br"),
        ('"Name" <user+tag@example.com>', "user+tag@example.com"),
        ("no-email-here", "no-email-here"),
    ],
)
def test_normalize_sender(header: str, expected: str) -> None:
    assert normalize_sender(header) == expected
