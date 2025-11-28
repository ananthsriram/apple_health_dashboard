# Apple Health Dashboard Configuration
import getpass

# Path to your Apple Health export directory
# Update this path whenever you export new data
DATA_DIR = '/Users/' + getpass.getuser() + '/Downloads/apple_health_export'

# You can also use an environment variable:
# import os
# DATA_DIR = os.getenv('HEALTH_DATA_DIR', '/Users/ananthsrivalli/Downloads/apple_health_export')

# Process the new data:
# cd $DATA_DIR
# venv/bin/python process_data.py
