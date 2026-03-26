"""
Test runner for the image processing handler.

─── LOCAL MODE (inside Docker) ──────────────────────────────────────────────
Runs the handler directly — no network, no RunPod credentials needed.

    # All tests
    python test_runner.py --local

    # Specific test
    python test_runner.py --local bib
    python test_runner.py --local face
    python test_runner.py --local both
    python test_runner.py --local single

Docker commands:
    docker run --gpus all \\
        -e FACE_URL="https://your-cdn.com/athlete.jpg" \\
        runpod-face-processing \\
        python test_runner.py --local bib

─── REMOTE MODE (against RunPod endpoint) ───────────────────────────────────
    export RUNPOD_API_KEY="your_key"
    export RUNPOD_ENDPOINT_ID="your_endpoint_id"

    python test_runner.py bib
    python test_runner.py face
    python test_runner.py both
    python test_runner.py single

─── Tests ───────────────────────────────────────────────────────────────────
    bib     — Batch mode, bib detection (uses BIB_URL — istock dorsal image)
    face    — Batch mode, face detection (requires FACE_URL env var)
    both    — Batch mode, face + bib together
    single  — Single mode, base64 image (uses image.b64 — local im.png)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

# ─── Configuration ────────────────────────────────────────────────────────────

API_KEY     = os.getenv("RUNPOD_API_KEY", "")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "")

BIB_URL = (
    "https://media.istockphoto.com/id/1166146739/es/foto/"
    "chica-colocando-el-n%C3%BAmero-de-carrera.jpg"
    "?s=612x612&w=0&k=20&c=xPzGXJnntfHnCcCnfvnhZOWaFwKvjZ-t0ndti1TbOvc="
)

# Set FACE_URL to a public image with a visible face.
FACE_URL = os.getenv("FACE_URL", "")


# ─── Dispatch: local vs remote ────────────────────────────────────────────────

def _call_local(payload: dict) -> dict:
    """Import and call the handler directly — no network overhead."""
    import app as _app
    _handler = _app.Application().handler
    start = time.time()
    output = _handler.handle(payload)
    elapsed = round(time.time() - start, 2)
    return {"output": output, "_elapsed_s": elapsed}


def _call_remote(payload: dict) -> dict:
    """POST to /runsync on the RunPod endpoint."""
    url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        elapsed = round(time.time() - start, 2)
        data = json.loads(resp.read())
    data["_elapsed_s"] = elapsed
    return data


def _call(payload: dict, local: bool) -> dict:
    return _call_local(payload) if local else _call_remote(payload)


# ─── Output formatting ────────────────────────────────────────────────────────

def _print_result(name: str, result: dict) -> None:
    elapsed = result.pop("_elapsed_s", "?")
    print(f"\n{'─'*60}")
    print(f"TEST: {name}  ({elapsed}s)")
    print(f"{'─'*60}")
    output = result.get("output", result)

    if "error" in output and output["error"]:
        print(f"  ERROR: {output['error']}")
        return

    if "results" in output:
        items = output["results"]
        print(f"  Batch results: {len(items)} items")
        for item in items:
            _print_item(item)
    else:
        _print_single(output)


def _print_item(item: dict) -> None:
    img_id = item.get("id", "?")
    if item.get("error"):
        print(f"  [{img_id}] ERROR: {item['error']}")
        return

    parts = [f"id={img_id}"]
    if "faces_count" in item:
        confs = [f"{f['confidence']:.2f}" for f in item.get("faces", [])]
        parts.append(f"faces={item['faces_count']} conf=[{', '.join(confs)}]")
    if "bibs_count" in item:
        nums = [f"{b['number']}({b['confidence']:.2f})" for b in item.get("bibs", [])]
        parts.append(f"bibs={item['bibs_count']} [{', '.join(nums)}]")
    print(f"  {' | '.join(parts)}")


def _print_single(output: dict) -> None:
    if "faces_count" in output:
        embedding = output.get("embedding")
        preview = f"[{embedding[0]:.4f}, ...]  (512 dims)" if embedding else "null"
        print(f"  faces_count: {output['faces_count']}")
        print(f"  embedding:   {preview}")
    if "bibs_count" in output:
        nums = [f"{b['number']}({b['confidence']:.2f})" for b in output.get("bibs", [])]
        print(f"  bibs_count:  {output['bibs_count']}")
        print(f"  bibs:        {nums}")


# ─── Test cases ───────────────────────────────────────────────────────────────

def test_bib_batch(local: bool) -> None:
    """Batch bib detection — istock dorsal image."""
    _print_result(
        "bib batch (dorsal istock)",
        _call({"input": {"mode": "bib", "images": [{"id": "dorsal-1", "url": BIB_URL}]}}, local),
    )


def test_face_batch(local: bool) -> None:
    """Batch face detection — requires FACE_URL env var."""
    if not FACE_URL:
        print("\nTEST: face batch — SKIPPED (set FACE_URL env var to a public image with a face)")
        return
    _print_result(
        "face batch",
        _call({"input": {"mode": "face", "images": [{"id": "face-1", "url": FACE_URL}]}}, local),
    )


def test_both_batch(local: bool) -> None:
    """Batch face + bib detection together."""
    images = [{"id": "dorsal-1", "url": BIB_URL}]
    if FACE_URL:
        images.append({"id": "face-1", "url": FACE_URL})
    _print_result(
        "both batch",
        _call({"input": {"mode": "both", "images": images}}, local),
    )


def test_single_base64(local: bool) -> None:
    """Single mode face detection — uses local image.b64 (im.png)."""
    try:
        with open("image.b64") as f:
            b64 = f.read().strip()
    except FileNotFoundError:
        print("\nTEST: single base64 — SKIPPED (image.b64 not found)")
        return
    _print_result(
        "single base64 (im.png → face)",
        _call({"input": {"mode": "face", "image": b64}}, local),
    )


# ─── Runner ───────────────────────────────────────────────────────────────────

ALL_TESTS = {
    "bib":    test_bib_batch,
    "face":   test_face_batch,
    "both":   test_both_batch,
    "single": test_single_base64,
}

if __name__ == "__main__":
    args = sys.argv[1:]
    local = "--local" in args
    args = [a for a in args if a != "--local"]

    if not local and (not API_KEY or not ENDPOINT_ID):
        print("Remote mode requires credentials:")
        print("  export RUNPOD_API_KEY=your_key")
        print("  export RUNPOD_ENDPOINT_ID=your_endpoint_id")
        print("Or use --local to run inside Docker against the handler directly.")
        sys.exit(1)

    selected = args[0] if args else None

    if selected:
        if selected not in ALL_TESTS:
            print(f"Unknown test '{selected}'. Choose from: {', '.join(ALL_TESTS)}")
            sys.exit(1)
        ALL_TESTS[selected](local)
    else:
        for fn in ALL_TESTS.values():
            fn(local)

    print(f"\n{'─'*60}\nDone.\n")
