"""Ignition Tag Data API - Secure Web Dev API for realtime and historical tag data."""

__version__ = "0.1.0"
__author__ = "Your Name"

from src.tagapi import (
    WebdevResponse,
    WebdevResponseError,
    WebdevError,
    handle_request,
    validate_request_auth,
    query_real_time_points,
    query_raw_points,
    query_aggregated_points,
)

__all__ = [
    "WebdevResponse",
    "WebdevResponseError",
    "WebdevError",
    "handle_request",
    "validate_request_auth",
    "query_real_time_points",
    "query_raw_points",
    "query_aggregated_points",
]
