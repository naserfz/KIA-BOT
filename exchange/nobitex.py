from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from .config import NobitexConfig
from .channels import (
    candle_channel,
    market_stats_channel,
    orderbook_channel,
    trades_channel,
)

from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
)


class Nobitex:

    def __init__(
        self,
        config: NobitexConfig | None = None,
    ) -> None:

        self.config = config or NobitexConfig()
        self.socket: ClientConnection | None = None

        self.connected = False
        self.protocol_ready = False

        self.symbols: set[str] = set()
        self.resolution = "5"

        self._request_id = 1
        self._message_queue = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None

    async def connect(self) -> None:

        if self.connected:
            return

        print("Connecting to Nobitex WebSocket...")

        self.socket = await asyncio.wait_for(
            ws_connect(
                self.config.websocket_url,
                open_timeout=self.config.timeout,
                ping_interval=None,
                close_timeout=5,
            ),
            timeout=self.config.timeout + 5,
        )

        self.connected = True

        print("CONNECTED")

        await self._centrifugo_connect()

        self._reader_task = asyncio.create_task(
            self._reader_loop()
        )

    async def _centrifugo_connect(self) -> None:

        if self.socket is None:
            raise RuntimeError("WebSocket is not connected.")

        request = {
            "connect": {},
            "id": self._request_id,
        }

        self._request_id += 1

        await self.socket.send(json.dumps(request))

        while True:

            raw = await asyncio.wait_for(
                self.socket.recv(),
                timeout=self.config.timeout,
            )

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            if raw == "{}":
                await self.socket.send("{}")
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if not isinstance(message, dict):
                continue

            if "connect" in message:
                self.protocol_ready = True
                print("CENTRIFUGO READY")
                return

            if "error" in message:
                raise RuntimeError(
                    f"Nobitex WebSocket error: {message}"
                )

    async def subscribe(self, channel: str) -> None:

        if not self.connected or self.socket is None:
            raise RuntimeError("WebSocket is not connected.")

        if not self.protocol_ready:
            raise RuntimeError("Centrifugo is not ready.")

        request = {
            "id": self._request_id,
            "subscribe": {
                "channel": channel,
            },
        }

        self._request_id += 1

        await self.socket.send(json.dumps(request))

        print(f"SUBSCRIBED: {channel}")

    async def select_market(
        self,
        symbol: str,
        resolution: str = "5",
    ) -> None:

        await self.select_markets(
            [symbol],
            resolution,
        )

    async def select_markets(
        self,
        symbols: list[str] | set[str] | tuple[str, ...],
        resolution: str = "5",
    ) -> None:

        self.resolution = str(resolution).strip()

        normalized_symbols = {
            str(symbol).strip().upper()
            for symbol in symbols
            if str(symbol).strip()
        }

        self.symbols = normalized_symbols

        for symbol in sorted(self.symbols):

            channels = (
                orderbook_channel(symbol),
                candle_channel(
                    symbol,
                    self.resolution,
                ),
                trades_channel(symbol),
                market_stats_channel(symbol),
            )

            for channel in channels:
                await self.subscribe(channel)

    @staticmethod
    def _symbol_from_channel(channel: str) -> str | None:

        channel = str(channel).strip()

        prefixes = (
            "public:orderbook-",
            "public:trades-",
            "public:market-stats-",
            "public:candle-",
        )

        for prefix in prefixes:

            if channel.startswith(prefix):

                value = channel[len(prefix):]

                if prefix == "public:candle-":
                    parts = value.rsplit("-", 1)
                    value = parts[0]

                return value.strip().upper()

        return None

    async def _reader_loop(self) -> None:

        if self.socket is None:
            return

        try:

            async for raw in self.socket:

                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

                # Centrifugo application-level heartbeat.
                if raw == "{}":
                    try:
                        await self.socket.send("{}")
                    except ConnectionClosed:
                        break
                    continue

                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if not isinstance(message, dict):
                    continue

                if "error" in message:
                    print("WEBSOCKET ERROR:", message)
                    continue

                if "subscribe" in message:
                    continue

                push = message.get("push")

                if not isinstance(push, dict):
                    continue

                channel = push.get("channel")
                pub = push.get("pub")

                if not isinstance(channel, str):
                    continue

                if not isinstance(pub, dict):
                    continue

                data = pub.get("data")

                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass

                symbol = self._symbol_from_channel(channel)

                if not symbol:
                    continue

                await self._message_queue.put(
                    {
                        "symbol": symbol,
                        "resolution": self.resolution,
                        "channel": channel,
                        "data": data,
                        "raw": message,
                    }
                )

        except (
            ConnectionClosed,
            ConnectionClosedError,
            ConnectionClosedOK,
        ) as exc:

            print(
                f"[NOBITEX WS] Connection closed: {exc}"
            )

        finally:
            self.connected = False
            self.protocol_ready = False

    async def messages(self):

        if not self.connected:
            raise RuntimeError(
                "WebSocket is not connected."
            )

        while self.connected:

            try:
                message = await self._message_queue.get()
            except asyncio.CancelledError:
                raise

            yield message

    async def close(self) -> None:

        self.connected = False
        self.protocol_ready = False
        self.symbols.clear()

        if self._reader_task is not None:

            self._reader_task.cancel()

            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

            self._reader_task = None

        if self.socket is not None:

            try:
                await self.socket.close()
            except Exception:
                pass

            self.socket = None
