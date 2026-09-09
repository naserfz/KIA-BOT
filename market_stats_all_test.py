import asyncio
import time

from exchange.nobitex import Nobitex


DURATION = 120
TARGET_SYMBOL = "XRPUSDT"
CHANNEL = "public:market-stats-all"


def normalize_symbol(key: str) -> str:
    return str(key).replace("-", "").strip().upper()


async def main():

    print("=" * 70)
    print("KIA BOT - NOBITEX MARKET-STATS-ALL TEST")
    print("=" * 70)
    print(f"CHANNEL  : {CHANNEL}")
    print(f"DURATION : {DURATION} seconds")
    print()

    bot = Nobitex()

    messages = 0
    total_market_entries = 0
    target_found = 0
    malformed = 0
    errors = []

    started = time.monotonic()
    last_report = started

    print("CONNECTING...")
    await bot.connect()

    print()
    print("SUBSCRIBING...")
    await bot.subscribe(CHANNEL)

    print()
    print(f"SUBSCRIBED: {CHANNEL}")
    print()
    print("RECEIVING ALL MARKET STATS...")
    print()

    try:
        async for message in bot.messages():

            if message.get("channel") != CHANNEL:
                continue

            data = message.get("data")

            if not isinstance(data, dict):
                malformed += 1
                continue

            messages += 1
            total_market_entries += len(data)

            symbols = {
                normalize_symbol(key)
                for key in data.keys()
            }

            if TARGET_SYMBOL in symbols:
                target_found += 1

            for key, stats in data.items():

                if not isinstance(stats, dict):
                    malformed += 1
                    continue

                required = (
                    "isClosed",
                    "bestSell",
                    "bestBuy",
                    "volumeSrc",
                    "volumeDst",
                    "latest",
                    "mark",
                    "dayLow",
                    "dayHigh",
                    "dayOpen",
                    "dayClose",
                    "dayChange",
                )

                missing = [
                    field
                    for field in required
                    if field not in stats
                ]

                if missing:
                    malformed += 1
                    errors.append(
                        f"{key}: missing {missing}"
                    )

            now = time.monotonic()

            if now - last_report >= 10:
                elapsed = now - started

                avg_markets = (
                    total_market_entries / messages
                    if messages
                    else 0
                )

                print(
                    f"[{elapsed:6.1f}s] "
                    f"MESSAGES={messages:4d} "
                    f"MARKETS={len(data):4d} "
                    f"AVG={avg_markets:7.1f} "
                    f"XRPUSDT={'YES' if TARGET_SYMBOL in symbols else 'NO'}"
                )

                last_report = now

            if now - started >= DURATION:
                break

    except Exception as exc:
        errors.append(
            f"WEBSOCKET: {type(exc).__name__}: {exc}"
        )

    finally:
        await bot.close()

    print()
    print("=" * 70)
    print("MARKET-STATS-ALL TEST FINISHED")
    print("=" * 70)

    print()
    print("RESULTS")
    print("-" * 30)

    print(f"MESSAGES RECEIVED       : {messages}")
    print(f"TOTAL MARKET ENTRIES    : {total_market_entries}")
    print(
        f"AVERAGE MARKETS/MESSAGE : "
        f"{total_market_entries / messages if messages else 0:.1f}"
    )
    print(f"{TARGET_SYMBOL} FOUND        : {target_found}")
    print(f"MALFORMED DATA           : {malformed}")

    print()
    print("VALIDATION")
    print("-" * 30)

    passed = True

    if messages > 0:
        print("[PASS] MARKET-STATS-ALL MESSAGE RECEIVED")
    else:
        print("[FAIL] NO MARKET-STATS-ALL MESSAGE RECEIVED")
        passed = False

    if total_market_entries > 0:
        print("[PASS] MARKET DATA PRESENT")
    else:
        print("[FAIL] NO MARKET DATA")
        passed = False

    if target_found > 0:
        print(f"[PASS] {TARGET_SYMBOL} FOUND")
    else:
        print(f"[FAIL] {TARGET_SYMBOL} NOT FOUND")
        passed = False

    if malformed == 0:
        print("[PASS] MARKET-STATS SCHEMA")
    else:
        print(
            f"[FAIL] MALFORMED MARKET-STATS: {malformed}"
        )
        passed = False

    if errors:
        print()
        print("ERRORS")
        print("-" * 30)

        for error in errors[:20]:
            print(error)

    print()
    print("=" * 70)

    if passed:
        print("[PASS] NOBITEX MARKET-STATS-ALL")
    else:
        print("[FAIL] NOBITEX MARKET-STATS-ALL")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
