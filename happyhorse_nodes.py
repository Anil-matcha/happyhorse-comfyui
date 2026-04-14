"""
MuAPI HappyHorse 1.0 ComfyUI Nodes
=====================================
Focused nodes for HappyHorse 1.0 video generation via muapi.ai.

  HappyHorseTextToVideo        — POST /api/v1/happyhorse-1.0-t2v
  HappyHorseImageToVideo       — POST /api/v1/happyhorse-1.0-i2v
  HappyHorseTextToVideoAudio   — POST /api/v1/happyhorse-1.0-t2v-audio
  HappyHorseImageToVideoAudio  — POST /api/v1/happyhorse-1.0-i2v-audio
  HappyHorseExtend             — POST /api/v1/happyhorse-1.0-extend
  HappyHorseVideoEdit          — POST /api/v1/happyhorse-1.0-video-edit

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

VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")

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

def _resolve_video_ref(api_key, ref):
    """Resolve a video reference to a URL (upload local file or return URL as-is)."""
    import mimetypes
    if not ref or not ref.strip():
        return None
    ref = ref.strip().strip('"').strip("'")
    if ref.lower().startswith(("http://", "https://")):
        return ref
    path = ref
    if not os.path.isfile(path):
        try:
            import folder_paths
            candidate = os.path.join(folder_paths.get_input_directory(), ref)
            if os.path.isfile(candidate):
                path = candidate
        except Exception:
            pass
    if not os.path.isfile(path):
        raise RuntimeError(
            f"[HappyHorse] Video reference not found: {ref!r}. "
            f"Provide an http(s) URL, an absolute file path, or a filename inside ComfyUI/input/."
        )
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "video/mp4"
    filename = os.path.basename(path)
    print(f"[HappyHorse] Uploading video: {filename}")
    with open(path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/upload_file",
            headers={"x-api-key": api_key},
            files={"file": (filename, f, mime)},
            timeout=600,
        )
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
    HappyHorse 1.0 Text-to-Video
    ------------------------------
    Generate native 1080p HD video from a text prompt using Alibaba's #1 ranked
    AI video model (1333 Elo T2V on Artificial Analysis leaderboard).

    HappyHorse uses a 15B-parameter 40-layer Transformer architecture to produce
    full HD output without upscaling, typically in ~10 seconds.

    Aspect ratios: 16:9 | 9:16 | 1:1
    Duration: 5 | 10 seconds
    Quality: 1080p | 4k
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "A cinematic aerial shot of a coastal city at golden hour, waves crashing against cliffs, birds flying"}),
            "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
            "duration": ([5, 10], {"default": 10}),
            "quality": (["1080p", "4k"], {"default": "1080p"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, prompt, aspect_ratio, duration, quality, api_key=""):
        api_key = _load_api_key(api_key)
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "quality": quality,
        }
        print("[HappyHorse T2V] Submitting...")
        rid = _submit(api_key, "happyhorse-1.0-t2v", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse T2V] Done → {url}")
        return (url, _first_frame(url), rid)


class HappyHorseImageToVideo:
    """
    HappyHorse 1.0 Image-to-Video
    --------------------------------
    Animate static images into native 1080p video using HappyHorse 1.0
    (#1 ranked I2V on Artificial Analysis, 1392 Elo).

    Connect up to 9 images and reference them in the prompt using
    @image1 … @image9.

    Example prompt:
        "@image1 comes alive — waves crashing, seagulls calling, ocean breeze"
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "@image1 comes alive with gentle motion, cinematic lighting, 1080p"}),
            "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
            "duration": ([5, 10], {"default": 10}),
            "quality": (["1080p", "4k"], {"default": "1080p"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
            "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
            "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
            "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, prompt, aspect_ratio, duration, quality, api_key="",
            image_1=None, image_2=None, image_3=None, image_4=None, image_5=None,
            image_6=None, image_7=None, image_8=None, image_9=None):
        api_key = _load_api_key(api_key)
        tensors = [image_1, image_2, image_3, image_4, image_5,
                   image_6, image_7, image_8, image_9]
        images_list = []
        for i, img in enumerate(tensors, 1):
            if img is not None:
                print(f"[HappyHorse I2V] Uploading image {i}...")
                images_list.append(_upload_image(api_key, img))
        if not images_list:
            raise ValueError("At least one image is required for Image-to-Video.")
        payload = {
            "prompt": prompt,
            "images_list": images_list,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "quality": quality,
        }
        print(f"[HappyHorse I2V] Submitting ({len(images_list)} image(s))...")
        rid = _submit(api_key, "happyhorse-1.0-i2v", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse I2V] Done → {url}")
        return (url, _first_frame(url), rid)


class HappyHorseTextToVideoAudio:
    """
    HappyHorse 1.0 Text-to-Video with Integrated Audio
    ------------------------------------------------------
    Generate video AND synchronized audio in a single Transformer forward
    pass — no separate audio pipeline needed.

    HappyHorse 1.0 jointly generates audio and video, so include explicit
    sound cues in your prompt for richer output:
      "rain pattering on leaves", "crowd cheering", "piano melody drifting"

    Aspect ratios: 16:9 | 9:16 | 1:1
    Duration: 5 | 10 seconds
    Quality: 1080p | 4k
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "A thunderstorm rolling over mountains, lightning flashing, thunder rumbling, rain pattering on leaves"}),
            "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
            "duration": ([5, 10], {"default": 10}),
            "quality": (["1080p", "4k"], {"default": "1080p"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, prompt, aspect_ratio, duration, quality, api_key=""):
        api_key = _load_api_key(api_key)
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "quality": quality,
        }
        print("[HappyHorse T2V+Audio] Submitting...")
        rid = _submit(api_key, "happyhorse-1.0-t2v-audio", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse T2V+Audio] Done → {url}")
        return (url, _first_frame(url), rid)


class HappyHorseImageToVideoAudio:
    """
    HappyHorse 1.0 Image-to-Video with Integrated Audio
    -------------------------------------------------------
    Animate images with jointly generated audio in one Transformer pass.

    Reference images in the prompt using @image1, @image2, etc. Include
    ambient sound cues for richer audio output:
      "@image1 comes alive — waves crashing, seagulls calling, ocean breeze"

    Aspect ratios: 16:9 | 9:16 | 1:1
    Duration: 5 | 10 seconds
    Quality: 1080p | 4k
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "@image1 comes alive — waves crashing, seagulls calling, ocean breeze"}),
            "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
            "duration": ([5, 10], {"default": 10}),
            "quality": (["1080p", "4k"], {"default": "1080p"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
            "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
            "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
            "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, prompt, aspect_ratio, duration, quality, api_key="",
            image_1=None, image_2=None, image_3=None, image_4=None, image_5=None,
            image_6=None, image_7=None, image_8=None, image_9=None):
        api_key = _load_api_key(api_key)
        tensors = [image_1, image_2, image_3, image_4, image_5,
                   image_6, image_7, image_8, image_9]
        images_list = []
        for i, img in enumerate(tensors, 1):
            if img is not None:
                print(f"[HappyHorse I2V+Audio] Uploading image {i}...")
                images_list.append(_upload_image(api_key, img))
        if not images_list:
            raise ValueError("At least one image is required for Image-to-Video with Audio.")
        payload = {
            "prompt": prompt,
            "images_list": images_list,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "quality": quality,
        }
        print(f"[HappyHorse I2V+Audio] Submitting ({len(images_list)} image(s))...")
        rid = _submit(api_key, "happyhorse-1.0-i2v-audio", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse I2V+Audio] Done → {url}")
        return (url, _first_frame(url), rid)


class HappyHorseExtend:
    """
    HappyHorse 1.0 Video Extend
    -----------------------------
    Seamlessly extend a previously generated HappyHorse 1.0 video while
    maintaining consistent style and motion.

    Pass the request_id from a completed generation node.
    Optionally provide a prompt to guide the continuation.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "request_id": ("STRING", {"multiline": False, "default": "",
                "tooltip": "request_id from a completed HappyHorse generation"}),
            "duration": ([5, 10], {"default": 10}),
            "quality": (["1080p", "4k"], {"default": "1080p"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
            "prompt": ("STRING", {"multiline": True, "default": "",
                "tooltip": "Optional prompt to guide the video continuation"}),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "new_request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, request_id, duration, quality, api_key="", prompt=""):
        api_key = _load_api_key(api_key)
        if not request_id.strip():
            raise ValueError("request_id is required.")
        payload = {
            "request_id": request_id.strip(),
            "duration": duration,
            "quality": quality,
        }
        if prompt.strip():
            payload["prompt"] = prompt.strip()
        print(f"[HappyHorse Extend] Extending {request_id}...")
        new_id = _submit(api_key, "happyhorse-1.0-extend", payload)
        result = _poll(api_key, new_id)
        url = _output_url(result)
        print(f"[HappyHorse Extend] Done → {url}")
        return (url, _first_frame(url), new_id)


class HappyHorseVideoEdit:
    """
    HappyHorse 1.0 Video Edit
    ---------------------------
    Edit existing videos using natural language prompts and optional
    reference images. Transform weather, style, lighting, objects, and more.

    Provide up to 3 video URLs to edit. Optionally add reference images
    for style guidance.

    Example prompt:
        "Change the weather to a dramatic thunderstorm"
        "Make it look like a vintage film from the 1970s"
    """
    @classmethod
    def INPUT_TYPES(cls):
        video_files = _list_input_files()
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "Change the weather to a dramatic thunderstorm with lightning"}),
            "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
            "quality": (["1080p", "4k"], {"default": "1080p"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
            # Video references: dropdown picker or URL/path override
            "video_file_1": (video_files, {"default": "(none)"}),
            "video_url_1":  ("STRING", {"multiline": False, "default": "",
                "tooltip": "http(s) URL or absolute path (used if dropdown is (none))"}),
            "video_file_2": (video_files, {"default": "(none)"}),
            "video_url_2":  ("STRING", {"multiline": False, "default": ""}),
            "video_file_3": (video_files, {"default": "(none)"}),
            "video_url_3":  ("STRING", {"multiline": False, "default": ""}),
            # Optional reference images
            "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
        }}
    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("video_url", "first_frame", "request_id")
    FUNCTION = "run"
    CATEGORY = "🐎 HappyHorse 1.0"

    def run(self, prompt, aspect_ratio, quality, api_key="",
            video_file_1="(none)", video_url_1="",
            video_file_2="(none)", video_url_2="",
            video_file_3="(none)", video_url_3="",
            image_1=None, image_2=None, image_3=None):
        api_key = _load_api_key(api_key)

        def pick(dropdown, url):
            return dropdown if (dropdown and dropdown != "(none)") else url

        video_urls = []
        for f, u in [(video_file_1, video_url_1), (video_file_2, video_url_2), (video_file_3, video_url_3)]:
            resolved = _resolve_video_ref(api_key, pick(f, u))
            if resolved:
                video_urls.append(resolved)

        if not video_urls:
            raise ValueError("At least one video is required for Video Edit.")

        images_list = []
        for i, img in enumerate([image_1, image_2, image_3], 1):
            if img is not None:
                print(f"[HappyHorse VideoEdit] Uploading reference image {i}...")
                images_list.append(_upload_image(api_key, img))

        payload = {
            "prompt": prompt,
            "video_urls": video_urls,
            "aspect_ratio": aspect_ratio,
            "quality": quality,
        }
        if images_list:
            payload["images_list"] = images_list

        print(f"[HappyHorse VideoEdit] Submitting ({len(video_urls)} video(s))...")
        rid = _submit(api_key, "happyhorse-1.0-video-edit", payload)
        result = _poll(api_key, rid)
        url = _output_url(result)
        print(f"[HappyHorse VideoEdit] Done → {url}")
        return (url, _first_frame(url), rid)


def _list_input_files():
    """Return sorted list of video files in ComfyUI/input/."""
    try:
        import folder_paths
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
            and f.lower().endswith(VIDEO_EXTS)
        ]
        return ["(none)"] + sorted(files)
    except Exception:
        return ["(none)"]


NODE_CLASS_MAPPINGS = {
    "HappyHorseApiKey":             HappyHorseApiKey,
    "HappyHorseTextToVideo":        HappyHorseTextToVideo,
    "HappyHorseImageToVideo":       HappyHorseImageToVideo,
    "HappyHorseTextToVideoAudio":   HappyHorseTextToVideoAudio,
    "HappyHorseImageToVideoAudio":  HappyHorseImageToVideoAudio,
    "HappyHorseExtend":             HappyHorseExtend,
    "HappyHorseVideoEdit":          HappyHorseVideoEdit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HappyHorseApiKey":             "🔑 HappyHorse 1.0 API Key",
    "HappyHorseTextToVideo":        "🐎 HappyHorse 1.0 Text-to-Video",
    "HappyHorseImageToVideo":       "🐎 HappyHorse 1.0 Image-to-Video",
    "HappyHorseTextToVideoAudio":   "🐎 HappyHorse 1.0 Text-to-Video + Audio",
    "HappyHorseImageToVideoAudio":  "🐎 HappyHorse 1.0 Image-to-Video + Audio",
    "HappyHorseExtend":             "🐎 HappyHorse 1.0 Extend",
    "HappyHorseVideoEdit":          "🐎 HappyHorse 1.0 Video Edit",
}
