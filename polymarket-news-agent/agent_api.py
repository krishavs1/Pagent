"""
HTTP API for the Next.js dashboard: backtest artifacts + parsed JSONL logs.

Run from repo root:
  uvicorn agent_api:app --reload --port 8765
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "backtest" / "results"
DEFAULT_JSONL = RESULTS / "biden_withdrawal_2024_historical.jsonl"
DEFAULT_SUMMARY = RESULTS / "biden_withdrawal_2024_historical_summary.json"
DEFAULT_EQUITY = RESULTS / "biden_withdrawal_2024_historical_equity_curve.json"

app = FastAPI(title="Polymarket News Agent API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _signal_type_to_tier(signal_type: str) -> str:
    return {"OFFICIAL_OUTCOME": "T1", "CREDIBLE_SCOOP": "T2", "INSIDER_LEAK": "T3"}.get(
        signal_type.upper(), "T3"
    )


def _build_signal_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten JSONL into dashboard rows (one per edge_calculated)."""
    rows: list[dict[str, Any]] = []
    last_signal: dict[str, Any] | None = None
    last_classified: dict[str, Any] = {}
    for i, obj in enumerate(events):
        ev = obj.get("event")
        if ev == "signal_received":
            last_signal = obj.get("fields") or {}
            last_classified = {}
            continue
        if ev == "signal_classified":
            last_classified = obj.get("fields") or {}
            continue
        if ev != "edge_calculated" or not last_signal:
            continue
        fields = obj.get("fields") or {}
        mid = str(fields.get("market_id", ""))
        adjusted = float(fields.get("adjusted_edge", 0.0))
        posterior = float(fields.get("posterior", 0.0))
        prior = float(fields.get("prior", 0.0))
        ts = str(obj.get("ts", ""))

        action: str = "SKIP"
        side: str | None = None
        for j in range(i + 1, len(events)):
            nxt = events[j]
            if nxt.get("event") == "signal_received":
                break
            if nxt.get("event") == "trade_executed":
                tf = nxt.get("fields") or {}
                if str(tf.get("market_id")) == mid:
                    side = str(tf.get("side", "")).upper()
                    break
            if nxt.get("event") == "trade_skipped":
                sf = nxt.get("fields") or {}
                if str(sf.get("market_id")) == mid:
                    action = "SKIP"
                    break

        if side == "BUY":
            action = "BUY"
        elif side == "SELL":
            action = "SELL"
        else:
            action = "SKIP"

        sig_id = str(last_signal.get("signal_id", ""))
        time_fmt = ts
        if "T" in ts:
            time_fmt = ts.split("T", 1)[-1][:8] if len(ts) > 10 else ts

        rows.append(
            {
                # Log line index keeps keys unique if the same market is logged twice.
                "id": f"{sig_id}-{mid}-{i}",
                "time": time_fmt,
                "sourceTier": _signal_type_to_tier(str(last_classified.get("signal_type", ""))),
                "source": str(last_signal.get("source", "")),
                "headline": str(last_signal.get("headline", "")),
                "matchedMarket": mid,
                "prior": prior,
                "posterior": posterior,
                "adjustedEdge": adjusted,
                "action": action,
                "confidence": float(last_classified.get("confidence", 0.0)),
            }
        )
    return rows


