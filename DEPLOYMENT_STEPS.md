# RunPod Deployment Steps - Face + Bib Detection

## Prerequisites

- ✅ Code pushed to GitHub: https://github.com/om10001/runpod-image-processing
- ✅ RunPod account with API key
- ✅ GitHub repository is public (or RunPod has access)

## Step 1: Create RunPod Template from GitHub

### 1.1 Navigate to RunPod Console

Go to: https://runpod.io/console/serverless

### 1.2 Create New Template

1. Click **"Templates"** in left sidebar
2. Click **"New Template"** button
3. Select **"Build from Repository"**

### 1.3 Configure Template

Fill in the following:

| Field | Value |
|-------|-------|
| **Template Name** | `Face + Bib Detection` |
| **Repository URL** | `https://github.com/om10001/runpod-image-processing` |
| **Branch** | `main` |
| **Dockerfile Path** | `/Dockerfile` |
| **Container Disk** | `15 GB` (PaddleOCR models are large) |
| **Build with GPU** | ✅ **ENABLED** (check this box) |

**Important Notes:**
- Container disk must be 15GB+ to fit both InsightFace and PaddleOCR models
- "Build with GPU" must be enabled for CUDA support

### 1.4 Advanced Settings (Optional)

If you need custom environment variables:
- Click "Advanced Options"
- Add any environment variables (none required by default)

### 1.5 Create Template

Click **"Create Template"** button

**Wait time**: 10-20 minutes for first build
- RunPod will clone your repo
- Build the Docker image with CUDA support
- Download InsightFace and PaddleOCR models (~8GB total)

You can monitor build progress in the "Build Logs" tab.

## Step 2: Create Serverless Endpoint

### 2.1 Navigate to Endpoints

1. Click **"Serverless"** in left sidebar
2. Click **"New Endpoint"** button

### 2.2 Configure Endpoint

| Field | Value |
|-------|-------|
| **Endpoint Name** | `face-bib-detection` (or your choice) |
| **Select Template** | Select the template created in Step 1 |
| **GPU Type** | ⚠️ **MUST BE GPU** - Recommended: |
|  | - RTX A4000 (16GB) |
|  | - RTX A5000 (24GB) ✅ Best |
|  | - RTX 3090 (24GB) |
| **Max Workers** | `1` (start small, scale later) |
| **Idle Timeout** | `5` seconds (keep workers warm) |
| **GPUs per Worker** | `1` |
| **Execution Timeout** | `90` seconds (for `/runsync`) |

**Critical**: Do NOT select CPU-only workers. The function requires GPU.

### 2.3 Advanced Settings

**Recommended configurations:**

```
Container Disk: 15 GB
Memory: 16 GB (minimum)
vCPUs: 4+ (for parallel batch processing)
```

### 2.4 Create Endpoint

Click **"Create Endpoint"**

## Step 3: Verify Deployment

### 3.1 Check Worker Status

1. In your endpoint dashboard, check **"Workers"** tab
2. Wait for worker status: **"Running"**
3. Initial cold start: 10-15 seconds (model loading)

### 3.2 Check Startup Logs

Click **"Logs"** tab and verify you see:

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

**If you see `CUDA available: False`:**
- ❌ You selected CPU worker instead of GPU
- Solution: Edit endpoint → Change GPU type to RTX A4000/A5000

### 3.3 Get Endpoint ID and API Key

1. Copy your **Endpoint ID** from the endpoint dashboard (e.g., `abc123xyz`)
2. Copy your **API Key** from Account Settings

Your API base URL will be:
```
https://api.runpod.ai/v2/{ENDPOINT_ID}
```

## Step 4: Test the Endpoint

### 4.1 Test Face Detection (Mode: face)

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "test1",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"
        }
      ],
      "mode": "face"
    }
  }'
