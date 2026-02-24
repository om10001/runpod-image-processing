# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RunPod serverless function for **face detection** and **bib number recognition** in sports photography. It uses:
- **InsightFace (buffalo_l)** for face detection and 512-dimensional embeddings
- **PaddleOCR** for bib number detection

Both models run on GPU for optimal performance. Processes images individually (base64) or in batches (URLs) with three modes: `face`, `bib`, or `both`.

## Architecture

### Core Components

- **[app.py](app.py)**: Single-file serverless handler
  - `handler()`: Main RunPod entry point supporting `face`, `bib`, or `both` modes
  - `process_single_image()`: Downloads and processes one image with face/bib detection
  - `detect_bib_numbers()`: PaddleOCR-based bib number extraction
  - `decode_base64_image()` / `download_image()`: Image loading utilities
  - Uses ThreadPoolExecutor with `MAX_WORKERS=10` for parallel batch processing

### Processing Modes

The API supports three detection modes via `input.mode`:

1. **`"face"`** (default): Face detection only → returns face embeddings
2. **`"bib"`**: Bib number detection only → returns bib numbers and bboxes
3. **`"both"`**: Combined detection → returns both faces and bibs

Input formats:
- **Batch mode** (`input.images`): List of `{id, url}` objects → parallel processing
- **Single mode** (`input.image`): Base64 string → single image processing

### Model Initialization

Both models are loaded at startup with GPU support:

1. **InsightFace** (`buffalo_l`) - Face detection
   - Loaded with `ctx_id=0` for GPU acceleration
   - Requires `onnxruntime-gpu` and CUDA base image

2. **PaddleOCR** - Bib number detection
   - Loaded with `use_gpu=True`
   - Requires `paddlepaddle-gpu` and CUDA

Models persist across invocations for fast warm starts.

**Critical**: The Dockerfile uses `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04` base image. Without CUDA, both models fall back to CPU (60x slower).

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
5. Recommended GPU memory: 12GB+ for batch processing with both models

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

### Response Data Structures

```python
# Single mode - face only (mode="face"):
{
  "faces_count": int,
  "embedding": List[float],  # First face only, 512 dims
  "error": str | None
}

# Single mode - bib only (mode="bib"):
{
  "bibs_count": int,
  "bibs": [
    {
      "number": str,  # e.g., "12345"
      "confidence": float,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    }
  ],
  "error": str | None
}

# Batch mode - both (mode="both"):
{
  "results": [
    {
      "id": str,
      "faces_count": int,
      "faces": [
        {
          "face_index": int,
          "embedding": List[float],
          "confidence": float
        }
      ],
      "bibs_count": int,
      "bibs": [
        {
          "number": str,
          "confidence": float,
          "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        }
      ],
      "error": str | None
    }
  ]
}
```

## API Usage

See [API_USAGE.md](API_USAGE.md) for complete API documentation with examples.

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
- `paddleocr`: Bib number OCR detection
- `onnxruntime-gpu`: **GPU-accelerated** ONNX runtime for InsightFace (critical for performance)
- `paddlepaddle-gpu`: **GPU-accelerated** PaddlePaddle for OCR
- `opencv-python-headless`: Image decoding (no GUI dependencies)
- `runpod`: Serverless framework integration
- `requests`: HTTP downloads for batch mode

## GPU Configuration

### Performance Comparison
| Configuration | Mode | Time for 100 images | Notes |
|--------------|------|---------------------|-------|
| CPU | face | ~60+ minutes | Using `onnxruntime` |
| GPU | face | ~2-3 minutes | Using `onnxruntime-gpu` + CUDA |
| GPU | bib | ~3-5 minutes | Using `paddlepaddle-gpu` + CUDA |
| GPU | both | ~4-6 minutes | Both models running on GPU |

### Requirements for GPU Mode
1. **Base image**: `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`
2. **Python packages**:
   - `onnxruntime-gpu` (not `onnxruntime`) for InsightFace
   - `paddlepaddle-gpu` for PaddleOCR
3. **RunPod worker**: Must select GPU instance (RTX A4000, RTX 3090, etc.)
4. **Code config**:
   - `face_app.prepare(ctx_id=0)` in [app.py:30](app.py#L30)
   - `PaddleOCR(use_gpu=True)` in [app.py:35](app.py#L35)

### Troubleshooting GPU Issues
- **Error "CUDA not available"**: Rebuild Docker image with CUDA base
- **Slow processing**: Verify you're using GPU worker in RunPod dashboard
- **OOM errors**: Reduce `MAX_WORKERS` or use GPU with more memory
