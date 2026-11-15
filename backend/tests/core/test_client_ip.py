import logging

import pytest

from app.core.client_ip import client_key

HEADER = "CloudFront-Viewer-Address"


@pytest.mark.parametrize(
    ("value", "key"),
    [
        ("198.51.100.10:46532", "198.51.100.10"),
        ("198.51.100.10", "198.51.100.10"),
        ("2001:db8:1:2:3:4:5:6:46532", "2001:db8:1:2::/64"),
        ("[2001:db8:1:2:3:4:5:6]:46532", "2001:db8:1:2::/64"),
        ("[::ffff:198.51.100.10]:443", "198.51.100.10"),
    ],
)
def test_key_comes_from_the_cdn_header(value: str, key: str) -> None:
    assert client_key({HEADER: value}, "10.0.0.1", HEADER) == key


def test_addresses_in_one_ipv6_64_share_a_key() -> None:
    first = client_key({HEADER: "[2001:db8:1:2::1]:1"}, None, HEADER)
    second = client_key({HEADER: "[2001:db8:1:2:ffff::9]:2"}, None, HEADER)

    assert first == second


def test_without_a_cdn_the_peer_address_is_used() -> None:
    assert client_key({HEADER: "198.51.100.10:1"}, "203.0.113.7", "") == "203.0.113.7"


def test_forwarded_for_sent_by_the_customer_is_ignored() -> None:
    headers = {"X-Forwarded-For": "1.2.3.4", HEADER: "198.51.100.10:1"}

    assert client_key(headers, "10.0.0.1", HEADER) == "198.51.100.10"


def test_missing_cdn_header_falls_back_to_the_peer_and_logs_an_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR):
        key = client_key({}, "10.0.0.1", HEADER)

    assert key == "10.0.0.1"
    assert HEADER in caplog.text
