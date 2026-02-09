from __future__ import annotations

import json
import logging

from spearhead.config import settings
from spearhead.data.storage import Database
from spearhead.v1.worker import reconcile_snapshots

logger = logging.getLogger(__name__)


def main() -> int:
    db = Database(settings.paths.db_path)
    result = reconcile_snapshots(db)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
