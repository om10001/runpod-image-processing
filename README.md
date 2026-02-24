# RunPod Face + Bib Detection API

**GPU-accelerated** serverless function for sports photography processing. Detects faces and bib numbers with high accuracy using InsightFace and PaddleOCR.

[![RunPod](https://img.shields.io/badge/RunPod-Serverless-blueviolet)](https://runpod.io)
[![CUDA](https://img.shields.io/badge/CUDA-11.8-green)](https://developer.nvidia.com/cuda-toolkit)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Features

- 🏃 **Face Detection** - 512-dimensional embeddings via InsightFace (buffalo_l)
- 🔢 **Bib Number Recognition** - OCR-based detection via PaddleOCR
- ⚡ **GPU Accelerated** - Both models run on CUDA for optimal speed
- 📦 **Batch Processing** - Process multiple images in parallel (10 workers)
- 🎯 **Flexible Modes** - Choose `face`, `bib`, or `both` detection
- 🌐 **REST API** - Simple JSON API via RunPod

## Performance

| Mode | GPU | Time (100 images) |
|------|-----|-------------------|
| Face | RTX A5000 | ~2-3 min |
| Bib  | RTX A5000 | ~3-5 min |
| Both | RTX A5000 | ~4-6 min |

*CPU mode is 60x slower (~60+ minutes)*

## Quick Start

### Deploy to RunPod

#### Option 1: Template Builder (Recommended)

1. Fork or clone this repo to your GitHub
2. Go to [RunPod Console](https://runpod.io/console/serverless) → Templates
3. Click **"New Template"** → **"Build from Repository"**
4. Configure:
   - **Repo URL**: `https://github.com/YOUR-USERNAME/runpod-image-processing`
   - **Branch**: `main`
   - **Dockerfile Path**: `/Dockerfile`
   - **Container Disk**: 10 GB
   - Enable **"Build with GPU"**
5. Create endpoint using this template
6. **Important**: Select GPU worker (RTX A4000/A5000 recommended)

#### Option 2: Docker Hub

```bash
# Build image
docker build -t your-username/runpod-face-processing .

# Push to Docker Hub
docker push your-username/runpod-face-processing

# In RunPod dashboard:
# 1. Create serverless endpoint
# 2. Set container image to your-username/runpod-face-processing
# 3. Select GPU worker (12GB+ VRAM recommended)
```

## API Usage

### Face Detection Only (Default)

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "img1", "url": "https://example.com/photo1.jpg"}
      ],
      "mode": "face"
    }
  }'
```

**Response:**
```json
{
  "results": [
    {
      "id": "img1",
      "faces_count": 2,
      "faces": [
        {
          "face_index": 0,
          "embedding": [0.123, -0.456, ...],
          "confidence": 0.99
        }
      ],
      "error": null
    }
  ]
}
```

### Bib Number Detection

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "runner1", "url": "https://example.com/runner.jpg"}
      ],
      "mode": "bib"
    }
  }'
```

**Response:**
```json
{
  "results": [
    {
      "id": "runner1",
      "bibs_count": 1,
      "bibs": [
        {
          "number": "12345",
          "confidence": 0.95,
          "bbox": [[100, 200], [300, 200], [300, 250], [100, 250]]
        }
      ],
      "error": null
    }
  ]
}
```

### Both Face + Bib Detection

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "athlete1", "url": "https://example.com/athlete.jpg"}
      ],
      "mode": "both"
    }
  }'
```

**Response includes both `faces` and `bibs` arrays.**

See [API_USAGE.md](API_USAGE.md) for complete documentation with Python/JavaScript examples.

## Python Example

```python
import requests

response = requests.post(
    "https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "input": {
            "images": [
                {"id": "img1", "url": "https://example.com/runner.jpg"}
            ],
            "mode": "both"
        }
    }
)

