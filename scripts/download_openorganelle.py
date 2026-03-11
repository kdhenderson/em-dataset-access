"""
Download script for the OpenOrganelle jrc_mus-nacc-2 dataset.

Usage:
    python scripts/download_openorganelle.py           # download center crop
    python scripts/download_openorganelle.py --full    # download full volume
"""

import zarr
import s3fs
import dask.array as da
import numpy as np
import json
from pathlib import Path

# S3 location of the dataset
S3_PATH = "s3://janelia-cosem-datasets/jrc_mus-nacc-2/jrc_mus-nacc-2.zarr"

# Path to the full-resolution EM array within the zarr store
ARRAY_PATH = "recon-2/em/fibsem-int16/s0"

# Path to the multiscale metadata attributes
ATTRS_PATH = "recon-2/em/fibsem-int16"

# Crop size in voxels for each dimension
CROP_SIZE = 1000

# Local directories for outputs
OUTPUT_DIR = Path("data/raw/openorganelle")
METADATA_DIR = Path("metadata")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)


def open_store(s3_path):
    """Open the zarr store on S3 anonymously."""
    fs = s3fs.S3FileSystem(anon=True)
    store = zarr.open(zarr.storage.FSStore(s3_path, fs=fs), mode="r")
    return store


def extract_metadata(store):
    """Extract and save metadata from the zarr attributes."""
    attrs = dict(store[ATTRS_PATH].attrs)
    arr = store[ARRAY_PATH]

    # Pull resolution for s0 from the multiscales metadata
    s0_transforms = attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"]
    resolution = next(t["scale"] for t in s0_transforms if t["type"] == "scale")
    axes = [ax["name"] for ax in attrs["multiscales"][0]["axes"]]
    units = [ax["unit"] for ax in attrs["multiscales"][0]["axes"]]

    metadata = {
        "dataset": "jrc_mus-nacc-2",
        "source": S3_PATH,
        "format": "OME-NGFF Zarr",
        "multiscale_version": attrs["multiscales"][0]["version"],
        "num_resolution_levels": len(attrs["multiscales"][0]["datasets"]),
        "full_resolution_shape_zyx": list(arr.shape),
        "dtype": str(arr.dtype),
        "chunk_size_zyx": list(arr.chunks),
        "axes": axes,
        "units": units,
        "resolution_zyx_nm": resolution,
    }

    # Save metadata to JSON
    metadata_path = METADATA_DIR / "openorganelle_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to {metadata_path}")
    return metadata


def get_crop_slices(shape, crop_size):
    """Calculate slices to crop the center of the volume."""
    slices = []
    for dim in shape:
        if dim <= crop_size:
            # Dimension is smaller than crop size, take the full dimension
            slices.append(slice(0, dim))
        else:
            # Take crop_size voxels from the center
            center = dim // 2
            start = center - crop_size // 2
            stop = start + crop_size
            slices.append(slice(start, stop))
    return tuple(slices)


def download_data(store, full=False):
    """Download the full volume or a center crop of CROP_SIZE in each dimension."""
    arr = store[ARRAY_PATH]
    shape = arr.shape

    if full:
        slices = tuple(slice(0, dim) for dim in shape)
        filename = "full_volume.npy"
        print("Downloading full volume...")
    else:
        slices = get_crop_slices(shape, CROP_SIZE)
        filename = f"crop_center_{'x'.join(str(s.stop - s.start) for s in slices)}.npy"
        print("Downloading center crop...")

    print(f"Full volume shape: {shape}")
    print(f"Slices: {slices}")

    dask_arr = da.from_zarr(arr)
    data = dask_arr[slices]

    print(f"Downloading array of shape {data.shape}, dtype {arr.dtype}...")
    data_np = data.compute()

    output_path = OUTPUT_DIR / filename
    np.save(output_path, data_np)
    print(f"Saved to {output_path}")

    return data_np


def main():
    parser = argparse.ArgumentParser(description="Download OpenOrganelle jrc_mus-nacc-2 dataset")
    parser.add_argument("--full", action="store_true", help="Download full volume instead of center crop")
    args = parser.parse_args()

    print("Connecting to OpenOrganelle dataset on S3...")
    store = open_store(S3_PATH)

    print("Extracting metadata...")
    metadata = extract_metadata(store)
    print(json.dumps(metadata, indent=2))

    print("\nDownloading data...")
    data = download_data(store, full=args.full)
    print(f"\nDone. Final array shape: {data.shape}, dtype: {data.dtype}")


if __name__ == "__main__":
    main()