from flask import Flask, render_template, abort, url_for, request
import json
import os
from datetime import datetime

import backup_metadata_generator

app = Flask(__name__)

# Path to your JSON metadata file.
JSON_FILE = "backup_metadata.json"
BACKUPS_PATH = "/media/Data/Backups/"


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


@app.route('/device/<device>/backup/<backup_name>/tree/')
def view_backup_tree(device, backup_name):
    base_backup_path = os.path.join(BACKUPS_PATH, device, backup_name)

    data = load_metadata()

    if not os.path.exists(base_backup_path):
        return "Backup not found", 404

    # Get the directory path from the query parameters (if available)
    current_path = request.args.get('path', "/")  # Defaults to the root of the backup

    if not os.path.exists(os.path.join(base_backup_path, current_path)):
        return "Directory not found", 404

    # Generate the file tree for the current directory
    file_tree = generate_file_tree(device, backup_name, current_path)

    return render_template('view_backup_tree.html', data=data, selected_device=device, backup_name=backup_name,
                           file_tree=file_tree, current_path=current_path)


@app.route('/device/<device>/backup/<backup_name>/file/')
def view_backup_file(device, backup_name):
    base_backup_path = os.path.join(BACKUPS_PATH, device, backup_name)

    data = load_metadata()

    # Get the relative path to the file from the query parameters
    relative_path = request.args.get('path', "")

    # Construct the full file path
    full_file_path = os.path.join(base_backup_path, relative_path)

    # Check if the file exists
    if not os.path.exists(full_file_path) or not os.path.isfile(full_file_path):
        return "File not found", 404

    # Read the file content (you can modify this based on file type, e.g., for binary files)
    try:
        with open(full_file_path, 'r') as file:
            file_content = file.read()
    except Exception as e:
        return f"Error reading file: {e}", 500

    # Render the file content to the template
    return render_template('view_backup_file.html', data=data, selected_device=device, backup_name=backup_name,
                           file_content=file_content, rel_path=relative_path)


def generate_file_tree(device, backup_name, rel_path):
    """
    Generate a file tree (directories only) for the given directory.
    Only shows current directory contents.
    """
    file_tree = []
    backup_base_path = os.path.join(os.path.join(BACKUPS_PATH, device), backup_name)
    full_path = os.path.join(backup_base_path, rel_path)

    items = sorted(os.listdir(full_path))  # Sort the files and directories

    for item in items:
        item_path = os.path.join(full_path, item)

        if os.path.isdir(item_path):
            file_tree.append({
                'type': 'directory',
                'name': item,
                'path': item_path
            })
        else:
            file_tree.append({
                'type': 'file',
                'name': item,
                'path': item_path
            })

    return file_tree


if __name__ == "__main__":
    backup_metadata_generator.run_metadata_generator()
    app.run(host="0.0.0.0", debug=True, port=5486)
