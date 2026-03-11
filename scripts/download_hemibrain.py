"""
Download script for the Janelia FlyEM Hemibrain dataset.
Raw EM data at 8x8x8nm resolution, stored as neuroglancer precomputed format on GCS.

Usage:
    python scripts/download_hemibrain.py    # random 1000x1000x1000 crop (required due to dataset size)
"""

import json
import random
import warnings
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")
from cloudvolume import CloudVolume

# GCS path to the raw EM data
GCS_PATH = "gs://neuroglancer-janelia-flyem-hemibrain/emdata/raw/jpeg"

CROP_SIZE = 1000

OUTPUT_DIR = Path("data/raw/hemibrain")
METADATA_DIR = Path("metadata")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)


def open_volume():
    """Open the Hemibrain CloudVolume dataset anonymously via HTTPS."""
    vol = CloudVolume(
        GCS_PATH,
        mip=0,
        use_https=True,
        fill_missing=True,
    )
    return vol


def extract_metadata(vol):
    """Extract and save metadata from the CloudVolume object."""
    metadata = {
        "dataset": "Janelia FlyEM Hemibrain",
        "source": GCS_PATH,
        "format": "Neuroglancer precomputed (sharded JPEG)",
        "full_resolution_shape_xyz": list(int(x) for x in vol.shape[:3]),
        "dtype": str(vol.dtype),
        "axes": ["x", "y", "z"],
        "units": ["nanometer", "nanometer", "nanometer"],
        "resolution_xyz_nm": list(int(x) for x in vol.resolution),
        "chunk_size_xyz": list(int(x) for x in vol.chunk_size),
        "num_mip_levels": len(vol.available_mips),
        "encoding": "jpeg",
    }

    metadata_path = METADATA_DIR / "hemibrain_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to {metadata_path}")
    return metadata


def get_random_crop_origin(shape, crop_size):
    """Choose a random starting point that leaves room for a full crop in each dimension."""
    origins = []
    for dim in shape[:3]:
        max_origin = int(dim) - crop_size
        origins.append(random.randint(0, max_origin))
    return origins


def download_crop(vol):
    """Download a random 1000x1000x1000 crop from the volume."""
    origins = get_random_crop_origin(vol.shape, CROP_SIZE)
    x0, y0, z0 = origins
    x1, y1, z1 = x0 + CROP_SIZE, y0 + CROP_SIZE, z0 + CROP_SIZE

    print(f"Full volume shape (xyz): {vol.shape[:3]}")
    print(f"Downloading crop at origin x={x0}, y={y0}, z={z0}...")
    print(f"Crop region: x[{x0}:{x1}], y[{y0}:{y1}], z[{z0}:{z1}]")

    # CloudVolume returns shape (x, y, z, channel) -- squeeze out channel dim
    crop = vol[x0:x1, y0:y1, z0:z1]
    crop = np.squeeze(crop, axis=-1)

    print(f"Downloaded crop shape: {crop.shape}, dtype: {crop.dtype}")

    # Save crop and its origin for reproducibility
    output_path = OUTPUT_DIR / f"crop_random_{CROP_SIZE}x{CROP_SIZE}x{CROP_SIZE}.npy"
    np.save(output_path, crop)
    print(f"Crop saved to {output_path}")

    # Save the crop origin so the exact region can be reproduced
    origin_path = OUTPUT_DIR / "crop_origin.json"
    with open(origin_path, "w") as f:
        json.dump({"x0": x0, "y0": y0, "z0": z0, "crop_size": CROP_SIZE}, f, indent=2)
    print(f"Crop origin saved to {origin_path}")

    return crop


def main():
    print("Opening Hemibrain dataset on GCS...")
    vol = open_volume()

    print("Extracting metadata...")
    metadata = extract_metadata(vol)
    print(json.dumps(metadata, indent=2))

    print("\nDownloading random crop...")
    crop = download_crop(vol)
    print(f"\nDone. Final array shape: {crop.shape}, dtype: {crop.dtype}")


if __name__ == "__main__":
    main()