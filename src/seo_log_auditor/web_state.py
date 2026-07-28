"""Flask-side session state and data loading (no Streamlit dependency)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from seo_log_auditor.classify import Classifier, add_page_type, default_classifier, load_classifier
from seo_log_auditor.parsers import parse_log_file
from seo_log_auditor.sitemap import SitemapResult, fetch_sitemap, to_paths
from seo_log_auditor.verify_bot import GoogleRanges, add_verification, fetch_google_ranges

_store: dict[str, dict[str, Any]] = {}


@dataclass
class AppState:
    log_df: pd.DataFrame
    sitemap: SitemapResult | None
    sitemap_paths: list[str]
    sitemap_page_types: pd.Series
    classifier: Classifier
    verification_enabled: bool
    only_verified_default: bool
    sitemap_url: str


def _bucket(session_id: str) -> dict[str, Any]:
    if session_id not in _store:
        _store[session_id] = {
            "log_df": None,
            "sitemap": None,
            "sitemap_paths": [],
            "sitemap_page_types": pd.Series(dtype="string"),
            "classifier": default_classifier(),
            "verification_enabled": False,
            "only_verified_default": False,
            "sitemap_url": "",
        }
    return _store[session_id]


def clear_session(session_id: str) -> None:
    _store.pop(session_id, None)


def clear_caches() -> None:
    parse_uploads_cached.cache_clear()
    fetch_sitemap_cached.cache_clear()
    fetch_google_ranges_cached.cache_clear()


def get_state(session_id: str) -> AppState | None:
    bucket = _bucket(session_id)
    if bucket["log_df"] is None:
        return None
    return AppState(
        log_df=bucket["log_df"],
        sitemap=bucket.get("sitemap"),
        sitemap_paths=bucket.get("sitemap_paths", []),
        sitemap_page_types=bucket.get("sitemap_page_types", pd.Series(dtype="string")),
        classifier=bucket.get("classifier") or default_classifier(),
        verification_enabled=bool(bucket.get("verification_enabled", False)),
        only_verified_default=bool(bucket.get("only_verified_default", False)),
        sitemap_url=bucket.get("sitemap_url", ""),
    )


def get_preferences(session_id: str) -> dict[str, Any]:
    bucket = _bucket(session_id)
    return {
        "verification_enabled": bool(bucket.get("verification_enabled", False)),
        "only_verified_default": bool(bucket.get("only_verified_default", False)),
        "sitemap_url": bucket.get("sitemap_url", ""),
        "has_data": bucket.get("log_df") is not None,
    }


@lru_cache(maxsize=32)
def parse_uploads_cached(files_key: tuple[tuple[str, bytes], ...]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for name, content in files_key:
        df = parse_log_file(name, content)
        if not df.empty:
            frames.append(df)
    if not frames:
        return parse_log_file("empty.txt", b"")
    return pd.concat(frames, ignore_index=True).sort_values("timestamp", kind="stable").reset_index(drop=True)


@lru_cache(maxsize=16)
def fetch_sitemap_cached(url: str) -> SitemapResult:
    return fetch_sitemap(url)


@lru_cache(maxsize=4)
def fetch_google_ranges_cached() -> GoogleRanges:
    return fetch_google_ranges()


def enrich(
    df: pd.DataFrame,
    classifier: Classifier,
    google_ranges: GoogleRanges,
    use_dns_fallback: bool,
) -> pd.DataFrame:
    df = add_page_type(df, classifier)
    df = add_verification(df, google_ranges, use_dns_fallback=use_dns_fallback)
    return df


def filter_to_googlebot(df: pd.DataFrame, only_verified: bool) -> pd.DataFrame:
    claimed_mask = df["claimed_bot"].fillna("").str.startswith(
        ("Googlebot", "AdsBot-Google", "Mediapartners-Google")
    )
    if only_verified and "is_verified_googlebot" in df.columns:
        return df[claimed_mask & df["is_verified_googlebot"].fillna(False)]
    return df[claimed_mask]


def files_cache_key(files: list[tuple[str, bytes]]) -> tuple[tuple[str, bytes], ...]:
    keyed: list[tuple[str, bytes]] = []
    for name, content in files:
        digest = hashlib.sha256(content).hexdigest()
        keyed.append((f"{name}:{digest}", content))
    return tuple(keyed)


def load_data(
    session_id: str,
    files: list[tuple[str, bytes]],
    sitemap_url: str,
    patterns_bytes: bytes | None,
    verify_bots: bool,
    only_verified: bool,
) -> tuple[AppState | None, list[str]]:
    errors: list[str] = []
    if not files:
        errors.append("Please upload at least one log file.")
        return None, errors

    bucket = _bucket(session_id)
    bucket["verification_enabled"] = verify_bots
    bucket["only_verified_default"] = only_verified
    bucket["sitemap_url"] = sitemap_url.strip()

    try:
        df = parse_uploads_cached(files_cache_key(files))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Could not parse log file: {exc}")
        return None, errors

    if df.empty:
        errors.append("Couldn't parse any rows. Is this a Grafana/Loki export of nginx access logs?")
        return None, errors

    if patterns_bytes:
        try:
            classifier = load_classifier(patterns_bytes)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to parse page-pattern rules: {exc}")
            return None, errors
    else:
        classifier = default_classifier()

    sitemap_paths: list[str] = []
    sitemap_result = None
    sitemap_page_types = pd.Series(dtype="string")
    if sitemap_url.strip():
        try:
            sitemap_result = fetch_sitemap_cached(sitemap_url.strip())
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Could not load sitemap from `{sitemap_url}`: {exc}")
            sitemap_result = None
        if sitemap_result is not None:
            host = urlparse(sitemap_url).netloc or None
            sitemap_paths = to_paths(sitemap_result.urls, base_host=host)
            sitemap_page_types = classifier.classify_series(sitemap_paths)
            if sitemap_result.urls and not sitemap_paths:
                errors.append(
                    "All sitemap URLs were filtered out by host matching. "
                    "Your sitemap may live on a different domain than the URLs inside it."
                )
            for err in sitemap_result.errors[:5]:
                errors.append(f"Sitemap error: {err}")

    ranges = fetch_google_ranges_cached()
    enriched = enrich(df, classifier, ranges, use_dns_fallback=verify_bots)

    bucket["log_df"] = enriched
    bucket["sitemap"] = sitemap_result
    bucket["sitemap_paths"] = sitemap_paths
    bucket["sitemap_page_types"] = sitemap_page_types
    bucket["classifier"] = classifier

    return get_state(session_id), errors


def dataframe_records(df: pd.DataFrame | None, limit: int = 500) -> list[dict]:
    if df is None or df.empty:
        return []
    display = df.head(limit).copy()
    for col in display.columns:
        if pd.api.types.is_numeric_dtype(display[col]):
            display[col] = display[col].fillna(0)
        else:
            display[col] = display[col].astype("object").fillna("—")
    return display.to_dict(orient="records")


def summary_for_insights(session_id: str) -> dict[str, Any]:
    state = get_state(session_id)
    if state is None:
        return {"loaded": False}
    from seo_log_auditor.analysis.status_waste import waste_overview

    bot_df = filter_to_googlebot(state.log_df, only_verified=state.only_verified_default)
    waste = waste_overview(bot_df)
    return {
        "loaded": True,
        "total_bot_hits": int(waste["total"]),
        "waste_ratio": float(waste["waste_ratio"]),
        "unique_urls": int(bot_df["path"].nunique()),
        "unique_ips": int(bot_df["ip"].nunique()),
        "verified_share": float(bot_df["is_verified_googlebot"].fillna(False).mean())
        if not bot_df.empty
        else 0.0,
        "sitemap_urls": len(state.sitemap_paths),
        "verification_enabled": state.verification_enabled,
        "only_verified": state.only_verified_default,
    }
