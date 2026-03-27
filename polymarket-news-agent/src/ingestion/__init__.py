"""
News ingestion sources and signal normalization.

This package defines abstract and concrete sources (RSS/X/official feeds) that
emit normalized `Signal` objects into a unified async queue.
"""

from src.ingestion.aggregator import AggregatorConfig, SignalAggregator
from src.ingestion.official import OfficialSource
from src.ingestion.rss import RSSSource
from src.ingestion.x_api import XApiSource

__all__ = ["AggregatorConfig", "OfficialSource", "RSSSource", "SignalAggregator", "XApiSource"]

