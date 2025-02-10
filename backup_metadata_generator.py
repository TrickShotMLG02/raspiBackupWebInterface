import re
import os
import json
import sqlite3
from datetime import datetime

# Configuration
BACKUP_DIR = "/media/Data/Backups/"
JSON_FILE = "/media/Data/Backups/backup_metadata.json"
DB_FILE = "/media/Data/Backups/backup_metadata.db"
LOG_FILE_NAME = "raspiBackup.log"
FLAG_FILE_NAME = "raspiBackup.log"
SQL_TABLE_PREFIX = ""

def extract_dates_from_log(log_file):
    start_date, end_date = None, None
    date_pattern = r"\d{8}-\d{6}"
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            if lines:
                match_start = re.search(date_pattern, lines[0])
                if match_start:
                    start_date = match_start.group(0)
                match_end = re.search(date_pattern, lines[-1])
                if match_end:
                    end_date = match_end.group(0)
    except Exception as e:
        print(f"Error reading log file {log_file}: {e}")
    return start_date, end_date

def get_backup_size(folder):
    total_size = 0
    for dirpath, _, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size

def generate_backup_metadata():
    device_backups = {}
    for device in sorted(os.listdir(BACKUP_DIR)):
        device_path = os.path.join(BACKUP_DIR, device)
        if not os.path.isdir(device_path):
            continue
        backup_folders = sorted([
            b for b in os.listdir(device_path)
            if os.path.isdir(os.path.join(device_path, b)) and os.path.exists(os.path.join(device_path, b, FLAG_FILE_NAME))
        ])
        if not backup_folders:
            print(f"{device_path} does not contain any valid backup folders. Skipping...")
            continue
        backups = {}
        for backup_folder in backup_folders:
            backup_path = os.path.join(device_path, backup_folder)
            log_file = os.path.join(backup_path, LOG_FILE_NAME)
            if not os.path.exists(log_file):
                print(f"Skipping {backup_folder} in device {device}: No log file found.")
                continue
            start_date, end_date = extract_dates_from_log(log_file)
            if not start_date or not end_date:
                print(f"Skipping {backup_folder} in device {device}: Could not extract dates from log.")
                continue
            backup_size = get_backup_size(backup_path)
            duration = str(datetime.strptime(end_date, "%Y%m%d-%H%M%S") - datetime.strptime(start_date, "%Y%m%d-%H%M%S"))
            backups[backup_folder] = {
                "id": None,
                "name": backup_folder,
                "start_date": start_date,
                "end_date": end_date,
                "duration": duration,
                "size": backup_size,
                "log_file": log_file,
                "valid": True
            }
        if backups:
            device_backups[device] = backups
    return device_backups

def save_to_sqlite(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for device, backups in data.items():
        table_name = SQL_TABLE_PREFIX + re.sub(r'\W+', '_', device)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                duration TEXT,
                size INTEGER,
                log_file TEXT NOT NULL,
                valid INTEGER
            )
        """)
        for backup in backups.values():
            valid_flag = 1 if backup["valid"] else 0
            cursor.execute(f"""
                INSERT INTO {table_name} (name, start_date, end_date, duration, size, log_file, valid)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    start_date=excluded.start_date,
                    end_date=excluded.end_date,
                    duration=excluded.duration,
                    size=excluded.size,
                    log_file=excluded.log_file,
                    valid=excluded.valid
            """, (backup["name"], backup["start_date"], backup["end_date"], backup["duration"], backup["size"], backup["log_file"], valid_flag))
    conn.commit()
    conn.close()
    print(f"Backup metadata saved to {DB_FILE}")

if __name__ == "__main__":
    backup_data = generate_backup_metadata()
    save_to_sqlite(backup_data)
    with open(JSON_FILE, "w") as f:
        json.dump(backup_data, f, indent=4)
    print("Backup processing complete.")