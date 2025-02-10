import re
import os
import json
import sqlite3
from datetime import datetime

# Configuration
BACKUP_DIR = "/media/Data/Backups/"  # Base directory containing all device folders
JSON_FILE = "/media/Data/Backups/backup_metadata.json"  # JSON output file
DB_FILE = "/media/Data/Backups/backup_metadata.db"      # SQLite database file
LOG_FILE_NAME = "raspiBackup.log"    # Log file name inside each backup folder
FLAG_FILE_NAME = "raspiBackup.log"   # Flag file that marks a folder as a backup folder
SQL_TABLE_PREFIX = ""

#########################
# Helper Functions
#########################

def load_existing_json():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading existing JSON: {e}")
    return {}

def extract_dates_from_log(log_file):
    """
    Extract the start and end date from the log file.
    It assumes that the first and last lines contain timestamps in the format YYYYMMDD-HHMMSS.
    """
    start_date, end_date = None, None
    date_pattern = r"\d{8}-\d{6}"  # Example: 20250209-183420

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            if lines:
                # Extract date from the first line
                match_start = re.search(date_pattern, lines[0])
                if match_start:
                    start_date = match_start.group(0)
                # Extract date from the last line
                match_end = re.search(date_pattern, lines[-1])
                if match_end:
                    end_date = match_end.group(0)
    except Exception as e:
        print(f"Error reading log file {log_file}: {e}")
    return start_date, end_date

def calculate_duration(start_date, end_date):
    """Calculate the duration between start_date and end_date as a string."""
    date_format = "%Y%m%d-%H%M%S"
    start_dt = datetime.strptime(start_date, date_format)
    end_dt = datetime.strptime(end_date, date_format)
    duration = end_dt - start_dt
    return str(duration)


def get_backup_size(folder):
    total_size = 0
    for dirpath, _, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size

def generate_backup_metadata(existing_data):
    """
    For each device folder in BACKUP_DIR, check its subfolders.
    Only subfolders that contain the FLAG_FILE_NAME are considered backup folders.
    For each valid backup folder that was not yet processed, extract metadata from its log file.
    Returns a dictionary with device names as keys and dictionaries of backup metadata keyed by backup folder name.
    """
    device_backups = {}
    for device in sorted(os.listdir(BACKUP_DIR)):
        device_path = os.path.join(BACKUP_DIR, device)
        # Only consider subfolders that contain the FLAG_FILE_NAME
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
        # Use the backup folder name as unique key for each backup record.

        for backup_folder in backup_folders:
            if device in existing_data and any(b["name"] == backup_folder and b["valid"] for b in existing_data[device]):
                # copy over existing data for already captured backup metadata if it exists and is valid
                matching_backup = next((b for b in existing_data[device] if b["name"] == backup_folder), None)
                if matching_backup:
                    backups[backup_folder] = matching_backup
                continue

            backup_path = os.path.join(device_path, backup_folder)
            log_file = os.path.join(backup_path, LOG_FILE_NAME)
            if not os.path.exists(log_file):
                continue

            start_date, end_date = extract_dates_from_log(log_file)
            if not start_date or not end_date:
                continue

            backups[backup_folder] = {
                "id": None,
                "name": backup_folder,
                "start_date": start_date,
                "end_date": end_date,
                "duration": calculate_duration(start_date, end_date),
                "size": get_backup_size(backup_path),
                "log_file": log_file,
                "valid": True
            }

        if backups:
            device_backups[device] = backups
    return device_backups

def merge_backup_data(existing, current):
    """
    Merge existing backup metadata with current scan.
    For each device:
      - If a backup record is found in the current scan, update it and mark it as valid.
      - If a record exists in the old data but is not found in the current scan, mark it as not valid.
    Also, assign a new ID (only to records that have id==None) while preserving already assigned IDs.
    New backups receive an ID equal to the current maximum ID + 1.
    Returns the merged data as a dict with device names as keys and lists of backup records as values.
    """
    merged = {}
    all_devices = set(existing.keys()).union(set(current.keys()))
    for device in all_devices:
        # Build a dictionary keyed by backup name for existing data.
        existing_list = existing.get(device, [])
        existing_backups = {rec["name"]: rec for rec in existing_list}
        current_backups = current.get(device, {})

        # Mark all existing backups as invalid by default.
        for name, rec in existing_backups.items():
            rec["valid"] = False

        # Update (or add) backups found in the current scan as valid.
        for name, new_rec in current_backups.items():
            new_rec["valid"] = True
            if name in existing_backups:
                old_rec = existing_backups[name]
                # Preserve the old ID if it exists.
                if old_rec.get("id") is not None:
                    new_rec["id"] = old_rec["id"]
                # Update the record with new data (without overwriting an existing ID).
                existing_backups[name].update(new_rec)
            else:
                existing_backups[name] = new_rec

        # Determine the maximum ID among all records for this device.
        max_id = 0
        for backup in existing_backups.values():
            if backup.get("id") is not None:
                try:
                    bid = int(backup["id"])
                    if bid > max_id:
                        max_id = bid
                except ValueError:
                    pass

        # For any backup record that still has id == None, assign a new ID.
        for backup in existing_backups.values():
            if backup.get("id") is None:
                max_id += 1
                backup["id"] = max_id

        merged[device] = list(existing_backups.values())
    return merged

def save_to_json(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Backup metadata saved to {JSON_FILE}")


def save_to_sqlite(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for device, backups in data.items():
        table_name = SQL_TABLE_PREFIX + re.sub(r'\W+', '_', device)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                start_date TEXT,
                end_date TEXT,
                duration TEXT,
                log_file TEXT,
                valid INTEGER
            )
        """)

        existing_names = {row[0] for row in cursor.execute(f"SELECT name FROM {table_name}").fetchall()}
        current_names = {b["name"] for b in backups}

        for backup in backups:
            cursor.execute(f"""
                INSERT INTO {table_name} (id, name, start_date, end_date, duration, log_file, valid)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET 
                    start_date=excluded.start_date, end_date=excluded.end_date,
                    duration=excluded.duration, log_file=excluded.log_file, valid=excluded.valid
            """, (backup["id"], backup["name"], backup["start_date"], backup["end_date"], backup["duration"], backup["log_file"], 1))

        if current_names:
            cursor.execute(f"UPDATE {table_name} SET valid = 0 WHERE name NOT IN ({','.join('?' * len(current_names))})", tuple(current_names))
        else:
            cursor.execute(f"UPDATE {table_name} SET valid = 0")

    conn.commit()
    conn.close()
    print(f"Backup metadata saved to {DB_FILE}")


if __name__ == "__main__":
    old_data = load_existing_json()
    current_data = generate_backup_metadata(old_data)
    merged_data = merge_backup_data(old_data, current_data)
    save_to_json(merged_data)
    save_to_sqlite(merged_data)
    print("Backup processing complete.")
