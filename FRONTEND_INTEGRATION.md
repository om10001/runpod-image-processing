# Frontend Integration Guide - Face + Bib Detection API

## 📋 Quick Reference

**Your Endpoint:**
- **URL**: `https://api.runpod.ai/v2/dbqlfb3xnm7y24`
- **Sync**: `/runsync` (results immediately, max 90s)
- **Async**: `/run` (returns job ID, poll for results)
- **Status**: `/status/{job_id}` (check job progress)

**Authentication:**
```javascript
headers: {
  'Authorization': 'Bearer YOUR_RUNPOD_API_KEY',
  'Content-Type': 'application/json'
}
```

---

## 🚀 Quick Start Examples

### React/Next.js Example

```typescript
// lib/runpod.ts
const RUNPOD_ENDPOINT = 'https://api.runpod.ai/v2/dbqlfb3xnm7y24';
const RUNPOD_API_KEY = process.env.NEXT_PUBLIC_RUNPOD_API_KEY;

export interface ImageInput {
  id: string;
  url: string;
}

export interface FaceResult {
  face_index: number;
  embedding: number[];  // 512 dimensions
  confidence: number;
}

export interface BibResult {
  number: string;
  confidence: number;
  bbox: [number, number][];  // 4 points
}

export interface ProcessedImage {
  id: string;
  faces_count: number;
  faces?: FaceResult[];
  bibs_count?: number;
  bibs?: BibResult[];
  error: string | null;
}

export type DetectionMode = 'face' | 'bib' | 'both';

/**
 * Process images synchronously (results immediately)
 * Use for: Small batches (<100 images)
 */
export async function processImagesSync(
  images: ImageInput[],
  mode: DetectionMode = 'both'
): Promise<ProcessedImage[]> {
  const response = await fetch(`${RUNPOD_ENDPOINT}/runsync`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RUNPOD_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: {
        images,
        mode,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`RunPod API error: ${response.statusText}`);
  }

  const data = await response.json();
  return data.output.results;
}

/**
 * Process images asynchronously (for large batches)
 * Use for: Batches >100 images, or when you need non-blocking processing
 */
export async function processImagesAsync(
  images: ImageInput[],
  mode: DetectionMode = 'both'
): Promise<string> {
  const response = await fetch(`${RUNPOD_ENDPOINT}/run`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RUNPOD_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: {
        images,
        mode,
      },
    }),
  });

  const data = await response.json();
  return data.id; // Job ID
}

/**
 * Check status of async job
 */
export async function checkJobStatus(jobId: string) {
  const response = await fetch(`${RUNPOD_ENDPOINT}/status/${jobId}`, {
    headers: {
      'Authorization': `Bearer ${RUNPOD_API_KEY}`,
    },
  });

  const data = await response.json();
  return {
    status: data.status, // 'IN_QUEUE', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    output: data.output?.results as ProcessedImage[] | undefined,
    error: data.error,
  };
}

/**
 * Poll for async job completion
 */
export async function waitForJobCompletion(
  jobId: string,
  onProgress?: (status: string) => void
): Promise<ProcessedImage[]> {
  while (true) {
    const { status, output, error } = await checkJobStatus(jobId);

    if (onProgress) {
      onProgress(status);
    }

    if (status === 'COMPLETED' && output) {
      return output;
    }

    if (status === 'FAILED') {
      throw new Error(error || 'Job failed');
    }

    // Wait 2 seconds before polling again
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}
```

### React Component Example

