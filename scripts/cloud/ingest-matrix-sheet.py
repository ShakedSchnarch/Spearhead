#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
        raise SystemExit(
            "Missing API token. Set --api-token or export SPEARHEAD_API_TOKEN before running ingestion."
        )
    return token


def _post_events(
    *,
    api_base_url: str,
    api_token: str,
    events: list[dict[str, Any]],
    timeout: int,
) -> tuple[int, int, int, list[str]]:
    endpoint = api_base_url.rstrip("/") + "/v1/ingestion/forms/events"
    session = requests.Session()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    created_count = 0
    duplicate_count = 0
    failed_count = 0
    failures: list[str] = []

    for idx, event in enumerate(events, start=1):
        resp = session.post(endpoint, headers=headers, json=event, timeout=timeout)
        if resp.status_code >= 400:
            failed_count += 1
            detail = resp.text.strip().replace("\n", " ")
            failures.append(f"{idx}: {resp.status_code} {detail[:220]}")
            continue

        data = resp.json()
        if data.get("created"):
            created_count += 1
        else:
            duplicate_count += 1

        if idx % 25 == 0:
            print(f"[progress] {idx}/{len(events)} events submitted")

    return created_count, duplicate_count, failed_count, failures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert weekly matrix workbook (Google Sheets export) into v1 form events "
            "and ingest them into Spearhead API."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-xlsx", type=Path, help="Path to local workbook file")
    source.add_argument("--sheet-id", type=str, help="Google Sheet ID (downloaded via export URL)")

    parser.add_argument("--api-base-url", required=True, help="Cloud Run base URL, e.g. https://<service>.run.app")
    parser.add_argument("--api-token", default=None, help="API token (fallback: SPEARHEAD_API_TOKEN env var)")
    parser.add_argument("--company", default="Kfir", help="Company/platoon name written into payload (default: Kfir)")
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now(UTC).year,
        help="ISO year used to map sheet names like 'שבוע 7' into timestamps",
    )
    parser.add_argument("--source-prefix", default="kfir-matrix", help="Prefix used in generated source_id values")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--dry-run", action="store_true", help="Parse only; do not call API")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    workbook_path: Path
    tmp_file: tempfile.NamedTemporaryFile[str] | None = None

    try:
        if args.input_xlsx:
            workbook_path = args.input_xlsx
            if not workbook_path.exists():
                raise SystemExit(f"Input file not found: {workbook_path}")
        else:
            tmp_file = tempfile.NamedTemporaryFile(prefix="spearhead-sheet-", suffix=".xlsx", delete=False)
            workbook_path = Path(tmp_file.name)
            tmp_file.close()
            _download_sheet_xlsx(args.sheet_id, workbook_path, args.timeout)

        parsed = parse_matrix_workbook(
            workbook_path,
            company=args.company,
            year=args.year,
            source_prefix=args.source_prefix,
        )
        print(
            f"Parsed {len(parsed.events)} events from {len(parsed.sheets_processed)} weekly sheets: "
            f"{', '.join(parsed.sheets_processed) if parsed.sheets_processed else 'none'}"
        )
        if parsed.warnings:
            for warning in parsed.warnings:
                print(f"[warn] {warning}")

        if not parsed.events:
            print("No events parsed. Nothing to ingest.")
            return 0

        if args.dry_run:
            sample = parsed.events[0]
            print(f"Dry run sample source_id={sample['source_id']}")
            print(f"Dry run sample payload fields={len(sample['payload'])}")
            return 0

        token = _resolve_token(args.api_token)
        created, duplicates, failed, failures = _post_events(
            api_base_url=args.api_base_url,
            api_token=token,
            events=parsed.events,
            timeout=args.timeout,
        )
        print(
            f"Ingestion done: total={len(parsed.events)} created={created} duplicates={duplicates} failed={failed}"
        )
        if failures:
            print("Failures:")
            for line in failures[:20]:
                print(f"  - {line}")
            if len(failures) > 20:
                print(f"  ... and {len(failures) - 20} more")
            return 1
        return 0
    finally:
        if tmp_file is not None:
            try:
                Path(tmp_file.name).unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
