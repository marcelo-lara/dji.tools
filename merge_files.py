import os

from proccess import merge_mp4_sequence as merge_mp4_files

source_folder = "/srv/storage/_"
target_folder = "/srv/storage/raw_footage"


# list mp4 files in source folder sorted by name 
# the ones that are around 3.6GB and smaller than 4.0GB (assumed split files) needs to be merged with the next file(s)
# the final file in the sequence is smaller than 3.7GB

def format_dji_filename(dji_filename):
    """
    Extract timestamp from DJI filename and format as YYYY.MM.DD_HH.MM
    Example: DJI_20251230055808_0001_D.MP4 -> 2025.12.30_05.58
    """
    # Extract the timestamp part: DJI_20251230055808_0001_D.MP4 -> 20251230055808
    timestamp_str = dji_filename.split('_')[1]  # Get the YYYYMMDDHHMMSS part
    
    # Parse the timestamp: 20251230055808 -> year=2025, month=12, day=30, hour=05, minute=58, second=08
    year = timestamp_str[:4]
    month = timestamp_str[4:6]
    day = timestamp_str[6:8]
    hour = timestamp_str[8:10]
    minute = timestamp_str[10:12]
    
    return f"{year}.{month}.{day} {hour}.{minute}"


def list_mp4_files(folder):
    files = [f for f in os.listdir(folder) if f.endswith('.MP4')]
    files.sort()
    return files

# get an array of mp4 files that are a single sequence (split files grouped together, final file last)
def get_footage_sequences(files):
    split_limit = 3760000000  # ~3.7GB
    max_limit = 4000000000  # ~4.0GB
    footage_files = []

    parts = []
    for file in files:
        file_size = os.path.getsize(os.path.join(source_folder, file))
        if file_size > max_limit:
            continue  # skip larger files (already joined)

        if file_size > split_limit:
            parts.append(file)
        else:
            parts.append(file)
            footage_files.append(parts)
            parts = []

    return footage_files

def merge_mp4_sequence(source_folder, target_folder):
    """
    Merge MP4 files using mp4-merge tool
    """
    source_files = list_mp4_files(source_folder)
    footage_sequences = get_footage_sequences(source_files)

    # print(f":: Merging {len(footage_sequences)} sequences...")
    # for seq in footage_sequences:
    #     output_filename = format_dji_filename(seq[0]) + ".mp4"
    #     print(f"\t{output_filename}: {seq}")

    # Merge sequences into one file each in the target folder
    for idx, seq in enumerate(footage_sequences):
        output_filename = format_dji_filename(seq[0]) + ".mp4"
        output_path = os.path.join(target_folder, output_filename)

        input_files = [os.path.join(source_folder, f) for f in seq]
        print(f"\n-- {idx+1}/{len(footage_sequences)}---------------------------------------------------------------------------")
        print(f"Merging {len(input_files)} files into {output_path}...")
        print(f"Input files: {input_files}")
        print(f"Output file: {output_path}")

        if os.path.exists(output_path):
            print(f"- Skip (exists): {output_path}")
            continue

        # if therete is only one file, just copy it with the new name
        if len(input_files) == 1:
            print(f".. Only one file, copying to {output_path}...")
            os.rename(input_files[0], output_path)
            continue 
        
        #merge using mp4-merge tool
        merge_mp4_files(input_files, output_path)
        
if __name__ == "__main__":
    merge_mp4_sequence(source_folder, target_folder)