```typescript
// components/ImageProcessor.tsx
'use client';

import { useState } from 'react';
import { processImagesSync, ProcessedImage, ImageInput } from '@/lib/runpod';

export default function ImageProcessor() {
  const [images, setImages] = useState<ImageInput[]>([]);
  const [results, setResults] = useState<ProcessedImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async () => {
    setLoading(true);
    setError(null);

    try {
      const processed = await processImagesSync(images, 'both');
      setResults(processed);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Face + Bib Detection</h2>

      {/* Input Section */}
      <div className="mb-6">
        <textarea
          className="w-full p-3 border rounded"
          rows={5}
          placeholder="Enter image URLs (one per line)"
          onChange={(e) => {
            const urls = e.target.value.split('\n').filter(Boolean);
            setImages(urls.map((url, i) => ({ id: `img_${i}`, url })));
          }}
        />
        <p className="text-sm text-gray-600 mt-2">
          {images.length} images loaded
        </p>
      </div>

      {/* Process Button */}
      <button
        onClick={handleProcess}
        disabled={loading || images.length === 0}
        className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Processing...' : `Process ${images.length} Images`}
      </button>

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Results Display */}
      {results.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xl font-semibold mb-3">Results</h3>
          <div className="space-y-4">
            {results.map((result) => (
              <div key={result.id} className="border p-4 rounded">
                <h4 className="font-semibold">{result.id}</h4>
                {result.error ? (
                  <p className="text-red-600">Error: {result.error}</p>
                ) : (
                  <>
                    <p>Faces detected: {result.faces_count}</p>
                    {result.bibs_count !== undefined && (
                      <div className="mt-2">
                        <p>Bibs detected: {result.bibs_count}</p>
                        {result.bibs?.map((bib, i) => (
                          <div key={i} className="ml-4 mt-1">
                            <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                              #{bib.number}
                            </span>
                            <span className="ml-2 text-sm text-gray-600">
                              {(bib.confidence * 100).toFixed(1)}% confidence
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

### Async Processing for Large Batches

```typescript
// components/LargeBatchProcessor.tsx
'use client';

import { useState } from 'react';
import { processImagesAsync, waitForJobCompletion, ProcessedImage } from '@/lib/runpod';

