"""Process DJI drone footage: merge split files and stabilize using Gyroflow.

Workflow:
1. Merge split DJI footage files from source into merged footage
2. Stabilize merged footage using Gyroflow

Configuration:
- Source folder: /srv/storage/_ (raw DJI footage with split files)
- Merged folder: /srv/storage/raw_footage (merged but unstabilized)
- Stabilized folder: /srv/storage/stabilized_footage (final output)
- Stabilization: 120% zoom limit, 80% horizon lock
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


# Folder configuration
source_folder = "/srv/storage/_"
merged_folder = "/srv/storage/_/merged_footage"
stabilized_folder = "/srv/storage/drone_footage"


# ============================================================================
# PART 1: MERGE SPLIT FILES
# ============================================================================

def format_dji_filename(dji_filename):
    """
    Extract timestamp from DJI filename and format as YYYY.MM.DD HH.MM
    Example: DJI_20251230055808_0001_D.MP4 -> 2025.12.30 05.58
    """
    timestamp_str = dji_filename.split('_')[1]
    year = timestamp_str[:4]
    month = timestamp_str[4:6]
    day = timestamp_str[6:8]
    hour = timestamp_str[8:10]
    minute = timestamp_str[10:12]
    return f"{year}.{month}.{day} {hour}.{minute}"


def merge_mp4(input_files, output_file):
    """Merge MP4 files using mp4-merge tool"""
    mp4_merge_path = shutil.which("mp4-merge")
    if not mp4_merge_path:
        cargo_bin_paths = [
            os.path.expanduser("~/.cargo/bin/mp4-merge"),
            os.path.expanduser("~/.cargo/bin/mp4_merge")
        ]
        for path in cargo_bin_paths:
            if os.path.isfile(path):
                mp4_merge_path = path
                break
        
        if not mp4_merge_path:
            raise FileNotFoundError("mp4-merge not found. Install from https://github.com/gyroflow/mp4-merge")
    
    cmd = [mp4_merge_path] + input_files + ["--out", output_file]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Merged to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error merging files: {e}")
        print(f"STDERR: {e.stderr}")
        return False


def list_mp4_files(folder):
    """List all MP4 files in folder, sorted by name"""
    files = [f for f in os.listdir(folder) if f.endswith('.MP4')]
    files.sort()
    return files


def get_footage_sequences(files, source_folder):
    """Group split files into sequences based on file size"""
    split_limit = 3760000000  # ~3.7GB
    max_limit = 4000000000  # ~4.0GB
    footage_files = []
    parts = []
    
    for file in files:
        file_size = os.path.getsize(os.path.join(source_folder, file))
        if file_size > max_limit:
            continue  # skip already merged files
        
        if file_size > split_limit:
            parts.append(file)
        else:
            parts.append(file)
            footage_files.append(parts)
            parts = []
    
    return footage_files


def merge_sequences(source_folder, target_folder):
    """Merge split DJI footage files into single files"""
    source_files = list_mp4_files(source_folder)
    footage_sequences = get_footage_sequences(source_files, source_folder)
    
    print(f"\n{'='*80}")
    print(f"STEP 1: MERGING SPLIT FILES")
    print(f"{'='*80}")
    print(f"Found {len(footage_sequences)} sequences to process\n")
    
    for idx, seq in enumerate(footage_sequences, start=1):
        output_filename = format_dji_filename(seq[0]) + ".mp4"
        output_path = os.path.join(target_folder, output_filename)
        
        print(f"\n-- {idx}/{len(footage_sequences)} " + "-" * 70)
        
        if os.path.exists(output_path):
            print(f"- Skip (exists): {output_filename}")
            continue
        
        input_files = [os.path.join(source_folder, f) for f in seq]
        print(f"* Processing: {output_filename}")
        print(f"  Input files: {len(input_files)}")
        
        # Single file: just rename
        if len(input_files) == 1:
            print(f"  Single file, moving...")
            os.rename(input_files[0], output_path)
            print(f"✓ Moved to {output_path}")
            continue
        
        # Multiple files: merge
        print(f"  Merging {len(input_files)} files...")
        merge_mp4(input_files, output_path)


# ============================================================================
# PART 2: STABILIZE WITH GYROFLOW
# ============================================================================

@dataclass(frozen=True)
class StabilizationParams:
    zoom_limit_percent: float = 120.0
    horizon_lock_percent: float = 80.0


def find_gyroflow_binary() -> str:
    """Find Gyroflow executable"""
    here = Path(__file__).resolve().parent
    bundled = here / "Gyroflow" / "gyroflow"
    if bundled.is_file() and os.access(bundled, os.X_OK):
        return str(bundled)
    
    found = shutil.which("gyroflow")
    if found:
        return found
    
    raise FileNotFoundError(
        "Gyroflow binary not found. Expected ./Gyroflow/gyroflow or 'gyroflow' on PATH."
    )


def to_file_uri(folder: Path) -> str:
    """Convert folder path to file:// URI"""
    return folder.resolve().as_uri().rstrip("/") + "/"


