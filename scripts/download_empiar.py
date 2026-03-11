"""
Download script for the EMPIAR-11759 zebrafish retina SBF-SEM dataset.

Usage:
    python scripts/download_empiar.py           # center crop (16 x 1000 x 1000)
    python scripts/download_empiar.py --full    # full volume (16 x 5500 x 5496)
"""

import argparse
import json
import requests
import ncempy.io as nio
import numpy as np
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Base URL for the EMPIAR-11759 data files
BASE_URL = "https://ftp.ebi.ac.uk/empiar/world_availability/11759/data/"

# File naming pattern for the 16 slices
FILE_PATTERN = "F57-8_test1_3VBSED_slice_{:04d}.dm3"
NUM_SLICES = 16

CROP_SIZE = 1000

OUTPUT_DIR = Path("data/raw/empiar")
METADATA_DIR = Path("metadata")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)


def download_slice(slice_idx):
    """Download a single DM3 slice file."""
    filename = FILE_PATTERN.format(slice_idx)
    url = BASE_URL + filename
    output_path = OUTPUT_DIR / filename

    if output_path.exists():
        return output_path

    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path


def download_all_slices(max_workers=4):
    """Download all slices in parallel using multiple threads."""
    print(f"Downloading {NUM_SLICES} slices with {max_workers} parallel threads...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_slice, i): i for i in range(NUM_SLICES)}

        with tqdm(total=NUM_SLICES, desc="Slices downloaded") as progress:
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error downloading slice {idx}: {e}")
                progress.update(1)

    print("All slices downloaded.")


def load_stack():
    """Load all DM3 slices and stack them into a single 3D numpy array."""
    print("Loading slices into 3D array...")
    slices = []

    for i in range(NUM_SLICES):
        path = OUTPUT_DIR / FILE_PATTERN.format(i)
        dm3 = nio.read(str(path))
        slices.append(dm3["data"])

    stack = np.stack(slices, axis=0)
    print(f"Stacked array shape: {stack.shape}, dtype: {stack.dtype}")
    return stack


def extract_metadata(stack):
    """Extract metadata from the first slice and combine with known dataset info."""
    path = OUTPUT_DIR / FILE_PATTERN.format(0)
    dm3 = nio.read(str(path))

    # pixelSize is in µm, convert to nm
    pixel_size_um = float(dm3["pixelSize"][0])
    pixel_size_nm = pixel_size_um * 1000

    metadata = {
        "dataset": "EMPIAR-11759",
        "source": BASE_URL,
        "accession": "EMPIAR-11759",
        "format": "DM3",
        "experiment_type": "SBF-SEM",
        "specimen": "Developing retina in zebrafish 55 hpf larval eye",
        "full_resolution_shape_zyx": list(stack.shape),
        "dtype": str(stack.dtype),
        "axes": ["z", "y", "x"],
        "units": ["nanometer", "nanometer", "nanometer"],
        # z resolution from dataset description, xy from file metadata
        "resolution_zyx_nm": [50.0, pixel_size_nm, pixel_size_nm],
        "pixel_size_raw": list(float(p) for p in dm3["pixelSize"]),
        "pixel_size_raw_unit": dm3["pixelUnit"][0],
        "num_slices": NUM_SLICES,
    }

    metadata_path = METADATA_DIR / "empiar_metadata.json"
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


def save_data(stack, full=False):
    """Save the full stack or a center crop as a numpy file."""
    if full:
        data = stack
        filename = "full_volume.npy"
        print("Saving full volume...")
    else:
        slices = get_crop_slices(stack.shape, CROP_SIZE)
        data = stack[slices]
        size_str = "x".join(str(s.stop - s.start) for s in slices)
        filename = f"crop_center_{size_str}.npy"
        print(f"Saving center crop with slices {slices}...")

    output_path = OUTPUT_DIR / filename
    np.save(output_path, data)
    print(f"Saved to {output_path}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Download EMPIAR-11759 zebrafish retina SBF-SEM dataset")
    parser.add_argument("--full", action="store_true", help="Save full volume instead of center crop")
    args = parser.parse_args()

    download_all_slices()

    stack = load_stack()

    metadata = extract_metadata(stack)
    print(json.dumps(metadata, indent=2))

    data = save_data(stack, full=args.full)
    print(f"\nDone. Final array shape: {data.shape}, dtype: {data.dtype}")


if __name__ == "__main__":
    main()