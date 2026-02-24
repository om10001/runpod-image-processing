# 🚀 START HERE - Face + Bib Detection API

Welcome! This guide will help you deploy your Face + Bib Detection API to RunPod in under 10 minutes.

## 📋 What You'll Get

A **GPU-accelerated** serverless API that can:
- ✅ Detect faces and generate 512-dimensional embeddings
- ✅ Recognize bib numbers from sports photos
- ✅ Process batches of images in parallel
- ✅ Return results in 2-6 minutes for 100 images

## 🎯 Quick Start (3 Steps)

### Step 1: Get Your RunPod Account Ready

1. **Sign up/Login**: https://runpod.io
2. **Get your API Key**:
   - Click your profile (top right)
   - Settings → API Keys
   - **Copy** your API key (you'll need this later)

### Step 2: Deploy from GitHub (2 minutes)

Your code is already on GitHub: https://github.com/om10001/runpod-image-processing

**Option A: RunPod Template Builder (EASIEST)**

1. Go to https://runpod.io/console/serverless
2. Click **"Templates"** → **"New Template"**
3. Select **"Build from Repository"**
4. Fill in:
   ```
   Template Name: Face + Bib Detection
   Repository URL: https://github.com/om10001/runpod-image-processing
   Branch: main
   Dockerfile Path: /Dockerfile
   Container Disk: 15 GB
   ✅ Enable "Build with GPU"
   ```
5. Click **"Create Template"** (wait 10-15 min for build)

6. Create Endpoint:
   - **Serverless** → **"New Endpoint"**
   - Select your template
   - **GPU Type**: RTX A5000 (24GB) ✅ RECOMMENDED
   - **Max Workers**: 1
   - **Idle Timeout**: 5 seconds
   - Click **"Create Endpoint"**

**Option B: Docker Hub (Alternative)**

See [DEPLOY_ALTERNATIVE.md](DEPLOY_ALTERNATIVE.md) for Docker Hub deployment.

### Step 3: Test Your API (1 minute)

Once your endpoint is running:

1. **Get your Endpoint ID** from the RunPod dashboard
2. **Edit and run** [QUICK_TEST.sh](QUICK_TEST.sh):
   ```bash
   # Edit these lines in QUICK_TEST.sh:
   ENDPOINT_ID="your-endpoint-id-here"
   API_KEY="your-api-key-here"

   # Run tests
   ./QUICK_TEST.sh
   ```

3. **Verify GPU Usage**:
   - Go to RunPod dashboard → **Telemetry** tab
   - During processing, you should see:
     - ✅ GPU Utilization: 50-100%
     - ✅ GPU Memory: 4-8GB used

**If you see 0% GPU usage**, see [GPU_FIX.md](GPU_FIX.md).

---

## 📚 Documentation Guide

Choose what you need:

| Document | When to Use |
|----------|-------------|
| **[SUMMARY.md](SUMMARY.md)** | Overview of what was implemented |
| **[DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md)** | Detailed step-by-step deployment guide |
| **[API_USAGE.md](API_USAGE.md)** | Complete API reference with examples |
| **[QUICK_TEST.sh](QUICK_TEST.sh)** | Test script to validate your deployment |
| **[GPU_FIX.md](GPU_FIX.md)** | Troubleshooting GPU issues |
| **[DEPLOY_ALTERNATIVE.md](DEPLOY_ALTERNATIVE.md)** | Alternative deployment methods |
| **[README.md](README.md)** | Project overview and features |

---

## 🎨 API Usage Examples

### Example 1: Detect Faces Only

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "photo1", "url": "https://your-image.jpg"}
      ],
      "mode": "face"
    }
  }'
```

### Example 2: Detect Bib Numbers Only

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "runner1", "url": "https://sports-photo.jpg"}
      ],
      "mode": "bib"
    }
  }'
```

### Example 3: Detect Both

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {"id": "athlete1", "url": "https://athlete-photo.jpg"}
      ],
      "mode": "both"
    }
  }'
