from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NobitexConfig:

    websocket_url: str = (
        "wss://ws.nobitex.ir/connection/websocket"
    )

    token: str | None = None

    timeout: float = 20.0

    ping_interval: float = 20.0

    ping_timeout: float = 20.0
