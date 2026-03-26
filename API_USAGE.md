# RunPod Face + Bib Detection API - Usage Guide

## Overview

This RunPod serverless function provides **GPU-accelerated** face detection and bib number recognition for sports photography. It supports three modes:

- **`face`** - Face detection only (default)
- **`bib`** - Bib number detection only
- **`both`** - Both face and bib detection

## Base URL

```
https://api.runpod.ai/v2/{ENDPOINT_ID}
```

Replace `{ENDPOINT_ID}` with your RunPod endpoint ID.

## Authentication

All requests require your RunPod API key:

```bash
Authorization: Bearer YOUR_RUNPOD_API_KEY
```

## API Endpoints

### 1. Synchronous Execution (Recommended)

**Endpoint:** `POST /runsync`

Returns results immediately (max 90s execution time).

### 2. Async Execution

**Endpoint:** `POST /run`

Returns job ID immediately. Poll `/status/{job_id}` for results.

### 3. Health Check

**Endpoint:** `GET /health`

Check worker and queue status.

---

## Request Formats

### Mode 1: Face Detection Only (Default)

#### Batch Processing (URLs)

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "photo1", "url": "https://example.com/image1.jpg"},
        {"id": "photo2", "url": "https://example.com/image2.jpg"}
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
      "id": "photo1",
      "faces_count": 2,
      "faces": [
        {
          "face_index": 0,
          "embedding": [0.123, -0.456, ...], // 512 dimensions
          "confidence": 0.99
        },
        {
          "face_index": 1,
          "embedding": [0.789, -0.321, ...],
          "confidence": 0.97
        }
      ],
      "error": null
    },
    {
      "id": "photo2",
      "faces_count": 1,
      "faces": [...],
      "error": null
    }
  ]
}
```

#### Single Image (Base64)

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image": "BASE64_ENCODED_IMAGE_HERE",
      "mode": "face"
    }
  }'
```

**Response:**
```json
{
  "faces_count": 1,
  "embedding": [0.123, -0.456, ...], // First face only, 512 dims
  "error": null
}
```

---

### Mode 2: Bib Number Detection Only

#### Batch Processing

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "runner1", "url": "https://example.com/runner1.jpg"},
        {"id": "runner2", "url": "https://example.com/runner2.jpg"}
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
    },
    {
      "id": "runner2",
      "bibs_count": 2,
      "bibs": [
        {
          "number": "789",
          "confidence": 0.92,
          "bbox": [[150, 180], [250, 180], [250, 220], [150, 220]]
        },
        {
          "number": "42",
          "confidence": 0.88,
          "bbox": [[200, 300], [280, 300], [280, 340], [200, 340]]
        }
      ],
      "error": null
    }
  ]
}
```

#### Single Image (Base64)

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image": "BASE64_ENCODED_IMAGE_HERE",
      "mode": "bib"
    }
  }'
```

**Response:**
```json
{
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
```

---

### Mode 3: Both Face + Bib Detection

#### Batch Processing

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "athlete1", "url": "https://example.com/athlete1.jpg"}
      ],
      "mode": "both"
    }
  }'
