"""
Download script for the IDR idr0086-miron-micrographs FIB-SEM dataset.
Image ID 9846137 (U2OS chromatin, 20x20x20nm FIB-SEM).

Usage:
    python scripts/download_idr.py           # center crop (184 x 1000 x 1000)
    python scripts/download_idr.py --full    # full volume (184 x 775 x 1121)
"""

import argparse
import json
import requests
import tifffile
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Direct FTP download URL for the TIFF file
DOWNLOAD_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/IDR/"
    "idr0086-miron-micrographs/20200610-ftp/experimentD/"
    "Miron_FIB-SEM/Miron_FIB-SEM_processed/"
    "Figure_S3B_FIB-SEM_U2OS_20x20x20nm_xy.tif"
)

# OMERO API URL for programmatic metadata access
OMERO_METADATA_URL = "https://idr.openmicroscopy.org/webclient/imgData/9846137/"

CROP_SIZE = 1000

OUTPUT_DIR = Path("data/raw/idr")
METADATA_DIR = Path("metadata")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

TIFF_PATH = OUTPUT_DIR / "Figure_S3B_FIB-SEM_U2OS_20x20x20nm_xy.tif"


def fetch_omero_metadata():
    """Fetch metadata from the OMERO JSON API."""
    r = requests.get(OMERO_METADATA_URL)
    r.raise_for_status()
    return r.json()


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


def extract_metadata(arr, omero_meta):
    """Combine OMERO API metadata with dtype extracted from the loaded array."""
    pixel_size = omero_meta["pixel_size"]

    metadata = {
        "dataset": "idr0086-miron-micrographs",
        "image_id": 9846137,
        "source_omero": "https://idr.openmicroscopy.org/webclient/img_detail/9846137/",
        "source_ftp": DOWNLOAD_URL,
        "format": "TIFF",
        "experiment_type": "FIB-SEM",
        "specimen": "U2OS cells, chromatin",
        "project": omero_meta["meta"]["projectName"],
        "full_resolution_shape_zyx": list(arr.shape),
        "dtype": str(arr.dtype),
        "axes": ["z", "y", "x"],
        "units": ["micrometer", "micrometer", "micrometer"],
        # pixel_size from OMERO is in micrometers
        "resolution_zyx_um": [pixel_size["z"], pixel_size["y"], pixel_size["x"]],
        "resolution_zyx_nm": [
            pixel_size["z"] * 1000,
            pixel_size["y"] * 1000,
            pixel_size["x"] * 1000,
        ],
    }

    metadata_path = METADATA_DIR / "idr_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to {metadata_path}")
    return metadata


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


def load_and_save(full=False):
    """Load the TIFF and save either the full volume or a center crop."""
    print("Loading TIFF file...")
    arr = tifffile.imread(TIFF_PATH)
    print(f"Loaded array shape: {arr.shape}, dtype: {arr.dtype}")

    print("Fetching metadata from OMERO API...")
    omero_meta = fetch_omero_metadata()

    metadata = extract_metadata(arr, omero_meta)
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
    parser = argparse.ArgumentParser(description="Download IDR FIB-SEM U2OS dataset")
    parser.add_argument("--full", action="store_true", help="Save full volume instead of center crop")
    args = parser.parse_args()

    download_tiff()
    data = load_and_save(full=args.full)
    print(f"\nDone. Final array shape: {data.shape}, dtype: {data.dtype}")


if __name__ == "__main__":
    main()