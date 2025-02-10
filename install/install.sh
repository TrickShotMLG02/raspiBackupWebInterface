#!/bin/bash

# Define source file paths
INITD_FILE="RaspiBackupWebInterface"
SYSTEMD_FILE="RaspiBackupWebInterface.service"

# Define target paths
INITD_TARGET="/etc/init.d/RaspiBackupWebInterface"
SYSTEMD_TARGET="/etc/systemd/system/RaspiBackupWebInterface.service"

# Copy the SysVinit script
if [ -f "$INITD_FILE" ]; then
    sudo cp "$INITD_FILE" "$INITD_TARGET"
    sudo chmod +x "$INITD_TARGET"
    sudo update-rc.d RaspiBackupWebInterface defaults
    echo "Copied and configured SysVinit script."
else
    echo "Error: $INITD_FILE not found!"
fi

# Copy the systemd service file
if [ -f "$SYSTEMD_FILE" ]; then
    sudo cp "$SYSTEMD_FILE" "$SYSTEMD_TARGET"
    sudo systemctl daemon-reload
    sudo systemctl enable RaspiBackupWebInterface.service
    echo "Copied and enabled systemd service."
else
    echo "Error: $SYSTEMD_FILE not found!"
fi

echo "Setup complete!"
