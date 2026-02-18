"""JSON file-based storage adapter — implements StoragePort."""

import json
import os
import tempfile
from pathlib import Path
from typing import List


class JsonStorage:
    """File-based JSON storage implementing StoragePort protocol."""

    def __init__(self, storage_dir: str = "memory"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._storage_dir / f"{key}.json"

    def load(self, key: str) -> list:
        path = self._path(key)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except Exception:
            return []

    def save(self, key: str, data: list) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        # Atomic write
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(path))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