```

**More examples**: See [API_USAGE.md](API_USAGE.md)

---

## 🔍 How to Verify Everything Works

### ✅ Checklist

After deployment, verify:

- [ ] **Template built successfully** (check "Build Logs" tab)
- [ ] **Endpoint status**: Running (green indicator)
- [ ] **Worker assigned**: GPU type shows RTX A4000/A5000
- [ ] **Startup logs show**:
  ```
  CUDA available: True
  ✓ InsightFace initialized with GPU
  ✓ PaddleOCR initialized with GPU
  ```
- [ ] **Test request returns results** (no timeout)
- [ ] **GPU telemetry shows >0% utilization** during processing

### 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Build fails | Check [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md#troubleshooting) |
| GPU at 0% | See [GPU_FIX.md](GPU_FIX.md) |
| Timeout errors | Increase execution timeout in endpoint settings |
| Slow processing | Verify GPU worker is selected (not CPU) |

---

## 📊 Performance Expectations

### Processing Speed (RTX A5000)

| Images | Mode | Expected Time |
|--------|------|---------------|
| 1 | face | ~30ms |
| 1 | bib | ~50ms |
| 1 | both | ~60ms |
| 100 | face | ~2-3 min |
| 100 | bib | ~3-5 min |
| 100 | both | ~4-6 min |

**First request**: Add 10-15s for model loading (cold start)

### Cost Estimates

RunPod pricing varies by GPU type. Example for RTX A5000 (~$0.50/hour):

- **100 images**: ~$0.04
- **1,000 images**: ~$0.42
- **10,000 images**: ~$4.00

---

## 🎓 Understanding the Modes

### Mode: `face`

**Use when**: You only need face detection/recognition

**Returns**:
- Face count
- 512-dimensional embeddings for each face
- Confidence scores

**Best for**:
- Face matching/similarity
- Identifying same person across photos
- Face-based photo search

### Mode: `bib`

**Use when**: You only need bib numbers

**Returns**:
- Bib count
- Detected numbers (1-5 digits)
- Bounding boxes
- Confidence scores

**Best for**:
- Finding runner numbers
- Searching by bib number
- Organizing race photos by participant

### Mode: `both`

**Use when**: You need to match faces to bib numbers

**Returns**:
- All face data (embeddings, confidence)
- All bib data (numbers, bboxes, confidence)

**Best for**:
- Marathon/race photography platforms
- Auto-tagging athletes
- Matching participants to their photos

---

## 🚀 Production Tips

### Scaling

1. **Start small**: 1 worker initially
2. **Monitor**: Watch queue length in dashboard
3. **Scale up**: Increase max workers based on demand
4. **Auto-scaling**: Enable to handle traffic spikes

### Cost Optimization

1. **Idle timeout**: Set to 5-10s (workers shut down when idle)
2. **Right-size GPU**: A4000 (16GB) for small batches, A5000 (24GB) for large
3. **Mode selection**: Use `face` or `bib` only if you don't need both
4. **Batch processing**: Process multiple images per request (faster + cheaper)

### Error Handling

- ✅ **Per-image errors**: One bad image doesn't fail entire batch
- ✅ **Timeouts**: Use `/run` (async) for batches >100 images
- ✅ **Retries**: Implement retry logic for network errors

---

## 📞 Need Help?

1. **Check docs first**: Most questions answered in [API_USAGE.md](API_USAGE.md) or [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md)
2. **GPU issues**: See [GPU_FIX.md](GPU_FIX.md)
3. **GitHub Issues**: https://github.com/om10001/runpod-image-processing/issues
4. **RunPod Support**: https://discord.gg/runpod

---

## 🎉 You're Ready!

**Next steps**:
1. ✅ Complete [Step 2](#step-2-deploy-from-github-2-minutes) if you haven't
2. ✅ Run [QUICK_TEST.sh](QUICK_TEST.sh) to validate
3. ✅ Test with your own sports photos
4. ✅ Integrate into your application (see [API_USAGE.md](API_USAGE.md))

**Questions?** Start with [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md) for detailed guidance.

---

Built with ❤️ for sports photographers 🏃📸
