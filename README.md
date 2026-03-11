# EM Dataset Access

A reproducible pipeline for downloading, organizing, and accessing five public 3D 
electron microscopy datasets for use in AI/ML pipelines.

## Overview

This project downloads a representative set of public 3D EM datasets, extracts and 
consolidates their metadata, and outlines a design for block-wise data access to 
support ML training workflows.

## Use of AI Assistance

I used Claude (Anthropic) throughout this project. For the download scripts, I worked 
iteratively with Claude to handle unfamiliar formats and libraries (Zarr, DM3, 
Neuroglancer precomputed, cloud storage access). I understood what the code needed to 
do and made decisions about structure and approach, but I did not write it from scratch 
on my own. For the metadata work, I identified the relevant fields and handled inconsistencies 
across datasets, and Claude helped me implement the consolidation. For the 
block-wise access design, Claude helped me iteratively think through the components. I 
wrote the outline myself, and it reflects my own knowledge and understanding. Overall, 
I used AI as a collaborator to work through unfamiliar territory and move faster than 
I could have alone.

## Datasets

| Dataset | Source | Format | Resolution (nm) |
|---|---|---|---|
| OpenOrganelle | Janelia / AWS S3 | OME-NGFF Zarr | 2.96 x 4 x 4 |
| EPFL Hippocampus | EPFL CVLab / HTTP | Multipage TIFF | 5 x 5 x 5 |
| EMPIAR-11759 | EBI / FTP | DM3 | 50 x 8 x 8 |
| IDR idr0086 | IDR / FTP | TIFF | 20 x 20 x 20 |
| Hemibrain | Janelia / GCS | Neuroglancer precomputed | 8 x 8 x 8 |

## Repository Structure
```
data/raw/          # downloaded data (not committed)
metadata/          # extracted and consolidated metadata
scripts/           # download and consolidation scripts
docs/              # project documentation
```

## Usage

Each dataset has its own download script in `scripts/`. Scripts default to a center 
crop and accept a `--full` flag for the full volume where applicable.
```bash
python scripts/download_openorganelle.py
python scripts/download_epfl.py
python scripts/download_empiar.py
python scripts/download_idr.py
python scripts/download_hemibrain.py
python scripts/consolidate_metadata.py
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Documentation

- `metadata/consolidated_metadata.csv` and `.json` -- unified metadata across all 
  five datasets
- `docs/metadata_summary.md` -- notes on how metadata was extracted for each dataset,
  including format quirks and corrections
- `docs/blockwise_access_design.md` -- design outline for a block-wise data access 
  system to support ML pipelines