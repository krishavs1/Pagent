"""
Fetch Polymarket CLOB /prices-history for a YES outcome token and emit backtest
timeline rows (mid + bid/ask from mid ± half-spread).

Does not fabricate order book ladders — use static ladders in the dataset or
refresh from a live book snapshot when building a scenario.

Usage:
  python backtest/scripts/fetch_prices_timeline.py \\
    --yes-token-id 29771515314065403331935508893946579645282141892225585852084723308418208825505 \\
    --start 2024-07-20T00:00:00Z --end 2024-07-23T00:00:00Z \\
    --fidelity 10 --step 20

Resolve token from Gamma (example):
  curl -sS 'https://gamma-api.polymarket.com/markets?slug=will-joe-biden-win-the-2024-democratic-presidential-nomination'
  # first clobTokenIds[] entry is YES.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from typing import Any


def _parse_iso(ts: str) -> int:
    return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())


def fetch_history(
    clob_base: str,
    token_id: str,
    start_ts: int,
    end_ts: int,
    fidelity: int,
    interval: str | None,
) -> list[dict[str, Any]]:
    q = f"market={token_id}&startTs={start_ts}&endTs={end_ts}&fidelity={fidelity}"
    if interval:
        q += f"&interval={interval}"
    url = f"{clob_base.rstrip('/')}/prices-history?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "polymarket-news-agent/backtest"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return list((data.get("history") or []))


def to_timeline_rows(
    history: list[dict[str, Any]],
    half_spread: float,
    step: int,
) -> list[dict[str, Any]]:
    if not history:
        return []
    hist = sorted(history, key=lambda x: int(x.get("t", 0)))
    thin: list[dict[str, Any]] = []
    for i in range(0, len(hist), max(1, step)):
        thin.append(hist[i])
    if hist[-1] not in thin:
        thin.append(hist[-1])
    out: list[dict[str, Any]] = []
    for x in thin:
        t = int(x["t"])
        p = float(x["p"])
        ts = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(
            {
                "timestamp": ts,
                "mid_price": round(p, 6),
                "best_bid_yes": round(max(0.0, p - half_spread), 6),
                "best_ask_yes": round(min(1.0, p + half_spread), 6),
            }
        )
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch CLOB price history as backtest timeline JSON.")
    p.add_argument("--yes-token-id", required=True, help="YES outcome token id (CLOB asset id).")
    p.add_argument("--start", required=True, help="ISO start (e.g. 2024-07-20T00:00:00Z).")
    p.add_argument("--end", required=True, help="ISO end (exclusive-ish; use CLOB endTs).")
    p.add_argument("--fidelity", type=int, default=5, help="CLOB fidelity (minutes between samples).")
    p.add_argument("--interval", default=None, help="Optional CLOB interval (1h, 1d, ...).")
    p.add_argument(
        "--clob-base",
        default="https://clob.polymarket.com",
        help="CLOB base URL.",
    )
    p.add_argument("--half-spread", type=float, default=0.01, help="Half-spread for bid/ask from mid.")
    p.add_argument("--step", type=int, default=15, help="Keep every Nth sample after fetch.")
    args = p.parse_args()

    start_ts = _parse_iso(args.start)
    end_ts = _parse_iso(args.end)
    raw = fetch_history(args.clob_base, args.yes_token_id, start_ts, end_ts, args.fidelity, args.interval)
    rows = to_timeline_rows(raw, args.half_spread, args.step)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
