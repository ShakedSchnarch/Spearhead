from __future__ import annotations

import logging
from datetime import UTC, datetime

from spearhead.data.storage import Database
from spearhead.v1.parser import FormResponseParserV2
from spearhead.v1.service import ResponseIngestionServiceV2, ResponseQueryServiceV2
from spearhead.v1.store import ResponseStore

logger = logging.getLogger(__name__)


def build_worker(db: Database) -> ResponseIngestionServiceV2:
    store = ResponseStore(db=db)
    query = ResponseQueryServiceV2(store=store)
    parser = FormResponseParserV2()
    return ResponseIngestionServiceV2(store=store, parser=parser, metrics=query)


def reconcile_snapshots(db: Database) -> dict:
    """
    Rebuilds read-model snapshots from normalized rows.
    Intended for scheduled worker execution.
    """
    store = ResponseStore(db=db)
    query = ResponseQueryServiceV2(store=store)
    weeks = store.list_weeks()
    for week in weeks:
        query.refresh_snapshots(week_id=week, platoon_key=None)

    result = {
        "reconciled_weeks": len(weeks),
        "at": datetime.now(UTC).isoformat(),
    }
    logger.info("snapshot reconciliation complete", extra=result)
    return result
