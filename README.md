# RaspiBackup Web Interface

This project provides a web interface to browse and manage backups created using `raspiBackup`. The web interface allows users to view backup contents, check file sizes, and navigate backup directories.

## Installation

### Prerequisites
- Raspberry Pi running a Linux-based OS
- `raspiBackup` installed (https://bangertech.de/raspibackup-einfaches-backup-fuer-den-raspberry-pi/) (https://github.com/framps/raspiBackup)
- Python 3.12 or higher (pyenv: sudo curl -fsSL https://pyenv.run | bash)
- Virtual environment tools (`pipenv` recommended)
- Flask and other dependencies

### Setup
1. Clone this repository:
   ```sh
   git clone https://github.com/your-repo/raspiBackupWebInterface.git
   cd raspiBackupWebInterface
   ```
   
2. Create and activate a virtual environment:
    ```sh
    pipenv install
    pipenv shell
    ```
   or
3. 
   ```sh
    pipenv shell
    pip install flask
    ```

3. Install services:
   ```sh
   sudo ./install/install.sh
   ```

## Usage
   ### Start/Stop/Status Web Interface Service
   ```sh
   sudo systemctl start/stop/status raspiBackupWebInterface
   ```

   

# Preview
![alt-text](https://i.imgur.com/I8zZOVP.png)
![alt-text](https://i.imgur.com/qxtmelj.png)
![alt-text](https://i.imgur.com/VULDbG2.png)
![alt-text](https://i.imgur.com/dIFSjPk.png)