def _edge_sparkline(events: list[dict[str, Any]], n: int = 7) -> list[dict[str, float]]:
    edges: list[float] = []
    for obj in events:
        if obj.get("event") == "edge_calculated":
            f = obj.get("fields") or {}
            edges.append(float(f.get("adjusted_edge", 0.0)))
    tail = edges[-n:] if len(edges) > n else edges
    return [{"x": float(i), "y": abs(e) * 100.0} for i, e in enumerate(tail)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/backtest/summary")
def backtest_summary() -> Any:
    return _read_json(DEFAULT_SUMMARY)


@app.get("/api/backtest/equity")
def backtest_equity() -> Any:
    return _read_json(DEFAULT_EQUITY)


@app.get("/api/backtest/file/{name}")
def backtest_file(name: str):
    key = name.lower().replace(".json", "").replace(".jsonl", "")
    if key in ("jsonl", "biden_dropout_2024", "biden_withdrawal_2024_historical"):
        path = DEFAULT_JSONL
    elif key == "summary":
        path = DEFAULT_SUMMARY
    elif key == "equity":
        path = DEFAULT_EQUITY
    else:
        raise HTTPException(status_code=404, detail="Unknown file")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Run backtest first")
    med = "application/x-ndjson" if path.suffix == ".jsonl" else "application/json"
    return FileResponse(path, filename=path.name, media_type=med)


@app.post("/api/backtest/run")
def backtest_run() -> dict[str, Any]:
    try:
        subprocess.run(
            [sys.executable, "-m", "backtest.runner"],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        return {"ok": True, "message": "Backtest finished"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr or str(e)) from e


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    events = _parse_jsonl(DEFAULT_JSONL)
    summary: dict[str, Any] = {}
    if DEFAULT_SUMMARY.is_file():
        summary = json.loads(DEFAULT_SUMMARY.read_text(encoding="utf-8"))

    bankroll = float(summary.get("bankroll_start_usd", 1000.0))
    total_exp = float(summary.get("total_exposure", 0.0))
    trades = int(summary.get("total_trades", 0))
    open_n = 1 if total_exp > 0.5 else 0
    win_rate = float(summary.get("win_rate", 0.0))
    avg_edge = float(summary.get("avg_edge_at_entry", 0.0))
    unreal = float(summary.get("unrealized_pnl", 0.0))
    realized = float(summary.get("realized_pnl", 0.0))

    signals = _build_signal_rows(events)
    spark = _edge_sparkline(events)

    pipeline = [
        {"step": "Ingestion", "status": "complete", "lastRun": "from replay"},
        {"step": "Aggregation", "status": "complete", "lastRun": "from replay"},
        {"step": "Market Matching", "status": "complete", "lastRun": "from replay"},
        {"step": "Bayesian Update", "status": "complete", "lastRun": "from replay"},
        {"step": "Edge Calculation", "status": "complete", "lastRun": "from replay"},
        {"step": "Risk Check", "status": "complete", "lastRun": "from replay"},
        {"step": "Execution", "status": "complete", "lastRun": "from replay"},
    ]

    return {
        "stats": {
            "bankroll": bankroll,
            "totalExposure": total_exp,
            "openPositions": open_n,
            "unrealizedPnl": unreal,
            "realizedPnl": realized,
            "winRate": win_rate,
            "totalTrades": trades,
            "avgEdge": avg_edge,
        },
        "signals": signals,
        "positions": [],
        "pipelineStatus": pipeline,
        "edgeSparkline": spark,
    }


def _build_replay_groups(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group JSONL events by signal for step-by-step replay UI."""
    groups: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for obj in events:
        ev = obj.get("event")
        if ev == "signal_received":
            if cur is not None:
                groups.append(cur)
            f = obj.get("fields") or {}
            cur = {
                "signalId": str(f.get("signal_id", "")),
                "headline": str(f.get("headline", "")),
                "source": str(f.get("source", "")),
                "timestamp": str(obj.get("ts", "")),
                "edges": [],
                "trades": [],
                "skipped": [],
            }
            continue
        if cur is None:
            continue
        if ev == "edge_calculated":
            f = obj.get("fields") or {}
            cur["edges"].append(
                {
                    "marketId": str(f.get("market_id", "")),
                    "posterior": float(f.get("posterior", 0.0)),
                    "adjustedEdge": float(f.get("adjusted_edge", 0.0)),
                }
            )
        elif ev == "trade_executed":
            f = obj.get("fields") or {}
            cur["trades"].append(
                {
                    "marketId": str(f.get("market_id", "")),
                    "side": str(f.get("side", "")),
                    "sizeUsd": float(f.get("size_usd", 0.0)),
                    "feeUsd": float(f.get("fee_usd", 0.0)),
                    "slippageBps": float(f.get("slippage_bps", 0.0)),
                }
            )
        elif ev == "trade_skipped":
            f = obj.get("fields") or {}
            cur["skipped"].append(
                {
                    "marketId": str(f.get("market_id", "")),
                    "reason": str(f.get("reason", "")),
                }
            )
    if cur is not None:
        groups.append(cur)
    return groups


def _summarize_log_line(obj: dict[str, Any]) -> str:
    ev = str(obj.get("event", ""))
    f = obj.get("fields") or {}
    if ev == "signal_received":
        h = str(f.get("headline", ""))[:80]
        return f"● signal · {f.get('signal_id')} · {h}"
    if ev == "edge_calculated":
        return (
            f"◆ edge · {f.get('market_id')} · post={float(f.get('posterior', 0)):.4f} "
            f"· adj={float(f.get('adjusted_edge', 0)):.4f}"
        )
    if ev == "trade_executed":
        return (
            f"▶ trade · {f.get('side')} · {f.get('market_id')} · "
            f"${float(f.get('size_usd', 0)):.2f} · fee ${float(f.get('fee_usd', 0)):.4f}"
        )
    if ev == "trade_skipped":
        return f"○ skip · {f.get('market_id')} · {f.get('reason')}"
    if ev == "backtest_started":
        return "══ backtest_started"
    if ev == "backtest_completed":
        return "══ backtest_completed"
    return f"  {ev}"


@app.get("/api/backtest/replay")
def backtest_replay() -> dict[str, Any]:
    events = _parse_jsonl(DEFAULT_JSONL)
    return {"dataset": DEFAULT_JSONL.name, "signals": _build_replay_groups(events)}


@app.get("/api/backtest/log_tail")
def backtest_log_tail(limit: int = 120) -> dict[str, Any]:
    if not DEFAULT_JSONL.is_file():
        return {"lines": []}
    raw_lines = DEFAULT_JSONL.read_text(encoding="utf-8").splitlines()
    tail = raw_lines[-max(1, min(limit, 500)) :]
    lines: list[dict[str, str]] = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            lines.append({"event": str(obj.get("event", "")), "text": _summarize_log_line(obj)})
        except json.JSONDecodeError:
            lines.append({"event": "?", "text": line[:200]})
    return {"lines": lines}

