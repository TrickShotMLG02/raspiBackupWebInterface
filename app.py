from flask import Flask, render_template, abort, url_for
import json
import os

app = Flask(__name__)

# Path to your JSON metadata file.
JSON_FILE = "/media/Data/Backups/backup_metadata.json"
JSON_FILE = "backup_metadata.json"


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
    Display a list of all devices and backups.
    The JSON structure is expected to be a dictionary where each key is a device name and the value
    is a list of backup records.
    """
    data = load_metadata()
    return render_template("index.html", data=data)


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
    backup = None
    for b in data[device]:
        if b["name"] == backup_name:
            backup = b
            break

    if backup is None:
        abort(404, description="Backup not found.")

    if not backup.get("valid", False):
        abort(403, description="Backup is not valid; log unavailable.")

    log_file = backup.get("log_file")
    if not log_file or not os.path.exists(log_file):
        abort(404, description="Log file not found.")

    # Read the log file content.
    try:
        with open(log_file, "r") as f:
            log_content = f.read()
    except Exception as e:
        abort(500, description=f"Error reading log file: {e}")

    return render_template("view_log.html", device=device, backup=backup, log_content=log_content)


if __name__ == "__main__":
    # Run the Flask app. Adjust host/port as needed.
    app.run(debug=True, host="0.0.0.0", port=5000)
