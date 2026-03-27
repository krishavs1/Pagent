"""
Backtest runner.

Planned responsibilities:
- Load historical event JSON files from `backtest/data/`
- Replay them as `Signal` objects through ingestion->market->scoring->execution->risk
- Maintain a simulated clock for time-based decay and orderbook updates
- Collect metrics (PnL, hit rate, calibration) for analysis

No replay or simulation logic is implemented in this scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils.types import PortfolioState


@dataclass(slots=True)
class BacktestConfig:
    """Configuration for backtest dataset and simulation mode."""

    data_dir: Path
    start_timestamp: Optional[float] = None
    end_timestamp: Optional[float] = None


class BacktestRunner:
    """Replays historical signals through the pipeline with a simulated clock."""

    def __init__(self, config: BacktestConfig) -> None:
        self._config = config

    async def run(self) -> PortfolioState:
        """Run the backtest and return final portfolio state."""
        raise NotImplementedError("Backtest replay not implemented in scaffold.")

