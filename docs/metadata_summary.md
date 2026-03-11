# Metadata Extraction Summary

## Overview

Metadata was extracted from five publicly available 3D electron microscopy datasets.
Each dataset uses a different storage format and access method, so metadata extraction
varied by dataset. All metadata is consolidated in `metadata/consolidated_metadata.csv`
and `metadata/consolidated_metadata.json`.

## Per-Dataset Extraction Methods

### OpenOrganelle (jrc_mus-nacc-2)
- **Access:** AWS S3 via `s3fs` and `zarr` (Python)
- **Format:** OME-NGFF Zarr
- **Method:** Browsed the S3 bucket programmatically to find the zarr store, then read
  metadata from a small JSON file (`.zattrs`) that is stored alongside the data in the
  Zarr format. This file contained resolution, axis names, units, chunk size, and the
  number of resolution levels, all following the OME-NGFF v0.4 specification.
- **Notes:** Resolution is anisotropic (2.96 x 4.0 x 4.0 nm). All metadata is stored
  inside the file format itself and does not require consulting external sources.

### EPFL CVLab Hippocampus
- **Access:** Direct HTTP download from EPFL server
- **Format:** Multipage TIFF
- **Method:** Downloaded the TIFF file and inspected its internal tags using `tifffile`.
  The file contained no embedded resolution information. Shape and dtype were read
  directly from the file. Resolution (5 x 5 x 5 nm) was taken from the dataset webpage
  as it is not stored anywhere in the file.
- **Notes:** The TIFF axis order as read by tifffile is (z=1065, y=1536, x=2048), which
  differs from the dataset webpage description of 1065 x 2048 x 1536 (y and x are
  swapped). Resolution relies entirely on the webpage description.

### EMPIAR-11759
- **Access:** EBI public FTP server, accessed via HTTPS
- **Format:** DM3 (Digital Micrograph 3), one file per z-slice
- **Method:** Downloaded 16 DM3 slices in parallel using `concurrent.futures`. Read
  pixel size and units from each file using `ncempy`. XY resolution (8nm) was extracted
  from file metadata (stored in µm in the file, converted to nm). Z resolution (50nm)
  was taken from the dataset description text on the EMPIAR webpage, as SBF-SEM z
  spacing is determined by the physical section thickness and is not stored in the DM3
  files. Dataset-level metadata (accession, experiment type, specimen) was read from
  the EMPIAR XML metadata file available at the same FTP location.
- **Notes:** Z resolution is a known limitation of the DM3 format for SBF-SEM data
  and must be sourced externally.

### IDR (idr0086-miron-micrographs)
- **Access:** EBI public FTP server for image data; OMERO JSON API for metadata
- **Format:** TIFF
- **Method:** The IDR is built on OMERO, an open-source image management platform with
  a REST API. Metadata (shape, pixel size, dtype, project name) was fetched
  programmatically from the OMERO JSON API at
  `https://idr.openmicroscopy.org/webclient/imgData/9846137/` using Python `requests`,
  with no account required. The project name from the API was used to navigate the IDR
  FTP directory structure and locate the original TIFF file for download. Pixel size is
  stored in µm in OMERO and was converted to nm.
- **Notes:** The standard OMERO Python library (`omero-py`) requires a C++ networking
  dependency (`zeroc-ice`) that fails to compile on recent Macs. The JSON REST API
  provides the same metadata without this dependency and was used instead.

### Janelia FlyEM Hemibrain
- **Access:** Google Cloud Storage (GCS) via `cloudvolume` and `gcsfs`
- **Format:** Neuroglancer precomputed (sharded JPEG)
- **Method:** Opened the dataset anonymously using `CloudVolume` with `use_https=True`.
  Shape, dtype, resolution, chunk size, and number of resolution pyramid levels were
  read directly from the CloudVolume object, which internally parses a JSON `info` file
  stored alongside the data. The raw EM data lives at
  `gs://neuroglancer-janelia-flyem-hemibrain/emdata/raw/jpeg`, separate from the
  versioned segmentation data under `v1.0/`.
- **Notes:** CloudVolume reports axes in xyz order; converted to zyx for consistency
  with other datasets. JPEG encoding means pixel values are lossy approximations of
  the original. A random 1000 x 1000 x 1000 crop was downloaded; the exact origin
  coordinates are saved in `data/raw/hemibrain/crop_origin.json` for reproducibility.

## Consolidated Metadata Fields

| Field | Description | Available For |
|---|---|---|
| source_format | File format used for storage | All |
| dtype | Pixel data type | All |
| shape_z/y/x | Volume dimensions in voxels | All |
| resolution_z/y/x_nm | Voxel size in nanometers | All |
| isotropic | Whether voxel size is equal in all three dimensions | All |
| experiment_type | Imaging modality (FIB-SEM, SBF-SEM, etc.) | EMPIAR, IDR |
| specimen | Biological sample description | EPFL, EMPIAR, IDR |
| chunk_size | Storage chunk size in voxels | OpenOrganelle, Hemibrain |
| num_resolution_levels | Number of downsampled pyramid levels | OpenOrganelle, Hemibrain |
| encoding | Compression encoding | Hemibrain |
| notes | Metadata quirks and corrections | Where applicable |