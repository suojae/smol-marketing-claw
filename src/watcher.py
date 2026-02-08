"""File system watcher for OS-level push events."""

from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.config import event_queue


class GitFileHandler(FileSystemEventHandler):
    """Watches filesystem and pushes events to the queue (no polling)"""

    def __init__(self, loop, debounce_seconds=3.0):
        self._loop = loop
        self._debounce_seconds = debounce_seconds
        self._last_event_time = None

    def _should_ignore(self, path: str) -> bool:
        ignore_patterns = [".git/", "__pycache__/", ".pyc", ".swp", ".tmp", "node_modules/"]
        return any(p in path for p in ignore_patterns)

    def _emit(self, path: str, change_type: str):
        now = datetime.now()
        if self._last_event_time and (now - self._last_event_time).total_seconds() < self._debounce_seconds:
            return
        self._last_event_time = now
        filename = Path(path).name
        event = {"type": "file_changed", "detail": f"{filename} {change_type}"}
        self._loop.call_soon_threadsafe(event_queue.put_nowait, event)

    def on_modified(self, event):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._emit(event.src_path, "modified")

    def on_created(self, event):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._emit(event.src_path, "created")


def start_file_watcher(loop):
    """Start OS-level file watcher on the project directory"""
    watch_path = str(Path.home() / "Documents")
    handler = GitFileHandler(loop)
    observer = Observer()
    observer.schedule(handler, watch_path, recursive=True)
    observer.daemon = True
    observer.start()
    print(f"File watcher started: {watch_path}")