export default function LargeBatchProcessor() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('IDLE');
  const [results, setResults] = useState<ProcessedImage[]>([]);

  const processBatch = async (imageUrls: string[]) => {
    const images = imageUrls.map((url, i) => ({ id: `img_${i}`, url }));

    // Start async job
    const id = await processImagesAsync(images, 'both');
    setJobId(id);
    setStatus('IN_QUEUE');

    // Wait for completion
    const processed = await waitForJobCompletion(id, (currentStatus) => {
      setStatus(currentStatus);
    });

    setResults(processed);
    setStatus('COMPLETED');
  };

  return (
    <div>
      <p>Job ID: {jobId}</p>
      <p>Status: {status}</p>
      {status === 'COMPLETED' && <p>Processed {results.length} images</p>}
    </div>
  );
}
```

---

## 📊 API Response Formats

### Mode: "face"

**Request:**
```json
{
  "input": {
    "images": [
      {"id": "photo1", "url": "https://example.com/photo1.jpg"}
    ],
    "mode": "face"
  }
}
```

**Response:**
```json
{
  "delayTime": 123,
  "executionTime": 456,
  "id": "job-abc123",
  "output": {
    "results": [
      {
        "id": "photo1",
        "faces_count": 2,
        "faces": [
          {
            "face_index": 0,
            "embedding": [0.123, -0.456, ...],  // 512 floats
            "confidence": 0.99
          },
          {
            "face_index": 1,
            "embedding": [0.789, -0.321, ...],
            "confidence": 0.97
          }
        ],
        "error": null
      }
    ]
  },
  "status": "COMPLETED"
}
```

### Mode: "bib"

**Request:**
```json
{
  "input": {
    "images": [
      {"id": "runner1", "url": "https://example.com/runner.jpg"}
    ],
    "mode": "bib"
  }
}
```

**Response:**
```json
{
  "output": {
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
}
```

### Mode: "both"

**Response includes both `faces` and `bibs` arrays:**
```json
{
  "output": {
    "results": [
      {
        "id": "athlete1",
        "faces_count": 1,
        "faces": [...],
        "bibs_count": 1,
        "bibs": [...]
      }
    ]
  }
}
```

---

## 🎨 UI/UX Patterns

### 1. Progress Indicator for Large Batches

```typescript
function ProcessingProgress({ total, processed }: { total: number; processed: number }) {
  const percentage = (processed / total) * 100;

  return (
    <div className="w-full">
      <div className="flex justify-between text-sm mb-1">
        <span>Processing images...</span>
        <span>{processed}/{total}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

### 2. Face Similarity Comparison

```typescript
function cosineSimilarity(a: number[], b: number[]): number {
  const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
  const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
  const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
  return dotProduct / (magnitudeA * magnitudeB);
}

function FaceComparison({ embedding1, embedding2 }: { embedding1: number[]; embedding2: number[] }) {
  const similarity = cosineSimilarity(embedding1, embedding2);
  const isSamePerson = similarity > 0.6;

  return (
    <div>
      <p>Similarity: {(similarity * 100).toFixed(1)}%</p>
      <p>{isSamePerson ? '✅ Same person' : '❌ Different people'}</p>
    </div>
  );
}
```

### 3. Bib Number Display

```typescript
function BibDisplay({ bib }: { bib: BibResult }) {
  return (
    <div className="inline-flex items-center gap-2 bg-yellow-100 px-3 py-1 rounded">
      <span className="text-2xl font-bold">#{bib.number}</span>
      <span className="text-sm text-gray-600">
        {(bib.confidence * 100).toFixed(0)}% confidence
      </span>
    </div>
  );
}
```

### 4. Image Grid with Results

```typescript
function ImageGrid({ results }: { results: ProcessedImage[] }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {results.map((result) => (
        <div key={result.id} className="border rounded p-2">
          <img src={result.id} alt="" className="w-full h-48 object-cover" />
          <div className="mt-2">
            <div className="flex gap-2">
              <span className="bg-blue-100 px-2 py-1 rounded text-sm">
                {result.faces_count} faces
              </span>
              {result.bibs_count !== undefined && (
                <span className="bg-yellow-100 px-2 py-1 rounded text-sm">
                  {result.bibs_count} bibs
                </span>
              )}
            </div>
            {result.bibs?.map((bib, i) => (
              <div key={i} className="mt-1">
                <span className="font-mono">#{bib.number}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔧 Advanced Patterns

### Batch Processing with Progress

```typescript
async function processBatchWithProgress(
  images: ImageInput[],
  onProgress: (processed: number, total: number) => void
): Promise<ProcessedImage[]> {
  const BATCH_SIZE = 100;
  const batches = [];

  // Split into batches
  for (let i = 0; i < images.length; i += BATCH_SIZE) {
    batches.push(images.slice(i, i + BATCH_SIZE));
  }

  const allResults: ProcessedImage[] = [];

  for (let i = 0; i < batches.length; i++) {
    const results = await processImagesSync(batches[i], 'both');
    allResults.push(...results);
    onProgress(allResults.length, images.length);
  }

  return allResults;
}
```

### Retry Logic

```typescript
async function processWithRetry(
  images: ImageInput[],
  maxRetries = 3
): Promise<ProcessedImage[]> {
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await processImagesSync(images, 'both');
    } catch (error) {
      lastError = error;
      if (attempt < maxRetries) {
        // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
      }
    }
  }

  throw lastError;
}
```

### Caching Results

```typescript
const resultCache = new Map<string, ProcessedImage>();

async function processWithCache(images: ImageInput[]): Promise<ProcessedImage[]> {
  const uncachedImages: ImageInput[] = [];
  const results: ProcessedImage[] = [];

  // Check cache
  for (const img of images) {
    const cached = resultCache.get(img.url);
    if (cached) {
      results.push(cached);
    } else {
      uncachedImages.push(img);
    }
  }

  // Process uncached
  if (uncachedImages.length > 0) {
    const newResults = await processImagesSync(uncachedImages, 'both');

    // Cache results
    newResults.forEach(result => {
      const original = uncachedImages.find(img => img.id === result.id);
      if (original) {
        resultCache.set(original.url, result);
      }
    });

    results.push(...newResults);
  }

  return results;
}
```

---

## 🚨 Error Handling

```typescript
interface RunPodError {
  error: string;
  message?: string;
}

async function safeProcessImages(images: ImageInput[]): Promise<ProcessedImage[]> {
  try {
    return await processImagesSync(images, 'both');
  } catch (error) {
    // Network error
    if (error instanceof TypeError) {
      throw new Error('Network error: Unable to reach RunPod API');
    }

    // API error
    if (error instanceof Response) {
      const errorData: RunPodError = await error.json();
      throw new Error(`API Error: ${errorData.error || errorData.message}`);
    }

    // Unknown error
    throw error;
  }
}
```

---

## 📱 Mobile Considerations

### React Native Example

```typescript
// Using fetch (works in React Native)
import { RUNPOD_ENDPOINT, RUNPOD_API_KEY } from './config';

export async function processImagesRN(imageUrls: string[]) {
  const images = imageUrls.map((url, i) => ({ id: `img_${i}`, url }));

  const response = await fetch(`${RUNPOD_ENDPOINT}/runsync`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RUNPOD_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: { images, mode: 'both' },
    }),
  });

  const data = await response.json();
  return data.output.results;
}
```

---

## 🔐 Security Best Practices

### 1. Never Expose API Key in Frontend

**❌ Bad:**
```typescript
const API_KEY = 'sk-abc123...'; // Exposed in browser!
```

**✅ Good:**
```typescript
// Use backend proxy
export async function processImages(images: ImageInput[]) {
  // Call your backend, which calls RunPod
  const response = await fetch('/api/process-images', {
    method: 'POST',
    body: JSON.stringify({ images }),
  });
  return response.json();
}
```

### 2. Backend Proxy Example (Next.js API Route)

```typescript
// app/api/process-images/route.ts
import { NextRequest, NextResponse } from 'next/server';

