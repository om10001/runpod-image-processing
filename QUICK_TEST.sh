#!/bin/bash

# Quick Test Script for RunPod Face + Bib Detection API
# Replace these with your actual values:

ENDPOINT_ID="YOUR_ENDPOINT_ID_HERE"
API_KEY="YOUR_RUNPOD_API_KEY_HERE"
BASE_URL="https://api.runpod.ai/v2/${ENDPOINT_ID}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "RunPod Face + Bib Detection API Tests"
echo "========================================="
echo ""

# Check if variables are set
if [[ "$ENDPOINT_ID" == "YOUR_ENDPOINT_ID_HERE" ]]; then
    echo -e "${RED}ERROR: Please set ENDPOINT_ID in this script${NC}"
    exit 1
fi

if [[ "$API_KEY" == "YOUR_RUNPOD_API_KEY_HERE" ]]; then
    echo -e "${RED}ERROR: Please set API_KEY in this script${NC}"
    exit 1
fi

echo -e "${YELLOW}Using endpoint: ${ENDPOINT_ID}${NC}"
echo ""

# Test 1: Health Check
echo "========================================"
echo "Test 1: Health Check"
echo "========================================"
curl -s "${BASE_URL}/health" \
  -H "Authorization: Bearer ${API_KEY}" | jq '.'
echo ""
echo ""

# Test 2: Face Detection Only
echo "========================================"
echo "Test 2: Face Detection (mode: face)"
echo "========================================"
curl -s -X POST "${BASE_URL}/runsync" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "test_face",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Albert_Einstein_Head.jpg/800px-Albert_Einstein_Head.jpg"
        }
      ],
      "mode": "face"
    }
  }' | jq '.output.results[0] | {id, faces_count, error}'
echo ""
echo ""

# Test 3: Bib Detection Only
echo "========================================"
echo "Test 3: Bib Detection (mode: bib)"
echo "========================================"
echo -e "${YELLOW}Note: Using generic test image. Replace with actual sports photo for better results.${NC}"
curl -s -X POST "${BASE_URL}/runsync" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "test_bib",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Palace_of_Fine_Arts_%2816794p%29.jpg/1200px-Palace_of_Fine_Arts_%2816794p%29.jpg"
        }
      ],
      "mode": "bib"
    }
  }' | jq '.output.results[0] | {id, bibs_count, bibs, error}'
echo ""
echo ""

# Test 4: Both Face and Bib
echo "========================================"
echo "Test 4: Both Detection (mode: both)"
echo "========================================"
curl -s -X POST "${BASE_URL}/runsync" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "test_both",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Albert_Einstein_Head.jpg/800px-Albert_Einstein_Head.jpg"
        }
      ],
      "mode": "both"
    }
  }' | jq '.output.results[0] | {id, faces_count, bibs_count, error}'
echo ""
echo ""

# Test 5: Batch Processing
echo "========================================"
echo "Test 5: Batch Processing (3 images)"
echo "========================================"
START_TIME=$(date +%s)
curl -s -X POST "${BASE_URL}/runsync" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "img1",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Albert_Einstein_Head.jpg/800px-Albert_Einstein_Head.jpg"
        },
        {
          "id": "img2",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"
        },
        {
          "id": "img3",
          "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Palace_of_Fine_Arts_%2816794p%29.jpg/800px-Palace_of_Fine_Arts_%2816794p%29.jpg"
        }
      ],
      "mode": "both"
    }
  }' | jq '.output.results[] | {id, faces_count, bibs_count}'
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo -e "${GREEN}Batch processing time: ${ELAPSED}s${NC}"
echo ""

# Test 6: Error Handling (Invalid URL)
echo "========================================"
echo "Test 6: Error Handling (invalid URL)"
echo "========================================"
curl -s -X POST "${BASE_URL}/runsync" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "images": [
        {
          "id": "bad_url",
          "url": "https://invalid-url-that-does-not-exist.com/image.jpg"
        }
      ],
      "mode": "face"
    }
  }' | jq '.output.results[0] | {id, error}'
echo ""
echo ""

# Summary
echo "========================================="
echo "Tests Complete!"
echo "========================================="
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test with your own sports photography URLs"
echo "2. Check RunPod dashboard → Telemetry for GPU usage"
echo "3. Monitor execution times for performance"
echo ""
echo -e "${GREEN}For production use, see API_USAGE.md${NC}"
echo ""
