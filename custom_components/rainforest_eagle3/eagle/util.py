"""Utility functions for Eagle API client."""

from collections.abc import Mapping
from datetime import UTC, datetime
import logging
from socket import gaierror, gethostbyname_ex

_LOGGER = logging.getLogger(__name__)


def parse_hex_timestamp(value: str) -> datetime | None:
    """Parse a hex timestamp string to a datetime object."""
    try:
        timestamp = int(value, 16)
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except (ValueError, TypeError):
        return None


def get_ensure_list(value: list | dict[str, list | dict], key: str) -> list:
    """Ensure value is a list."""
    if value is None:
        return []
    if isinstance(value, dict) and key in value:
        value = value.get(key, [])
    return value if isinstance(value, list) else [value]


def unwrap_outer_dict(value: Mapping, key: str) -> Mapping:
    """Unwrap outer dict if present."""
    if isinstance(value, Mapping):
        return value.get(key, value)
    return value


def resolve_host(host: str, *, missing_ok: bool = False) -> tuple[str, str | None]:
    """Fallback method to resolve host to an IP address."""
    try:
        fqdn, _, addrs = gethostbyname_ex(host)
    except gaierror as e:
        msg = f"DNS resolution failed for host {host}"
        if not missing_ok:
            _LOGGER.exception(msg)
            raise ValueError(msg) from e
        _LOGGER.debug(msg)
    else:
        return fqdn, addrs[0]
    return host, None


def resolve_host_ex(host: str) -> tuple[str, str | None]:
    """Resolve host to an IP address, trying with some common suffixes."""
    addr = None

    if "." in host:
        fqdn, addr = resolve_host(host, missing_ok=True)
        if addr is None:
            _LOGGER.warning("Failed to resolve host %s", host)
            # FQDN didn't work, so let's try suffixes
            host = host.split(".")[0]

    for suffix in ["", ".local", ".lan", ".home"]:
        fqdn, addr = resolve_host(f"{host}{suffix}", missing_ok=True)
        if addr is not None:
            _LOGGER.info("Resolved host %s to %s", fqdn, addr)

    return host, addr
