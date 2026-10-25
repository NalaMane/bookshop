"""Lab 2 – moving ERP files between the exchange folders (owner: Ami).

    erp_exchange/inbox/      new files from the ERP, waiting to be imported
    erp_exchange/processed/  imported files (kept as a record of what was transferred)
    erp_exchange/failed/     files that could not be imported at all

Naming convention: products_YYYY-MM-DD_HHMMSS.xlsx (time of the import),
so files never overwrite each other and the same file is never imported twice.
"""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings

INBOX = "inbox"
PROCESSED = "processed"
FAILED = "failed"


def exchange_folder(name):
    folder = Path(settings.ERP_EXCHANGE_DIR) / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def inbox_files():
    """All files waiting in the inbox, oldest first (the order they arrived)."""
    files = [path for path in exchange_folder(INBOX).iterdir()
             if path.is_file() and not path.name.startswith(".")]
    return sorted(files, key=lambda path: path.stat().st_mtime)


def move_file(path, folder_name):
    """Move a file to processed/ or failed/ with a timestamped name. Returns the new path."""
    path = Path(path)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = exchange_folder(folder_name) / f"products_{stamp}{path.suffix.lower()}"
    counter = 1
    while target.exists():  # two files in the same second
        target = target.with_name(f"products_{stamp}_{counter}{path.suffix.lower()}")
        counter += 1
    shutil.move(str(path), str(target))
    return target
