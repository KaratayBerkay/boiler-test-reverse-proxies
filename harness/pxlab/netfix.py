"""Resolve every *.lab hostname to 127.0.0.1 inside this process (no /etc/hosts edits needed).

httpx / http.client / ssl / websockets all go through socket.getaddrinfo, so `https://app.lab:18443/` reaches the
published port with the right SNI and Host header. (grpcio resolves natively: it uses 127.0.0.1 plus
`grpc.ssl_target_name_override` / `grpc.default_authority` instead.)
"""
from __future__ import annotations

import socket

_real_getaddrinfo = socket.getaddrinfo


def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):  # noqa: A002
    if isinstance(host, str) and host.endswith(".lab"):
        host = "127.0.0.1"
        family = socket.AF_INET
    return _real_getaddrinfo(host, port, family, type, proto, flags)


def install() -> None:
    if socket.getaddrinfo is not _getaddrinfo:
        socket.getaddrinfo = _getaddrinfo  # type: ignore[assignment]
