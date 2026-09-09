"""
KIA BOT - Core Service Manager
"""

from __future__ import annotations

from typing import Any


class ServiceManager:

    def __init__(self) -> None:
        self.services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        self.services[name] = service

    async def start_all(self) -> None:
        for service in self.services.values():
            start = getattr(service, "start", None)
            if start is not None:
                result = start()
                if hasattr(result, "__await__"):
                    await result

    async def stop_all(self) -> None:
        for service in reversed(list(self.services.values())):
            stop = getattr(service, "stop", None)
            if stop is not None:
                result = stop()
                if hasattr(result, "__await__"):
                    await result