result = response.json()["results"][0]
print(f"Faces: {result['faces_count']}, Bibs: {result['bibs_count']}")
```

## Architecture

### Models

1. **InsightFace (buffalo_l)**
   - 512-dimensional face embeddings
   - GPU-accelerated via `onnxruntime-gpu`
   - Loaded at startup for fast warm starts

2. **PaddleOCR**
   - Bib number text detection and recognition
   - GPU-accelerated via `paddlepaddle-gpu`
   - Filters results to numeric bibs (1-5 digits)

### Processing Pipeline

```
Image URL/Base64
    ↓
Download/Decode
    ↓
┌─────────────┬─────────────┐
│ Face Model  │  OCR Model  │  (GPU parallel)
└─────────────┴─────────────┘
    ↓              ↓
Embeddings     Bib Numbers
    ↓              ↓
    JSON Response
```

### Batch Processing

- **Parallelism**: 10 concurrent workers (configurable via `MAX_WORKERS`)
- **Error Handling**: Per-image errors don't fail entire batch
- **Timeout**: 15s per image download

## Requirements

### System
- **CUDA 11.8+**
- **Docker** with GPU support
- **12GB+ GPU VRAM** (for batch processing with both models)

### Python Dependencies
- `insightface` - Face detection
- `paddleocr` - OCR for bib numbers
- `onnxruntime-gpu` - GPU acceleration for InsightFace
- `paddlepaddle-gpu` - GPU acceleration for OCR
- `opencv-python-headless` - Image processing
- `runpod` - Serverless framework

See [requirements.txt](requirements.txt) for full list.

## Local Development

### With Docker (Recommended)

```bash
# Build image
docker build -t runpod-face-processing .

# Run with GPU
docker run --gpus all -p 8000:8000 runpod-face-processing
```

### Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set up RunPod test environment
# (See RunPod docs for local testing)
python app.py
```

## GPU Diagnostics

The function logs GPU availability on startup:

```
=== GPU Diagnostics ===
ONNX Runtime providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
CUDA available: True
Loading InsightFace model...
✓ InsightFace initialized with GPU (ctx_id=0)
Loading PaddleOCR model...
✓ PaddleOCR initialized with GPU
=======================
```

If you see `CUDA available: False`, the function will fall back to CPU (very slow).

## Troubleshooting

### GPU Not Being Used

**Symptoms**: 0% GPU utilization in RunPod telemetry, slow processing

**Solutions**:
1. Verify Docker image uses `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04` base
2. Check `onnxruntime-gpu` and `paddlepaddle-gpu` are in requirements
3. Ensure RunPod worker has GPU assigned (not CPU-only)
4. Check startup logs for "CUDA available: True"

See [GPU_FIX.md](GPU_FIX.md) for detailed troubleshooting.

### Slow First Request

**Expected**: First request takes 10-15s for model loading (GPU initialization)

**Solution**: Use RunPod's worker warm-up feature to keep instances ready

### OOM Errors

**Cause**: Insufficient GPU memory for batch size

**Solutions**:
1. Reduce `MAX_WORKERS` in [app.py](app.py#L15)
2. Use GPU with more VRAM (24GB recommended for large batches)
3. Process smaller batches

## Documentation

- [API_USAGE.md](API_USAGE.md) - Complete API reference with examples
- [CLAUDE.md](CLAUDE.md) - Development guide for AI assistants
- [GPU_FIX.md](GPU_FIX.md) - GPU troubleshooting guide
- [DEPLOY_ALTERNATIVE.md](DEPLOY_ALTERNATIVE.md) - Alternative deployment methods

## Use Cases

- 🏃 **Marathon/Race Photography** - Match runner faces to bib numbers
- 📸 **Sports Event Management** - Auto-tag athlete photos
- 👥 **Face Recognition** - Compare face embeddings for similarity
- 🔍 **Athlete Search** - Find all photos of a specific bib number

## License

MIT License - see [LICENSE](LICENSE) for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/YOUR-USERNAME/runpod-image-processing/issues)
- **RunPod Docs**: https://docs.runpod.io
- **Discord**: [RunPod Community](https://discord.gg/runpod)

---

Built with ❤️ for sports photographers
