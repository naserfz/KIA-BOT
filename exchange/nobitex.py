"""
KIA BOT - Nobitex Raw WebSocket
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from websockets.asyncio.client import ClientConnection
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
)
from websockets.asyncio.client import connect as ws_connect

from .config import NobitexConfig
from .channels import (
    candle_channel,
    market_stats_channel,
    orderbook_channel,
    trades_channel,
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

        self.symbol: str | None = None
        self.resolution: str | None = None

        self._request_id = 1

    async def connect(self) -> None:

        if self.connected:
            return

        print("Connecting to Nobitex WebSocket...")

        self.socket = await asyncio.wait_for(
            ws_connect(
                self.config.websocket_url,
                open_timeout=self.config.timeout,
                ping_interval=self.config.ping_interval,
                close_timeout=5,
            ),
            timeout=self.config.timeout + 5,
        )

        self.connected = True

        print("CONNECTED")

        await self._centrifugo_connect()

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

        self.symbol = symbol.strip().upper()
        self.resolution = str(resolution).strip()

        channels = (
            orderbook_channel(self.symbol),
            candle_channel(
                self.symbol,
                self.resolution,
            ),
            trades_channel(self.symbol),
            market_stats_channel(self.symbol),
        )

        for channel in channels:
            await self.subscribe(channel)

    async def messages(self):

        if not self.connected or self.socket is None:
            raise RuntimeError("WebSocket is not connected.")

        try:

            async for raw in self.socket:

                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

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

                if not isinstance(pub, dict):
                    continue

                data = pub.get("data")

                if isinstance(data, str):

                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass

                yield {
                    "symbol": self.symbol,
                    "resolution": self.resolution,
                    "channel": channel,
                    "data": data,
                    "raw": message,
                }

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

    async def close(self) -> None:

        self.connected = False
        self.protocol_ready = False

        if self.socket is not None:

            try:
                await self.socket.close()
            except Exception:
                pass

            self.socket = None


async def main():

    bot = Nobitex()

    try:

        await bot.connect()

        state_file = Path(__file__).with_name("market_state.json")

        if not state_file.exists():
            raise RuntimeError(
                "No market_state.json found. Select a market first."
            )

        state = json.loads(
            state_file.read_text(encoding="utf-8")
        )

        market = state.get("active_market")

        if not market:
            raise RuntimeError(
                "No active market selected."
            )

        market = str(market).strip().upper()

        print(f"ACTIVE MARKET FROM SELECTOR: {market}")

        await bot.select_market(
            market,
            "5",
        )

        print("\nWAITING FOR RAW DATA...\n")

        async for message in bot.messages():

            print("=" * 80)

            print(
                json.dumps(
                    message,
                    ensure_ascii=False,
                    indent=2,
                )
            )

    finally:

        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())

