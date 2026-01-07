import os
import subprocess
import shutil
from datetime import datetime

def merge_mp4_sequence(input_files, output_file):
    """
    Merge MP4 files using mp4-merge tool
    """
    # Find mp4-merge binary (check cargo bin directory first)
    mp4_merge_path = shutil.which("mp4-merge")
    if not mp4_merge_path:
        # Check cargo bin directory (try both naming conventions)
        cargo_bin_paths = [
            os.path.expanduser("~/.cargo/bin/mp4-merge"),
            os.path.expanduser("~/.cargo/bin/mp4_merge")
        ]
        for path in cargo_bin_paths:
            if os.path.isfile(path):
                mp4_merge_path = path
                break
        
        if not mp4_merge_path:
            raise FileNotFoundError("mp4-merge not found. Please install it from https://github.com/gyroflow/mp4-merge")
    
    # Build the command
    cmd = [mp4_merge_path] + input_files + ["--out", output_file]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully merged to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error merging files: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
