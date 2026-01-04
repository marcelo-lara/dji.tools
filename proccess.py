import os
import subprocess
import shutil

DRONE_DRIVE = "/mnt/usb/DCIM/DJI_001"
TARGET_PATH = "/srv/storage/raw_footage"

# 1. Merge split footage from drone drive to local storage

## 1.1 get drone files 
raw_files = sorted(os.listdir(DRONE_DRIVE))

## 1.2 check file sizes and determine if split or final part
split_limit = 3760000000  # ~3.7GB
max_limit = 4000000000  # ~4.0GB
footage_files = []

parts = []
for file in raw_files:
    file_size = os.path.getsize(os.path.join(DRONE_DRIVE, file))
    if file_size > max_limit or (not file.startswith('DJI_')):
        continue  # skip larger files (already joined) or metadata files

    print(f"{file}: {file_size} bytes")
    if file_size > split_limit:
        #print(f"\tsplitted part...")
        parts.append(file)
    else:
        parts.append(file)
        footage_files.append(parts)
        parts = []
        print(f"\tfinal part or single part.")

print(f":: Identified {len(footage_files)} footage sequences.")
for seq in footage_files:
    print(f"\tSequence: {seq}")

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

# Create target directory if it doesn't exist
os.makedirs(TARGET_PATH, exist_ok=True)

# Process each footage sequence
for i, sequence in enumerate(footage_files):
    if len(sequence) > 1:  # Only merge if there are multiple parts
        # Build full paths for input files
        input_paths = [os.path.join(DRONE_DRIVE, file) for file in sequence]
        
        # Generate output filename
        base_name = sequence[0].split('.')[0]  # Get base name without extension
        output_file = os.path.join(TARGET_PATH, f"{base_name}_merged.mp4")
        
        print(f"Merging sequence {i+1}: {sequence}")
        if merge_mp4_sequence(input_paths, output_file):
            print(f"✓ Merged {len(sequence)} parts into {output_file}")
        else:
            print(f"✗ Failed to merge sequence {i+1}")
    else:
        # Single file, just copy it
        source = os.path.join(DRONE_DRIVE, sequence[0])
        dest = os.path.join(TARGET_PATH, sequence[0])
        shutil.copy2(source, dest)
        print(f"✓ Copied single file: {sequence[0]}")
