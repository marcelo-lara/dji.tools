"""Batch-stabilize drone footage using Gyroflow.

Expected behavior (from the original comments):
- Stabilize all videos from source_folder into target_folder
- Stabilization parameters:
  - Zoom Limit: 120%
  - Horizon lock: 80%
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


source_folder = "/srv/storage/raw_footage"
target_folder = "/srv/storage/stabilized_footage"


@dataclass(frozen=True)
class StabilizationParams:
	zoom_limit_percent: float = 120.0
	horizon_lock_percent: float = 80.0


def _find_gyroflow_binary() -> str:
	here = Path(__file__).resolve().parent
	bundled = here / "Gyroflow" / "gyroflow"
	if bundled.is_file() and os.access(bundled, os.X_OK):
		return str(bundled)

	found = shutil.which("gyroflow")
	if found:
		return found

	raise FileNotFoundError(
		"Gyroflow binary not found. Expected ./Gyroflow/gyroflow next to this script "
		"or 'gyroflow' available on PATH."
	)


def _to_file_uri(folder: Path) -> str:
	# Gyroflow projects store folders as file:// URIs.
	# Ensure a trailing slash to match Gyroflow's typical output_folder format.
	return folder.resolve().as_uri().rstrip("/") + "/"


def _build_preset(params: StabilizationParams) -> str:
	# Based on an exported .gyroflow project from Gyroflow 1.6.3:
	# - stabilization.max_zoom is expressed as percent (e.g. 130.0 == 130%)
	# - stabilization.horizon_lock_amount is in [0..1]
	preset = {
		"stabilization": {
			"max_zoom": float(params.zoom_limit_percent),
			"horizon_lock_amount": float(params.horizon_lock_percent) / 100.0,
		}
	}
	return json.dumps(preset, separators=(",", ":"))


def _build_out_params(target_dir: Path, output_filename: str) -> str:
	out_params = {
		"output_folder": _to_file_uri(target_dir),
		"output_filename": output_filename,
		# Defaults in user settings can try NVENC/VDPAU and fail on headless hosts.
		# Set safe defaults to reliably produce output files.
		"use_gpu": False,
		"codec": "H.264/AVC",
		"pixel_format": "YUV420P",
	}
	return json.dumps(out_params, separators=(",", ":"))


def stabilize_one(
	*,
	gyroflow_bin: str,
	input_path: Path,
	target_dir: Path,
	params: StabilizationParams,
	overwrite: bool,
	parallel_renders: int = 1,
	no_gpu_decoding: bool = True,
) -> None:
	output_path = target_dir / input_path.name
	tmp_output_path = output_path.with_suffix(output_path.suffix + ".tmp")
	if output_path.exists() and not overwrite:
		print(f"- Skip (exists): {output_path}")
		return

	target_dir.mkdir(parents=True, exist_ok=True)

	if overwrite:
		output_path.unlink(missing_ok=True)
		tmp_output_path.unlink(missing_ok=True)

	cmd = [
		gyroflow_bin,
		str(input_path),
		"--preset",
		_build_preset(params),
		"--out-params",
		_build_out_params(target_dir, input_path.name),
		"--parallel-renders",
		str(parallel_renders),
	]
	if overwrite:
		cmd.append("--overwrite")
	if no_gpu_decoding:
		cmd.append("--no-gpu-decoding")

	print(f"* Stabilizing: {input_path.name}")
	subprocess.run(cmd, check=True)

	# Gyroflow writes to a .tmp file and renames on success. If encoding fails,
	# it can leave a 0-byte .tmp behind.
	if not output_path.exists() or output_path.stat().st_size == 0:
		if tmp_output_path.exists() and tmp_output_path.stat().st_size == 0:
			tmp_output_path.unlink(missing_ok=True)
		raise RuntimeError(f"Gyroflow did not produce a valid output file: {output_path}")

	print(f"✓ Wrote: {output_path}")


def main() -> int:
	parser = argparse.ArgumentParser(description="Stabilize videos using Gyroflow")
	parser.add_argument("--source", default=source_folder, help="Source folder with input .mp4 files")
	parser.add_argument("--target", default=target_folder, help="Target folder for stabilized .mp4 files")
	parser.add_argument("--overwrite", action="store_true", help="Overwrite outputs if they already exist")
	parser.add_argument(
		"--parallel-renders",
		type=int,
		default=1,
		help="Gyroflow parallel renders (maps to --parallel-renders)",
	)
	parser.add_argument(
		"--zoom-limit",
		type=float,
		default=120.0,
		help="Zoom limit in percent (e.g. 120 for 120%%)",
	)
	parser.add_argument(
		"--horizon-lock",
		type=float,
		default=80.0,
		help="Horizon lock strength in percent (e.g. 80 for 80%%)",
	)
	parser.add_argument(
		"--gpu-decoding",
		action="store_true",
		help="Allow GPU decoding (by default it's disabled for headless compatibility)",
	)
	args = parser.parse_args()

	src = Path(args.source)
	dst = Path(args.target)

	if not src.is_dir():
		raise SystemExit(f"Source folder does not exist: {src}")

	gyroflow_bin = _find_gyroflow_binary()
	params = StabilizationParams(
		zoom_limit_percent=float(args.zoom_limit),
		horizon_lock_percent=float(args.horizon_lock),
	)

	videos = sorted([p for p in src.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"])
	if not videos:
		print(f"No .mp4 files found in {src}")
		return 0

	print(f"Gyroflow: {gyroflow_bin}")
	print(f"Inputs: {len(videos)} file(s) from {src}")
	print(f"Outputs: {dst}")
	print(f"Zoom limit: {params.zoom_limit_percent:.1f}%")
	print(f"Horizon lock: {params.horizon_lock_percent:.1f}%")

	for video in videos:
		stabilize_one(
			gyroflow_bin=gyroflow_bin,
			input_path=video,
			target_dir=dst,
			params=params,
			overwrite=bool(args.overwrite),
			parallel_renders=int(args.parallel_renders),
			no_gpu_decoding=not bool(args.gpu_decoding),
		)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())



