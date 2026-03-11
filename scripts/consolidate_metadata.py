"""
Consolidates metadata from all five EM datasets into a single comparison table.
Outputs both a JSON summary and a CSV table.

Usage:
    python scripts/consolidate_metadata.py
"""

import json
import csv
from pathlib import Path

METADATA_DIR = Path("metadata")
OUTPUT_DIR = Path("metadata")


def load_all_metadata():
    """Load all five individual metadata JSON files."""
    files = {
        "OpenOrganelle": "openorganelle_metadata.json",
        "EPFL": "epfl_metadata.json",
        "EMPIAR": "empiar_metadata.json",
        "IDR": "idr_metadata.json",
        "Hemibrain": "hemibrain_metadata.json",
    }
    return {name: json.loads((METADATA_DIR / fname).read_text())
            for name, fname in files.items()}


def get_resolution_zyx_nm(meta, name):
    """
    Extract resolution in nm as a zyx list, handling axis order differences.
    Hemibrain is stored xyz so we reverse it to match zyx convention.
    EMPIAR xy resolution is rounded from raw µm conversion.
    """
    if name == "Hemibrain":
        # stored as xyz, reverse to zyx
        res = meta["resolution_xyz_nm"]
        return [res[2], res[1], res[0]]
    elif name == "EMPIAR":
        # round from raw µm conversion
        res = meta["resolution_zyx_nm"]
        return [round(r, 2) for r in res]
    else:
        return meta["resolution_zyx_nm"]


def get_shape_zyx(meta, name):
    """
    Extract volume shape as zyx, handling axis order differences.
    Hemibrain is stored xyz so we reverse to zyx.
    """
    if name == "Hemibrain":
        shape = meta["full_resolution_shape_xyz"]
        return [shape[2], shape[1], shape[0]]
    else:
        return meta["full_resolution_shape_zyx"]


def get_chunk_size(meta, name):
    """Extract chunk size if available, otherwise return None."""
    if name == "OpenOrganelle":
        return meta.get("chunk_size_zyx")
    elif name == "Hemibrain":
        c = meta.get("chunk_size_xyz")
        if c:
            return [c[2], c[1], c[0]]
    return None


def consolidate(all_meta):
    """Build a list of consolidated records, one per dataset."""
    records = []

    for name, meta in all_meta.items():
        resolution = get_resolution_zyx_nm(meta, name)
        shape = get_shape_zyx(meta, name)
        chunk_size = get_chunk_size(meta, name)

        record = {
            "dataset": name,
            "full_name": meta.get("dataset", name),
            "source_format": meta.get("format"),
            "experiment_type": meta.get("experiment_type", None),
            "specimen": meta.get("specimen", None),
            "shape_z": shape[0],
            "shape_y": shape[1],
            "shape_x": shape[2],
            "dtype": meta.get("dtype"),
            "resolution_z_nm": resolution[0],
            "resolution_y_nm": resolution[1],
            "resolution_x_nm": resolution[2],
            "isotropic": resolution[0] == resolution[1] == resolution[2],
            "chunk_size": str(chunk_size) if chunk_size else None,
            "num_resolution_levels": meta.get("num_resolution_levels")
                or meta.get("num_mip_levels"),
            "source_url": meta.get("source")
                or meta.get("source_ftp")
                or meta.get("source_omero"),
            "notes": _get_notes(name, meta),
        }
        records.append(record)

    return records


def _get_notes(name, meta):
    """Record dataset-specific notes about metadata quirks or corrections."""
    notes = []
    if name == "IDR":
        notes.append("Pixel size from OMERO API in µm, converted to nm.")
    if name == "EPFL":
        notes.append("No resolution metadata in TIFF file; 5nm from dataset webpage.")
        notes.append("TIFF axis order is z=1065, y=1536, x=2048; website lists as 1065x2048x1536.")
    if name == "EMPIAR":
        notes.append("Z resolution (50nm) from dataset description, not file metadata.")
        notes.append("XY resolution rounded from raw µm value (0.007998 µm).")
    if name == "Hemibrain":
        notes.append("Stored in xyz axis order; converted to zyx for consistency.")
        notes.append("JPEG encoding is lossy; pixel values are approximate.")
        notes.append("Crop is random; origin saved in data/raw/hemibrain/crop_origin.json.")
    return " ".join(notes) if notes else None


def save_csv(records):
    """Save the consolidated records as a CSV file."""
    output_path = OUTPUT_DIR / "consolidated_metadata.csv"
    fieldnames = list(records[0].keys())

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"CSV saved to {output_path}")


def save_json(records):
    """Save the consolidated records as a JSON file."""
    output_path = OUTPUT_DIR / "consolidated_metadata.json"
    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"JSON saved to {output_path}")


def print_table(records):
    """Print a readable summary table to the terminal."""
    fields = [
        "dataset", "source_format", "dtype",
        "shape_z", "shape_y", "shape_x",
        "resolution_z_nm", "resolution_y_nm", "resolution_x_nm",
        "isotropic", "num_resolution_levels",
    ]

    # Print header
    print("\nConsolidated Metadata Summary")
    print("=" * 80)
    for record in records:
        print(f"\n{record['dataset']} ({record['full_name']})")
        for field in fields:
            value = record.get(field)
            if value is not None:
                print(f"  {field}: {value}")
        if record.get("notes"):
            print(f"  notes: {record['notes']}")


def main():
    print("Loading metadata files...")
    all_meta = load_all_metadata()

    print("Consolidating...")
    records = consolidate(all_meta)

    print_table(records)
    save_csv(records)
    save_json(records)

    print("\nDone.")


if __name__ == "__main__":
    main()