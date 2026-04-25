"""
MuAPI HappyHorse 1.0 ComfyUI Nodes
=====================================
Focused nodes for HappyHorse 1.0 video generation via muapi.ai.

  HappyHorseTextToVideo   — POST /api/v1/happy-horse-1-text-to-video-1080p
  HappyHorseImageToVideo  — POST /api/v1/happy-horse-1-image-to-video-1080p

Auth:     x-api-key header
Polling:  GET /api/v1/predictions/{request_id}/result
Upload:   POST /api/v1/upload_file
"""

import io
import os
import time

import numpy as np
import requests
import torch
from PIL import Image

BASE_URL = "https://api.muapi.ai/api/v1"
POLL_INTERVAL = 10
MAX_WAIT = 900

ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"]

# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_api_key(api_key_input):
    """Return api_key_input if set, otherwise fall back to ~/.muapi/config.json."""
    if api_key_input and api_key_input.strip():
        return api_key_input.strip()
    config_path = os.path.expanduser("~/.muapi/config.json")
    if os.path.isfile(config_path):
        try:
            import json as _json
            with open(config_path) as f:
                key = _json.load(f).get("api_key", "")
            if key:
                return key
        except Exception:
            pass
    raise RuntimeError(
        "No API key found. Either paste your key into the api_key field, "
        "or run `muapi auth configure --api-key YOUR_KEY` in a terminal."
    )

def _upload_image(api_key, image_tensor):
    if image_tensor.dim() == 4:
        image_tensor = image_tensor[0]
    arr = (image_tensor.cpu().numpy() * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)
    resp = requests.post(f"{BASE_URL}/upload_file",
                         headers={"x-api-key": api_key},
                         files={"file": ("image.jpg", buf, "image/jpeg")},
                         timeout=120)
    _check(resp)
    return _url(resp.json())

def _url(data):
    u = data.get("url") or data.get("file_url") or data.get("output")
    if not u:
        raise RuntimeError(f"Upload missing URL: {data}")
    return str(u)

def _submit(api_key, endpoint, payload):
    resp = requests.post(f"{BASE_URL}/{endpoint}",
                         headers={"x-api-key": api_key, "Content-Type": "application/json"},
                         json=payload, timeout=60)
    _check(resp)
    rid = resp.json().get("request_id")
    if not rid:
        raise RuntimeError(f"No request_id: {resp.json()}")
    return rid

def _poll(api_key, request_id):
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        resp = requests.get(f"{BASE_URL}/predictions/{request_id}/result",
                            headers={"x-api-key": api_key}, timeout=30)
        _check(resp)
        data = resp.json()
        status = data.get("status")
        print(f"[HappyHorse] {status}  {request_id}")
        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError(f"Failed: {data.get('error', 'unknown')}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Timeout: {request_id}")

def _output_url(result):
    out = result.get("outputs") or result.get("output") or []
    if isinstance(out, list) and out:
        return str(out[0])
    if isinstance(out, str):
        return out
    for k in ("video_url", "url"):
        if result.get(k):
            return str(result[k])
    raise RuntimeError(f"No output URL: {result}")

def _check(resp):
    if resp.status_code == 401:
        raise RuntimeError("Auth failed — check API key.")
    if resp.status_code == 402:
        raise RuntimeError("Insufficient credits — top up at muapi.ai")
    if resp.status_code == 403:
        raise RuntimeError(
            "Access denied. HappyHorse 1.0 is in closed beta and requires a "
            "Pro or Business plan on muapi.ai."
        )
    if resp.status_code == 429:
        raise RuntimeError("Rate limited — retry later.")
    if not resp.ok:
        print(f"[HappyHorse] API ERROR {resp.status_code}: {resp.text[:500]}")
        try:
            err = resp.json()
            raise RuntimeError(f"API {resp.status_code}: {err}")
        except Exception:
            raise RuntimeError(f"API {resp.status_code}: {resp.text[:300]}")

def _first_frame(video_url):
    try:
        import tempfile, cv2
        r = requests.get(video_url, timeout=180, stream=True)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            for chunk in r.iter_content(8192):
                if chunk:
                    tmp.write(chunk)
            path = tmp.name
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        cap.release()
        os.remove(path)
        if not ret:
            raise RuntimeError("no frame")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        return torch.from_numpy(rgb).unsqueeze(0)
    except Exception as e:
        print(f"[HappyHorse] first frame failed: {e}")
        return torch.zeros(1, 64, 64, 3)

