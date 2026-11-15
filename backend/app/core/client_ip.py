"""Who is calling, for rate limits.

Behind CloudFront the TCP peer is CloudFront itself, so the customer's address comes
from a header CloudFront fills (`CLIENT_IP_HEADER`, `CloudFront-Viewer-Address` in
production: "198.51.100.10:46532"). It can be trusted because Caddy refuses every
request that did not come through CloudFront. Never the first value of
`X-Forwarded-For`, which the customer can send.

IPv6 customers are keyed by their /64 network: one connection usually owns a whole
/64, and could otherwise change address on every attempt.
"""

import logging
from collections.abc import Mapping
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

type IPAddress = IPv4Address | IPv6Address


def client_key(headers: Mapping[str, str], peer: str | None, header_name: str) -> str:
    """The rate-limit key of a request: its IPv4 address, or its IPv6 /64 network."""
    address = _client_address(headers, peer, header_name)
    if address is None:
        return "unknown"
    return _network_key(address)


def _client_address(
    headers: Mapping[str, str], peer: str | None, header_name: str
) -> IPAddress | None:
    if not header_name:
        return _parse_address(peer)
    address = _parse_viewer_address(headers.get(header_name))
    if address is None:
        # A misconfigured CDN: everyone would share the peer's key. Loud, not silent.
        logger.error("Header %s is missing or unreadable; using the peer address", header_name)
        return _parse_address(peer)
    return address


def _parse_viewer_address(value: str | None) -> IPAddress | None:
    """ "ip:port", "[ipv6]:port", or an address without a port."""
    if not value:
        return None
    value = value.strip()
    if value.startswith("["):
        return _parse_address(value[1 : value.find("]")])
    return _parse_address(value.rsplit(":", 1)[0]) or _parse_address(value)


def _parse_address(value: str | None) -> IPAddress | None:
    try:
        return ip_address(value) if value else None
    except ValueError:
        return None


def _network_key(address: IPAddress) -> str:
    if isinstance(address, IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ip_network(f"{address}/64", strict=False))
    return str(address)


def request_client_key(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> str:
    peer = request.client.host if request.client else None
    return client_key(request.headers, peer, settings.client_ip_header)


ClientKey = Annotated[str, Depends(request_client_key)]
"""The caller's rate-limit key, as an endpoint parameter."""
