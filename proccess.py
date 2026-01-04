import os
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



WORK_PATH = "/srv/storage/raw_footage"
