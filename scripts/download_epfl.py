"""
Download script for the EPFL CVLab hippocampus EM dataset.

Usage:
    python scripts/download_epfl.py           # download center crop
    python scripts/download_epfl.py --full    # download full volume
"""

import argparse
import json
import requests
import tifffile
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Direct download URL for the multipage TIFF
DOWNLOAD_URL = "https://documents.epfl.ch/groups/c/cv/cvlab-unit/www/data/%20ElectronMicroscopy_Hippocampus/volumedata.tif"

# Known metadata from the dataset webpage
KNOWN_METADATA = {
    "dataset": "EPFL CVLab Hippocampus",
    "source": DOWNLOAD_URL,
    "format": "Multipage TIFF",
    "full_resolution_shape_zyx": [1065, 2048, 1536],
    "resolution_zyx_nm": [5.0, 5.0, 5.0],
    "units": ["nanometer", "nanometer", "nanometer"],
    "axes": ["z", "y", "x"],
    "specimen": "CA1 hippocampus",
    "physical_size_um": [5.0, 5.0, 5.0],
}

CROP_SIZE = 1000

OUTPUT_DIR = Path("data/raw/epfl")
METADATA_DIR = Path("metadata")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

TIFF_PATH = OUTPUT_DIR / "volumedata.tif"


def download_tiff():
    """Download the TIFF file with a progress bar."""
    if TIFF_PATH.exists():
        print(f"TIFF already exists at {TIFF_PATH}, skipping download.")
        return

    print(f"Downloading from {DOWNLOAD_URL}...")
    response = requests.get(DOWNLOAD_URL, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    with open(TIFF_PATH, "wb") as f, tqdm(
        total=total_size, unit="B", unit_scale=True, desc="Downloading"
    ) as progress:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            progress.update(len(chunk))

    print(f"TIFF saved to {TIFF_PATH}")


def get_crop_slices(shape, crop_size):
    """Calculate slices to crop the center of the volume."""
    slices = []
    for dim in shape:
        if dim <= crop_size:
            slices.append(slice(0, dim))
        else:
            center = dim // 2
            start = center - crop_size // 2
            stop = start + crop_size
            slices.append(slice(start, stop))
    return tuple(slices)


def extract_metadata(arr):
    """Combine known metadata with dtype extracted from the loaded array."""
    metadata = KNOWN_METADATA.copy()
    metadata["dtype"] = str(arr.dtype)
    metadata["full_resolution_shape_zyx"] = list(arr.shape)

    metadata_path = METADATA_DIR / "epfl_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to {metadata_path}")
    return metadata


def load_and_save(full=False):
    """Load the TIFF and save either the full volume or a center crop."""
    print("Loading TIFF file...")
    arr = tifffile.imread(TIFF_PATH)
    print(f"Loaded array shape: {arr.shape}, dtype: {arr.dtype}")

    metadata = extract_metadata(arr)
    print(json.dumps(metadata, indent=2))

    if full:
        data = arr
        filename = "full_volume.npy"
        print("Saving full volume...")
    else:
        slices = get_crop_slices(arr.shape, CROP_SIZE)
        data = arr[slices]
        size_str = "x".join(str(s.stop - s.start) for s in slices)
        filename = f"crop_center_{size_str}.npy"
        print(f"Saving center crop with slices {slices}...")

    output_path = OUTPUT_DIR / filename
    np.save(output_path, data)
    print(f"Saved to {output_path}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Download EPFL CVLab hippocampus EM dataset")
    parser.add_argument("--full", action="store_true", help="Save full volume instead of center crop")
    args = parser.parse_args()

    download_tiff()
    data = load_and_save(full=args.full)
    print(f"\nDone. Final array shape: {data.shape}, dtype: {data.dtype}")


if __name__ == "__main__":
    main()