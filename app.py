from flask import Flask, render_template, abort, url_for
import json
import os
from datetime import datetime

import backup_metadata_generator

app = Flask(__name__)

# Path to your JSON metadata file.
JSON_FILE = "backup_metadata.json"

# Filters Start

def format_size(bytes_size):
    """Convert bytes to a human-readable format (KB, MB, GB, etc.)."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def formatTimestamp(timestamp):
    """Convert timestamp to human-readable one"""
    dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
    formatted_timestamp = dt.strftime("%d.%m.%Y %H:%M:%S")
    return formatted_timestamp

app.jinja_env.filters['filesizeformat'] = format_size  # Register filter
app.jinja_env.filters['timestampformat'] = formatTimestamp

# Filters End

def load_metadata():
    """Load backup metadata from the JSON file."""
    if not os.path.exists(JSON_FILE):
        return {}
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON metadata: {e}")
        return {}

@app.route("/")
def index():
    """
    Home route.
    If no device is selected, the main content will show a placeholder message.
    """
    data = load_metadata()
    return render_template("index.html", data=data, selected_device=None, backups=None)

@app.route("/device/<device>")
def device_view(device):
    """
    Display backups for a specific device.
    If the device does not exist in the metadata, an empty backup list is passed.
    """
    data = load_metadata()
    backups = data.get(device, [])
    return render_template("index.html", data=data, selected_device=device, backups=backups)

@app.route("/device/<device>/backup/<backup_name>/log")
def view_log(device, backup_name):
    """
    Display the log file content for a given backup on a device,
    but only if the backup is marked as valid.
    """
    data = load_metadata()
    if device not in data:
        abort(404, description="Device not found.")
    # Find the backup record by its name.
    backup = next((b for b in data[device] if b["name"] == backup_name), None)
    if backup is None:
        abort(404, description="Backup not found.")
    if not backup.get("valid", False):
        abort(403, description="Backup is not valid; log unavailable.")
    log_file = backup.get("log_file")
    if not log_file or not os.path.exists(log_file):
        abort(404, description="Log file not found.")
    try:
        with open(log_file, "r") as f:
            log_content = f.read()
    except Exception as e:
        abort(500, description=f"Error reading log file: {e}")
    return render_template("view_log.html", data=data, selected_device=device, backup=backup, log_content=log_content)

if __name__ == "__main__":
    backup_metadata_generator.run_metadata_generator()
    app.run(host="0.0.0.0", debug=True, port=5486)
