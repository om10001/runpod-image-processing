# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RunPod serverless function for face detection and embedding generation using InsightFace (buffalo_l model). It processes images either individually (base64) or in batches (URLs) and returns 512-dimensional face embeddings suitable for facial recognition and similarity matching.

## Architecture

### Core Components

- **[app.py](app.py)**: Single-file serverless handler
  - `handler()`: Main RunPod entry point that routes between single/batch modes
  - `process_single_image()`: Downloads and processes one image (used by batch mode)
  - `decode_base64_image()` / `download_image()`: Image loading utilities
  - Uses ThreadPoolExecutor with `MAX_WORKERS=10` for parallel batch processing

### Processing Modes

1. **Single mode** (`input.image`): Base64 image → returns first face embedding only
2. **Batch mode** (`input.images`): List of `{id, url}` objects → returns all faces per image with parallel download/processing

### Model Initialization

The InsightFace model (`buffalo_l`) is loaded at startup with GPU support (`ctx_id=0`). This is intentional for serverless warm starts - the model persists across invocations.

**Critical**: The Dockerfile uses `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04` base image and `onnxruntime-gpu` to enable GPU acceleration. Without these, the model will fail or fall back to CPU (extremely slow).

## Development Commands

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires RunPod environment simulation)
python app.py
```

### Docker Build
```bash
# Build image
docker build -t runpod-face-processing .

# Test locally
docker run --gpus all -p 8000:8000 runpod-face-processing
```

### Deploy to RunPod
1. Build and push image to Docker Hub:
   ```bash
   docker build -t your-dockerhub-username/runpod-face-processing .
   docker push your-dockerhub-username/runpod-face-processing
   ```
2. Create serverless endpoint in RunPod dashboard
3. **Required**: Select a GPU worker (RTX A4000, RTX 3090, etc.). CPU workers will not work.
4. Set container image to your Docker Hub image
5. Recommended GPU memory: 10GB+ for batch processing

## Key Implementation Details

### Batch Processing
- Uses `ThreadPoolExecutor.map()` for parallel execution
- Each image in batch is independent - failures don't block others
- Each result includes `{id, faces_count, faces[], error}`
- Downloads have 15s timeout per image

### Error Handling
- Single mode: Returns `{"error": "...", "faces_count": 0, "embedding": null}`
- Batch mode: Each item gets individual error field, never fails entire batch
- Invalid images return gracefully with error message

### Face Data Structure
```python
# Single mode returns:
{
  "faces_count": int,
  "embedding": List[float],  # First face only, 512 dims
  "error": str | None
}

# Batch mode returns per image:
{
  "id": str,  # From input
  "faces_count": int,
  "faces": [
    {
      "face_index": int,
      "embedding": List[float],  # 512 dims
      "confidence": float  # det_score
    }
  ],
  "error": str | None
}
```

## API Usage

See [docs.md](docs.md) for complete API documentation.

**Base URL**: `https://api.runpod.ai/v2/{ENDPOINT_ID}`

**Authentication**: `Authorization: Bearer {RUNPOD_API_KEY}`

- `/runsync` - Synchronous execution (recommended for most cases)
- `/run` - Async execution (returns job ID, poll for results)
- `/health` - Worker and queue status

## Important Constraints

- Base64 input must be pure base64 (no `data:image/...;base64,` prefix)
- Image URLs must be publicly accessible (no auth required)
- Batch processing uses 10 parallel workers - adjust `MAX_WORKERS` for different memory/CPU profiles
- Model is GPU-dependent (`ctx_id=0`) - CPU fallback would require code change
- Embeddings are 512 dimensions - use cosine similarity for comparison
- No image preprocessing/resizing - InsightFace handles internally

## Dependencies

- `insightface`: Face detection and embedding generation
- `onnxruntime-gpu`: **GPU-accelerated** ONNX runtime for model inference (critical for performance)
- `opencv-python-headless`: Image decoding (no GUI dependencies)
- `runpod`: Serverless framework integration
- `requests`: HTTP downloads for batch mode

## GPU Configuration

### Performance Comparison
| Configuration | Time for 100 images | Notes |
|--------------|---------------------|-------|
| CPU (`ctx_id=-1`) | ~60+ minutes | Using `onnxruntime` |
| GPU (`ctx_id=0`) | ~2-3 minutes | Using `onnxruntime-gpu` + CUDA base image |

### Requirements for GPU Mode
1. **Base image**: `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`
2. **Python package**: `onnxruntime-gpu` (not `onnxruntime`)
3. **RunPod worker**: Must select GPU instance (RTX A4000, RTX 3090, etc.)
4. **Code config**: `face_app.prepare(ctx_id=0)` in [app.py:16](app.py#L16)

### Troubleshooting GPU Issues
- **Error "CUDA not available"**: Rebuild Docker image with CUDA base
- **Slow processing**: Verify you're using GPU worker in RunPod dashboard
- **OOM errors**: Reduce `MAX_WORKERS` or use GPU with more memory