```

**Response:**
```json
{
  "results": [
    {
      "id": "athlete1",
      "faces_count": 1,
      "faces": [
        {
          "face_index": 0,
          "embedding": [0.123, -0.456, ...],
          "confidence": 0.99
        }
      ],
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

#### Single Image (Base64)

```bash
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image": "BASE64_ENCODED_IMAGE_HERE",
      "mode": "both"
    }
  }'
```

**Response:**
```json
{
  "faces_count": 1,
  "embedding": [0.123, -0.456, ...], // First face only
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
```

---

## Python Examples

### Using requests library

```python
import requests
import base64

API_KEY = "YOUR_RUNPOD_API_KEY"
ENDPOINT_ID = "YOUR_ENDPOINT_ID"

# Batch processing - Both faces and bibs
response = requests.post(
    f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "input": {
            "images": [
                {"id": "img1", "url": "https://example.com/runner1.jpg"},
                {"id": "img2", "url": "https://example.com/runner2.jpg"}
            ],
            "mode": "both"
        }
    }
)

results = response.json()
for item in results["results"]:
    print(f"Image {item['id']}:")
    print(f"  Faces: {item['faces_count']}")
    print(f"  Bibs: {item['bibs_count']}")
    for bib in item["bibs"]:
        print(f"    Bib #{bib['number']} (confidence: {bib['confidence']:.2%})")
```

### Single image with base64

```python
import base64
import requests

# Read and encode image
with open("runner.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = requests.post(
    f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "input": {
            "image": image_b64,
            "mode": "both"
        }
    }
)

result = response.json()
print(f"Detected {result['faces_count']} faces")
print(f"Detected {result['bibs_count']} bibs")
```

---

## JavaScript/TypeScript Example

```typescript
const API_KEY = 'YOUR_RUNPOD_API_KEY';
const ENDPOINT_ID = 'YOUR_ENDPOINT_ID';

async function detectFacesAndBibs(imageUrls: Array<{id: string, url: string}>) {
  const response = await fetch(
    `https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        input: {
          images: imageUrls,
          mode: 'both'
        }
      })
    }
  );

  const data = await response.json();
  return data.results;
}

// Usage
const results = await detectFacesAndBibs([
  { id: 'runner1', url: 'https://example.com/runner1.jpg' },
  { id: 'runner2', url: 'https://example.com/runner2.jpg' }
]);

results.forEach(result => {
  console.log(`${result.id}: ${result.faces_count} faces, ${result.bibs_count} bibs`);
});
```

---

## Performance

### GPU-Accelerated Processing

- **Face detection**: ~50-100ms per image
- **Bib detection**: ~100-200ms per image
- **Both**: ~150-300ms per image

### Batch Processing

- **Max workers**: 10 parallel threads
- **100 images**: ~2-3 minutes (GPU mode)
- **Timeout**: 90s for `/runsync`, unlimited for `/run`

---

## Error Handling

### Per-Image Errors (Batch Mode)

Images with errors return individual error messages without failing the entire batch.

Note: batch responses include fields only for the requested `mode`. The example
below assumes `mode: "both"`.

```json
{
  "results": [
    {
      "id": "bad_image",
      "faces_count": 0,
      "faces": [],
      "bibs_count": 0,
      "bibs": [],
      "error": "Invalid image or URL"
    },
    {
      "id": "good_image",
      "faces_count": 2,
      "faces": [...],
      "error": null
    }
  ]
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid base64 image` | Malformed base64 | Ensure proper encoding |
| `Invalid image or URL` | Bad URL or unreachable image | Verify URL is publicly accessible |
| `Invalid mode` | Wrong mode parameter | Use 'face', 'bib', or 'both' |
| `No valid input provided` | Missing `image` or `images` | Check request format |

---

## Best Practices

1. **Use batch mode** for multiple images (faster than individual requests)
2. **Set mode appropriately** - only detect what you need (`face`, `bib`, or `both`)
3. **Use `/runsync`** for immediate results, `/run` for long batches
4. **Handle per-image errors** in batch mode gracefully
5. **Cache face embeddings** - they're deterministic for the same image
6. **Use cosine similarity** to compare face embeddings

---

## Comparing Face Embeddings

```python
import numpy as np

def cosine_similarity(emb1, emb2):
    """Calculate cosine similarity between two embeddings"""
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

# Get embeddings from two images
embedding1 = result1["embedding"]
embedding2 = result2["embedding"]

similarity = cosine_similarity(embedding1, embedding2)

if similarity > 0.6:
    print("Same person!")
else:
    print("Different people")
```

---

## Support

For issues or questions:
- GitHub: https://github.com/YOUR-USERNAME/runpod-image-processing/issues
- RunPod Docs: https://docs.runpod.io