def build_preset(params: StabilizationParams) -> str:
    """Build Gyroflow preset JSON"""
    preset = {
        "stabilization": {
            "max_zoom": float(params.zoom_limit_percent),
            "horizon_lock_amount": float(params.horizon_lock_percent) / 100.0,
        }
    }
    return json.dumps(preset, separators=(",", ":"))


def build_out_params(target_dir: Path, output_filename: str) -> str:
    """Build Gyroflow output parameters JSON"""
    out_params = {
        "output_folder": to_file_uri(target_dir),
        "output_filename": output_filename,
        "use_gpu": False,
        "codec": "H.264/AVC",
        "pixel_format": "YUV420P",
    }
    return json.dumps(out_params, separators=(",", ":"))


def stabilize_file(
    *,
    gyroflow_bin: str,
    input_path: Path,
    target_dir: Path,
    params: StabilizationParams,
    overwrite: bool,
) -> None:
    """Stabilize a single video file using Gyroflow"""
    output_path = target_dir / input_path.name
    tmp_output_path = output_path.with_suffix(output_path.suffix + ".tmp")
    
    if output_path.exists() and not overwrite:
        print(f"- Skip (exists): {output_path.name}")
        return
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if overwrite:
        output_path.unlink(missing_ok=True)
        tmp_output_path.unlink(missing_ok=True)
    
    cmd = [
        gyroflow_bin,
        str(input_path),
        "--preset",
        build_preset(params),
        "--out-params",
        build_out_params(target_dir, input_path.name),
        "--parallel-renders", "1",
        "--no-gpu-decoding",
    ]
    if overwrite:
        cmd.append("--overwrite")
    
    print(f"* Stabilizing: {input_path.name}")
    subprocess.run(cmd, check=True)
    
    if not output_path.exists() or output_path.stat().st_size == 0:
        if tmp_output_path.exists() and tmp_output_path.stat().st_size == 0:
            tmp_output_path.unlink(missing_ok=True)
        raise RuntimeError(f"Gyroflow failed to produce valid output: {output_path}")
    
    print(f"✓ Wrote: {output_path}")


def stabilize_footage(source_folder, target_folder):
    """Stabilize all MP4 files using Gyroflow"""
    source_files = [
        f for f in os.listdir(source_folder) if f.lower().endswith(".mp4")
    ]
    
    print(f"\n{'='*80}")
    print(f"STEP 2: STABILIZING FOOTAGE")
    print(f"{'='*80}")
    print(f"Found {len(source_files)} files to stabilize\n")
    
    gyroflow_bin = find_gyroflow_binary()
    params = StabilizationParams()
    target_dir = Path(target_folder)
    
    for idx, filename in enumerate(source_files, start=1):
        print(f"\n-- {idx}/{len(source_files)} " + "-" * 70)
        
        if (target_dir / filename).exists():
            print(f"- Skip (exists): {filename}")
            continue
        
        input_path = Path(source_folder) / filename
        stabilize_file(
            gyroflow_bin=gyroflow_bin,
            input_path=input_path,
            target_dir=target_dir,
            params=params,
            overwrite=False,
        )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\nDJI FOOTAGE PROCESSING PIPELINE")
    print("=" * 80)
    
    # Step 1: Merge split files
    merge_sequences(source_folder, merged_folder)
    
    # Step 2: Stabilize merged footage
    stabilize_footage(merged_folder, stabilized_folder)
    
    print(f"\n{'='*80}")
    print("PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Final output: {stabilized_folder}\n")