const RUNPOD_ENDPOINT = 'https://api.runpod.ai/v2/dbqlfb3xnm7y24';
const RUNPOD_API_KEY = process.env.RUNPOD_API_KEY; // Server-side only!

export async function POST(request: NextRequest) {
  const { images, mode } = await request.json();

  const response = await fetch(`${RUNPOD_ENDPOINT}/runsync`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RUNPOD_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      input: { images, mode: mode || 'both' },
    }),
  });

  const data = await response.json();
  return NextResponse.json(data.output.results);
}
```

---

## 📚 Complete Documentation

For more details, see:
- **[API_USAGE.md](API_USAGE.md)** - Complete API reference
- **[PERFORMANCE_5K.md](PERFORMANCE_5K.md)** - Performance for large batches
- **[START_HERE.md](START_HERE.md)** - Quick start guide

---

## 🎯 Common Use Cases

### Use Case 1: Marathon Photo Platform

```typescript
// Find all photos of a specific bib number
async function findPhotosByBib(bibNumber: string, allPhotos: string[]) {
  const images = allPhotos.map((url, i) => ({ id: url, url }));
  const results = await processImagesSync(images, 'bib');

  return results.filter(result =>
    result.bibs?.some(bib => bib.number === bibNumber)
  );
}
```

### Use Case 2: Face Matching Across Photos

```typescript
// Find all photos with the same person
async function findSimilarFaces(referenceEmbedding: number[], allPhotos: string[]) {
  const images = allPhotos.map((url, i) => ({ id: url, url }));
  const results = await processImagesSync(images, 'face');

  const matches = results.filter(result => {
    return result.faces?.some(face => {
      const similarity = cosineSimilarity(referenceEmbedding, face.embedding);
      return similarity > 0.6; // Threshold for "same person"
    });
  });

  return matches;
}
```

### Use Case 3: Auto-Tagging Athletes

```typescript
// Match faces to bib numbers in the same photo
async function tagAthletes(photoUrls: string[]) {
  const images = photoUrls.map((url, i) => ({ id: url, url }));
  const results = await processImagesSync(images, 'both');

  return results.map(result => ({
    photoUrl: result.id,
    athletes: result.faces?.map((face, i) => ({
      faceEmbedding: face.embedding,
      bibNumber: result.bibs?.[i]?.number || 'unknown',
    })) || [],
  }));
}
```

---

Built with ❤️ for sports photography platforms
