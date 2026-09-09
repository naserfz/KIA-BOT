import asyncio
import time
import sqlite3
from pathlib import Path

from exchange.nobitex import Nobitex
from exchange.normalizer import ExchangeNormalizer
from database.market_database import MarketDatabase


ROOT = Path(__file__).parent
SYMBOL = "XRPUSDT"
RESOLUTION = "5"
DURATION = 120


def count_rows(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


async def main():

    print("=" * 70)
    print("KIA BOT - FULL NOBITEX WEBSOCKET INTEGRATION TEST")
    print("=" * 70)
    print(f"SYMBOL   : {SYMBOL}")
    print(f"DURATION : {DURATION} seconds")
    print()

    bot = Nobitex()
    normalizer = ExchangeNormalizer()

    database = MarketDatabase(
        exchange="nobitex",
        symbol=SYMBOL,
        root=ROOT / "database",
    )

    received = {
        "trades": 0,
        "orderbook": 0,
        "candle": 0,
        "market_stats": 0,
    }

    saved = {
        "trades": 0,
        "orderbook": 0,
        "candle": 0,
        "market_stats": 0,
    }

    errors = []

    print("CONNECTING...")
    await bot.connect()

    print()
    print("SUBSCRIBING ALL CHANNELS...")

    await bot.select_market(SYMBOL, RESOLUTION)

    print()
    print("ACTIVE CHANNELS:")
    print(f"  public:trades-{SYMBOL}")
    print(f"  public:orderbook-{SYMBOL}")
    print(f"  public:candle-{SYMBOL}-{RESOLUTION}")
    print(f"  public:market-stats-{SYMBOL}")

    print()
    print("RECEIVING DATA...")
    print()

    started = time.monotonic()
    last_report = started

    try:
        async for message in bot.messages():

            channel = str(message.get("channel", ""))

            if channel.startswith("public:trades-"):
                data_type = "trades"

            elif channel.startswith("public:orderbook-"):
                data_type = "orderbook"

            elif channel.startswith("public:candle-"):
                data_type = "candle"

            elif channel.startswith("public:market-stats-"):
                data_type = "market_stats"

            else:
                continue

            try:
                normalized = normalizer.normalize(message)
                database.save(normalized)

                received[data_type] += 1
                saved[data_type] += 1

            except Exception as exc:
                errors.append(
                    f"{data_type}: {type(exc).__name__}: {exc}"
                )

            now = time.monotonic()

            if now - last_report >= 10:
                elapsed = now - started

                print(
                    f"[{elapsed:6.1f}s] "
                    f"TRADES={received['trades']:5d} "
                    f"ORDERBOOK={received['orderbook']:5d} "
                    f"CANDLE={received['candle']:5d} "
                    f"STATS={received['market_stats']:5d}"
                )

                last_report = now

            if now - started >= DURATION:
                break

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        errors.append(
            f"WEBSOCKET: {type(exc).__name__}: {exc}"
        )

    finally:
        await bot.close()

    print()
    print("=" * 70)
    print("FULL INTEGRATION TEST FINISHED")
    print("=" * 70)

    print()
    print("WEBSOCKET RECEIVED")
    print("-" * 30)

    for key, value in received.items():
        print(f"{key.upper():20s}: {value}")

    print()
    print("DATABASE SAVED")
    print("-" * 30)

    for key, value in saved.items():
        print(f"{key.upper():20s}: {value}")

    print()
    print("DATABASE TOTALS")
    print("-" * 30)

    db_totals = {}

    try:
        db_totals["trades"] = count_rows(
            database.trades_db,
            "trades",
        )

        db_totals["orderbook"] = count_rows(
            database.orderbook_db,
            "orderbook",
        )

        db_totals["candle"] = count_rows(
            database.candles_db,
            "candles",
        )

        db_totals["market_stats"] = count_rows(
            database.market_stats_db,
            "market_stats",
        )

        print(f"TRADES TOTAL       : {db_totals['trades']}")
        print(f"ORDERBOOK TOTAL    : {db_totals['orderbook']}")
        print(f"CANDLES TOTAL      : {db_totals['candle']}")
        print(f"MARKET STATS TOTAL : {db_totals['market_stats']}")

    except Exception as exc:
        errors.append(
            f"DATABASE READ: {type(exc).__name__}: {exc}"
        )

    print()
    print("VALIDATION")
    print("-" * 30)

    passed = True

    for key in received:

        if received[key] != saved[key]:
            print(
                f"[FAIL] {key.upper()}: "
                f"received={received[key]} "
                f"saved={saved[key]}"
            )
            passed = False
        else:
            print(
                f"[PASS] {key.upper()}: "
                f"received={received[key]} "
                f"saved={saved[key]}"
            )

    print()
    print("DATABASE INTEGRITY")
    print("-" * 30)

    table_map = {
        "trades": "TRADES",
        "orderbook": "ORDERBOOK",
        "candle": "CANDLES",
        "market_stats": "MARKET_STATS",
    }

    if db_totals:
        for key, label in table_map.items():

            expected = saved[key]
            total = db_totals[key]

            print(
                f"{label:20s}: "
                f"new={expected} | total={total}"
            )

            if total < expected:
                passed = False
                print(
                    f"[FAIL] DATABASE TOTAL INVALID: {label}"
                )

    if errors:
        passed = False

        print()
        print("ERRORS")
        print("-" * 30)

        for error in errors:
            print(error)

    print()
    print("=" * 70)

    if passed:
        print("[PASS] FULL WEBSOCKET -> NORMALIZER -> DATABASE")
    else:
        print("[FAIL] FULL INTEGRATION TEST")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
