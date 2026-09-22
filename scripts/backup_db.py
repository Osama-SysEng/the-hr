#!/usr/bin/env python
"""The H.R - Backup Database Script"""
import subprocess
import os
from datetime import datetime

BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
DB_USER = os.environ.get("POSTGRES_USER", "hr_user")
DB_NAME = os.environ.get("POSTGRES_DB", "thehr")
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")


def backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    filename = f"{BACKUP_DIR}/{DB_NAME}_{TIMESTAMP}.sql"
    cmd = f"pg_dump -h {DB_HOST} -U {DB_USER} -d {DB_NAME} -F c -f {filename}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Backup created: {filename}")
    else:
        print(f"Backup failed: {result.stderr}")
    return filename


if __name__ == "__main__":
    backup()
