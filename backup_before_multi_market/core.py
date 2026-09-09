from __future__ import annotations

import asyncio

import json
from pathlib import Path

from core.database_service import DatabaseService
from core.exchange_service import ExchangeService
from core.service_manager import ServiceManager

from database.market_database import MarketDatabase

from exchange.nobitex import Nobitex
from exchange.normalizer import ExchangeNormalizer


ROOT = Path(__file__).parent.parent

MARKET_STATE_FILE = (
    ROOT
    / "exchange"
    / "market_state.json"
)


class KIACore:

    SUPPORTED_EXCHANGES = (
        "NOBITEX",
    )

    def __init__(
        self,
        exchange: str = "NOBITEX",
    ) -> None:

        self.symbol = self._get_active_market()

        self.exchange_name = (
            str(exchange)
            .strip()
            .upper()
        )

        if (
            self.exchange_name
            not in self.SUPPORTED_EXCHANGES
        ):
            raise RuntimeError(
                f"Unsupported exchange: "
                f"{self.exchange_name}"
            )

        self.bot = self._create_exchange(
            self.exchange_name
        )

        self.normalizer = ExchangeNormalizer()

        self.database = self._create_database()

        self.exchange_service = ExchangeService(
            self.bot
        )

        self.database_service = DatabaseService(
            self.database
        )

        self.service_manager = ServiceManager()

        self.service_manager.register(
            "database",
            self.database_service,
        )

        self.service_manager.register(
            "exchange",
            self.exchange_service,
        )

        self.running = False

    # ========================================================
    # MARKET
    # ========================================================

    @staticmethod
    def _get_active_market() -> str:

        if not MARKET_STATE_FILE.exists():
            raise RuntimeError(
                "No market_state.json found."
            )

        state = json.loads(
            MARKET_STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        symbol = state.get(
            "active_market"
        )

        if not symbol:
            raise RuntimeError(
                "No active market selected."
            )

        return str(symbol).strip().upper()

    # ========================================================
    # EXCHANGE
    # ========================================================

    @staticmethod
    def _create_exchange(
        exchange: str,
    ):

        if exchange == "NOBITEX":
            return Nobitex()

        raise RuntimeError(
            f"Unsupported exchange: {exchange}"
        )

    def _create_database(
        self,
    ) -> MarketDatabase:

        return MarketDatabase(
            exchange=self.exchange_name.lower(),
            symbol=self.symbol,
            root=ROOT / "database",
        )

    # ========================================================
    # START
    # ========================================================

    async def start(self) -> None:

        if self.running:
            return

        print("KIA BOT")
        print(
            f"ACTIVE EXCHANGE: "
            f"{self.exchange_name}"
        )
        print(
            f"ACTIVE MARKET: "
            f"{self.symbol}"
        )
        print("")

        await self.service_manager.start_all()

        await self.bot.select_market(
            self.symbol,
            "5",
        )

        self.running = True

        print("")
        print("DATABASE READY")
        print(
            f"DATABASE PATH: "
            f"{self.database.market_dir}"
        )
        print("")
        print("WAITING FOR RAW DATA...")

        try:

            async for message in self.bot.messages():

                normalized = (
                    self.normalizer.normalize(
                        message
                    )
                )

                self.database_service.save(
                    normalized
                )

                print(
                    f"[SAVED] "
                    f"{normalized['type']} "
                    f"{normalized['symbol']}"
                )

        except asyncio.CancelledError:
            raise

        finally:
            self.running = False

    # ========================================================
    # STOP
    # ========================================================

    async def stop(self) -> None:

        if not self.running:
            return

        print(
            f"STOPPING EXCHANGE: "
            f"{self.exchange_name}"
        )

        await self.service_manager.stop_all()

        self.running = False

        print(
            f"EXCHANGE STOPPED: "
            f"{self.exchange_name}"
        )

    # ========================================================
    # EXCHANGE SWITCH
    # ========================================================

    async def switch_exchange(
        self,
        exchange: str,
    ) -> None:

        exchange = (
            str(exchange)
            .strip()
            .upper()
        )

        if exchange not in self.SUPPORTED_EXCHANGES:
            raise RuntimeError(
                f"Unsupported exchange: "
                f"{exchange}"
            )

        if exchange == self.exchange_name:
            return

        was_running = self.running

        if was_running:
            await self.stop()

        self.exchange_name = exchange

        self.bot = self._create_exchange(
            exchange
        )

        self.database = self._create_database()

        self.exchange_service.bot = self.bot

        self.database_service.database = (
            self.database
        )

        if was_running:
            await self.start()