# ── Nodes ──────────────────────────────────────────────────────────────────────

class HappyHorseApiKey:
    """
    Store your MuAPI API key once and wire it to any HappyHorse node.
    Leave all node api_key fields empty — they auto-read from this node
    or from ~/.muapi/config.json (set via `muapi auth configure`).
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "api_key": ("STRING", {"multiline": False, "default": "",
                "tooltip": "Your muapi.ai API key. Get one at muapi.ai → Dashboard → API Keys"}),
        }}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("api_key",)
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, api_key):
        return (_load_api_key(api_key),)


class HappyHorseTextToVideo:
    """
    HappyHorse 1.0 Text-to-Video (native 1080p)
    ----------------------------------------------
    Generate native 1080p HD video from a text prompt using Alibaba's
    HappyHorse 1.0 model (Future Life Lab, Taotian Group).

    Endpoint: POST /api/v1/happy-horse-1-text-to-video-1080p

    Aspect ratios: 16:9 | 9:16 | 1:1 | 4:3 | 3:4
    Duration:      4–15 seconds
    Output:        always native 1080p HD (no upscaling)

    NOTE: HappyHorse 1.0 is currently in closed beta on muapi.ai. API-key
    access returns 403 until GA; Pro/Business plan users can try it today
    inside the muapi playground.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "A cinematic aerial shot of a coastal city at golden hour, waves crashing against cliffs, birds flying"}),
            "aspect_ratio": (ASPECT_RATIOS, {"default": "16:9"}),
            "duration": ("INT", {"default": 5, "min": 4, "max": 15, "step": 1,
                "tooltip": "Video duration in seconds (4–15)"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, prompt, aspect_ratio, duration, api_key=""):
        api_key = _load_api_key(api_key)
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": int(duration),
        }
        print("[HappyHorse T2V] Submitting...")
        rid = _submit(api_key, "happy-horse-1-text-to-video-1080p", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse T2V] Done → {url}")
        return (url, _first_frame(url), rid)


class HappyHorseImageToVideo:
    """
    HappyHorse 1.0 Image-to-Video (native 1080p)
    -----------------------------------------------
    Animate a single start-frame image into a native 1080p HD video.

    Endpoint: POST /api/v1/happy-horse-1-image-to-video-1080p

    Provide either an IMAGE input (auto-uploaded) or a direct image_url.
    The video animates outward from this start frame.

    Aspect ratios: 16:9 | 9:16 | 1:1 | 4:3 | 3:4
    Duration:      4–15 seconds
    Output:        always native 1080p HD
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "aspect_ratio": (ASPECT_RATIOS, {"default": "16:9"}),
            "duration": ("INT", {"default": 5, "min": 4, "max": 15, "step": 1,
                "tooltip": "Video duration in seconds (4–15)"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
            "prompt": ("STRING", {"multiline": True, "default": "",
                "tooltip": "Optional text prompt guiding the motion"}),
            "image": ("IMAGE", {"tooltip": "Start-frame image (uploaded automatically)"}),
            "image_url": ("STRING", {"multiline": False, "default": "",
                "tooltip": "Alternative to IMAGE input — direct URL of the start-frame image"}),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, aspect_ratio, duration, api_key="", prompt="", image=None, image_url=""):
        api_key = _load_api_key(api_key)

        if image is not None:
            print("[HappyHorse I2V] Uploading start-frame image...")
            start_url = _upload_image(api_key, image)
        elif image_url and image_url.strip():
            start_url = image_url.strip()
        else:
            raise ValueError("Provide either an `image` input or an `image_url`.")

        payload = {
            "prompt": prompt or "",
            "images_list": [start_url],
            "aspect_ratio": aspect_ratio,
            "duration": int(duration),
        }
        print("[HappyHorse I2V] Submitting...")
        rid = _submit(api_key, "happy-horse-1-image-to-video-1080p", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse I2V] Done → {url}")
        return (url, _first_frame(url), rid)


NODE_CLASS_MAPPINGS = {
    "HappyHorseApiKey":       HappyHorseApiKey,
    "HappyHorseTextToVideo":  HappyHorseTextToVideo,
    "HappyHorseImageToVideo": HappyHorseImageToVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HappyHorseApiKey":       "🔑 HappyHorse 1.0 API Key",
    "HappyHorseTextToVideo":  "🐎 HappyHorse 1.0 Text-to-Video",
    "HappyHorseImageToVideo": "🐎 HappyHorse 1.0 Image-to-Video",
}
