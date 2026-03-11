# Block-wise Data Access for AI/ML Pipelines: Design Outline

## Goal
These datasets are in different formats, sizes, and storage locations. The goal is to
standardize how data is accessed so that the ML pipeline can just request a block of
data from any dataset and receive it in the same format, a numpy array, without
needing to know anything about the dataset, file format, or storage.

## 1. Common Data Adapter (similar to a dataloader)
- The ML pipeline requests a 128x128x128 block from a named dataset and always gets
  back a numpy array without ever needing to interact with the files directly.

## 2. Format-Specific Adapters
- There is one adapter for each file format: Zarr, TIFF, DM3, Neuroglancer precomputed, etc.
- Each adapter knows how to read its format and create a block, so that it doesn't matter 
  if the data comes from a single file, multiple files, or multiple chunks.
- There is one adapter per file format, not per dataset, so the same adapter can be
  reused for any dataset stored in that format.

## 3. A Lookup Table and Shared Metadata File
- A lookup table matches each dataset name to its adapter.
- Each adapter reads the information it needs from a consolidated metadata JSON file:
  volume shape, voxel size, axis order, whether the data is chunked
- Nothing is hardcoded into the adapters, so adding a new dataset only requires
  updating the metadata file and lookup table.

## 4. Handling Axis Order and Assembling Blocks
- Datasets store dimensions in different orders (e.g., xyz vs zyx).
- The adapter reads the axis order from the metadata and reorders the dimensions to match 
  what the pipeline expects, so the pipeline receives data in the correct orientation.
- For chunked datasets, the adapter finds the chunks that overlap with the requested 
  block and assembles them.
- For flat file datasets like TIFF, the adapter reads and slices the portion
  of the file that is needed.

## 5. Resolution Standardization
- Voxel sizes vary across datasets (e.g., 2.96nm in OpenOrganelle vs 50nm z-spacing
  in EMPIAR).
- The adapter resamples the block to a standard resolution before passing it to the 
  pipeline, so the images a model sees are from the same physical scale.

## 6. Edge Handling
- The adapter checks the volume dimensions from the metadata to detect when a
  requested block is at the edge of the volume.
- Rather than returning an error or a smaller block, the adapter adds padding to 
  fill out the full 128x128x128 block size.

## 7. Caching
- If the training loop accesses the same blocks repeatedly, re-reading them from
  disk or remote storage each time is inefficient.
- A cache stores recently accessed blocks in memory to reduce the number of times 
  they need to be retrieved and processed.