```

**Expected response:**
```json
{
  "delayTime": 123,
  "executionTime": 456,
  "id": "job-id-here",
  "output": {
    "results": [
      {
        "id": "test1",
        "faces_count": 0,  // Cat image has no faces
        "faces": [],
        "error": null
      }
    ]
  },
  "status": "COMPLETED"
}
```

### 4.2 Test Bib Detection (Mode: bib)

Use a sports photo with visible bib numbers:

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "runner1",
          "url": "YOUR_SPORTS_PHOTO_URL"
        }
      ],
      "mode": "bib"
    }
  }'
```

### 4.3 Test Both (Mode: both)

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "athlete1",
          "url": "YOUR_SPORTS_PHOTO_URL"
        }
      ],
      "mode": "both"
    }
  }'
```

## Step 5: Monitor Performance

### 5.1 Check GPU Utilization

In RunPod dashboard → Telemetry tab:

**If GPU is being used:**
- ✅ GPU Utilization: 50-100% during processing
- ✅ GPU Memory: 4-8GB used
- ✅ Processing time: ~2-6 min per 100 images

**If GPU is NOT being used:**
- ❌ GPU Utilization: 0%
- ❌ CPU: 100%
- ❌ Processing time: 60+ min per 100 images
- **Solution**: See [GPU_FIX.md](GPU_FIX.md)

### 5.2 Check Execution Times

Good performance indicators:
- **Cold start**: 10-15s (first request, models loading)
- **Warm start**: 150-300ms per image (mode: both)
- **Batch (100 images)**: 4-6 minutes (mode: both)

## Step 6: Scale Your Deployment

### 6.1 Increase Workers

If you have high traffic:
1. Edit endpoint
2. Increase **"Max Workers"** to 3-5
3. Workers auto-scale based on queue

### 6.2 Configure Auto-scaling

```
Min Workers: 1 (always keep one warm)
Max Workers: 5 (scale based on traffic)
Scale Down Delay: 30 seconds
```

### 6.3 Cost Optimization

**Idle timeout**: Set to 5-10 seconds
- Workers shut down after 10s of inactivity
- Saves costs when not in use
- Trade-off: Cold starts on next request

## Troubleshooting

### Issue: "CUDA not available"

**Check:**
1. Template was built with "Build with GPU" enabled
2. Endpoint uses GPU worker (not CPU)
3. Dockerfile uses `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`

**Solution:**
- Rebuild template with GPU enabled
- Change worker type to RTX A4000/A5000

### Issue: Slow processing (60+ min for 100 images)

**Cause**: Running on CPU instead of GPU

**Solution**: See [GPU_FIX.md](GPU_FIX.md)

### Issue: OOM (Out of Memory) errors

**Cause**: Batch size too large for GPU VRAM

**Solutions:**
1. Reduce parallel workers in code (`MAX_WORKERS` in app.py)
2. Use larger GPU (24GB instead of 16GB)
3. Process smaller batches

### Issue: Template build fails

**Check build logs for:**
- `pip install` errors → Missing dependencies?
- `COPY` errors → File paths correct?
- Timeout → Increase build timeout in template settings

**Common fixes:**
- Ensure `requirements.txt` is in repository root
- Verify Dockerfile path is `/Dockerfile`
- Check GitHub repository is public or RunPod has access

## Next Steps

### Production Checklist

- [ ] Test all three modes (face, bib, both)
- [ ] Verify GPU utilization in telemetry
- [ ] Test with your actual image dataset
- [ ] Set up monitoring/alerts
- [ ] Configure auto-scaling based on traffic
- [ ] Add error handling in your application
- [ ] Consider using `/run` for long batches (>90s)
- [ ] Cache face embeddings to reduce costs

### Integration Examples

See [API_USAGE.md](API_USAGE.md) for:
- Python client examples
- JavaScript/TypeScript examples
- Error handling patterns
- Batch processing best practices

## Support

- **GitHub Issues**: https://github.com/om10001/runpod-image-processing/issues
- **RunPod Docs**: https://docs.runpod.io
- **RunPod Discord**: https://discord.gg/runpod

---

**Deployment completed!** 🎉

Your Face + Bib Detection API is now live on RunPod.
