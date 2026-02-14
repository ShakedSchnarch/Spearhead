#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from spearhead.v1.matrix_ingest import parse_matrix_workbook


def _download_sheet_xlsx(sheet_id: str, destination: Path, timeout: int) -> None:
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    resp = requests.get(export_url, timeout=timeout)
    resp.raise_for_status()
    destination.write_bytes(resp.content)


def _resolve_token(explicit_token: str | None) -> str:
    token = explicit_token or os.getenv("SPEARHEAD_API_TOKEN")
    if not token:
        raise SystemExit("Missing API token. Set --api-token or export SPEARHEAD_API_TOKEN.")
    return token


def _post_events(*, api_base_url: str, api_token: str, events: list[dict[str, Any]], timeout: int) -> tuple[int, int, int]:
    endpoint = api_base_url.rstrip("/") + "/v1/ingestion/forms/events"
    session = requests.Session()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    created = 0
    duplicates = 0
    failed = 0
    for event in events:
        resp = session.post(endpoint, headers=headers, json=event, timeout=timeout)
        if resp.status_code >= 400:
            failed += 1
            continue
        body = resp.json()
        if body.get("created"):
            created += 1
        else:
            duplicates += 1
    return created, duplicates, failed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest multiple company matrix sources using a single registry file "
            "(Kfir/Mahatz/Sufa)."
        )
    )
    parser.add_argument("--registry", type=Path, default=Path("data/external/company_sources/registry.json"))
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--api-token", default=None)
    parser.add_argument("--year", type=int, default=datetime.now(UTC).year)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--companies",
        default="",
        help="Comma-separated company keys to ingest (e.g. Kfir,Mahatz). Empty means all active/ready.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _load_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Registry not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise SystemExit("Invalid registry format: expected list under 'sources'.")
    return sources


def main() -> int:
    args = _build_parser().parse_args()
    sources = _load_registry(args.registry)
    requested = {
        token.strip().lower()
        for token in args.companies.split(",")
        if token.strip()
    }

    token = None if args.dry_run else _resolve_token(args.api_token)

    total_events = 0
    total_created = 0
    total_duplicates = 0
    total_failed = 0

    for source in sources:
        company = str(source.get("company") or "").strip()
        status = str(source.get("status") or "").strip().lower()
        ingest_cfg = source.get("ingestion") or {}
        if not company or not isinstance(ingest_cfg, dict):
            continue
        if requested and company.lower() not in requested:
            continue
        if status not in {"active", "ready"}:
            continue

        sheet_id = str(ingest_cfg.get("sheet_id") or "").strip()
        local_cache = str(ingest_cfg.get("local_cache") or "").strip()
        source_prefix = str(ingest_cfg.get("source_prefix") or f"{company.lower()}-matrix")

        workbook_path: Path | None = None
        temp_file: tempfile.NamedTemporaryFile[str] | None = None
        try:
            if local_cache and Path(local_cache).exists():
                workbook_path = Path(local_cache)
            elif sheet_id:
                temp_file = tempfile.NamedTemporaryFile(prefix=f"{company.lower()}-", suffix=".xlsx", delete=False)
                workbook_path = Path(temp_file.name)
                temp_file.close()
                _download_sheet_xlsx(sheet_id, workbook_path, args.timeout)
            else:
                print(f"[skip] {company}: no local_cache or sheet_id")
                continue

            parsed = parse_matrix_workbook(
                workbook_path,
                company=company,
                year=args.year,
                source_prefix=source_prefix,
            )
            print(
                f"[{company}] parsed events={len(parsed.events)} sheets={len(parsed.sheets_processed)} "
                f"warnings={len(parsed.warnings)}"
            )
            for warning in parsed.warnings:
                print(f"  [warn] {warning}")

            total_events += len(parsed.events)
            if args.dry_run or not parsed.events:
                continue

            created, duplicates, failed = _post_events(
                api_base_url=args.api_base_url,
                api_token=token,
                events=parsed.events,
                timeout=args.timeout,
            )
            total_created += created
            total_duplicates += duplicates
            total_failed += failed
            print(f"[{company}] created={created} duplicates={duplicates} failed={failed}")
        finally:
            if temp_file is not None:
                try:
                    Path(temp_file.name).unlink(missing_ok=True)
                except Exception:
                    pass

    if args.dry_run:
        print(f"Dry-run done. total_events={total_events}")
        return 0

    print(
        f"Ingestion done. events={total_events} created={total_created} "
        f"duplicates={total_duplicates} failed={total_failed}"
    )
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
