# HappyHorse 1.0 ComfyUI Nodes

> **ComfyUI custom nodes for HappyHorse 1.0** — Alibaba's #1 ranked AI video generation model (1392 Elo I2V, 1333 Elo T2V on Artificial Analysis).
> Generate 1080p (or cheaper 720p) videos directly inside ComfyUI using the [muapi.ai](https://muapi.ai) API.
> Prefer raw Python? See the companion [HappyHorse 1.0 API wrapper](https://github.com/Anil-matcha/Awesome-HappyHorse-1.0-API-and-Prompt).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![HappyHorse 1.0](https://img.shields.io/badge/Model-HappyHorse%201.0-green)](https://muapi.ai)

---

## What is HappyHorse 1.0?

HappyHorse 1.0 is Alibaba's state-of-the-art AI video generation model, built by the Future Life Lab team at Taotian Group. It debuted on April 7, 2026, instantly claiming the top spot in both Text-to-Video and Image-to-Video categories on the Artificial Analysis leaderboard.

- **#1 Ranked** — 1333 Elo T2V, 1392 Elo I2V
- **Native 1080p HD** — full HD output without upscaling, powered by a 15B-parameter 40-layer Transformer
- **720p option** — same model, ~half the cost, available on every node via the `resolution` selector
- **Integrated audio-video** — jointly generates video and synchronized audio in a single Transformer forward pass
- **Fast** — ~10 seconds typical generation time

---

## Nodes

| Node | Description |
|------|-------------|
| 🔑 HappyHorse 1.0 API Key | Set your key once — wire to all nodes |
| 🐎 HappyHorse 1.0 Text-to-Video | Generate 1080p / 720p video from a text prompt |
| 🐎 HappyHorse 1.0 Image-to-Video | Animate a start-frame image into 1080p / 720p video |
| 🐎 HappyHorse 1.0 Save Video | Download URL → disk + ComfyUI IMAGE frames |

---

## Installation

### Via ComfyUI Manager (recommended)
1. Open **ComfyUI Manager** → **Install via Git URL**
2. Paste: `https://github.com/Anil-matcha/happyhorse-comfyui`
3. Restart ComfyUI

### Manual
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Anil-matcha/happyhorse-comfyui
pip install -r happyhorse-comfyui/requirements.txt
```

---

## Quick Start

1. Sign up at [muapi.ai](https://muapi.ai) and grab a key from **Dashboard → API Keys → Create Key** .
2. Right-click the ComfyUI canvas → **Add Node** → **🐎 HappyHorse 1.0**.
3. Add a **🔑 HappyHorse 1.0 API Key** node, paste your key, and wire its output into any generation node.
4. Write a prompt and hit **Queue Prompt**.

> **Tip:** If you use the [MuAPI CLI](https://github.com/SamurAIGPT/muapi-cli), run `muapi auth configure --api-key YOUR_KEY` once and every node will pick the key up automatically — no need to paste it anywhere.

---

## Node Reference

### 🔑 HappyHorse 1.0 API Key

Set your muapi.ai API key once and wire the output to all generation nodes. Alternatively, leave every `api_key` field blank — nodes auto-read from `~/.muapi/config.json` if you've authenticated via the CLI.

---

### 🐎 HappyHorse 1.0 Text-to-Video

Generate a HappyHorse 1.0 video from a text prompt. HappyHorse 1.0 jointly generates synchronized audio with the video, so feel free to include sound cues (e.g. _"rain pattering on leaves"_, _"crowd cheering"_, _"piano melody drifting"_) right inside your prompt.

| Field | Values | Default |
|-------|--------|---------|
| `api_key` | Optional — leave blank if using the API Key node or CLI config | — |
| `prompt` | Text describing the video (and any sound cues) | — |
| `aspect_ratio` | `16:9` / `9:16` / `1:1` / `4:3` / `3:4` | `16:9` |
| `duration` | Seconds, integer 4 – 15 | `5` |
| `resolution` | `1080p` / `720p` (720p costs ~half) | `1080p` |

**Outputs:** `video_url` · `first_frame` (IMAGE) · `request_id`

**Endpoint:** `POST /api/v1/happy-horse-1-text-to-video-{1080p|720p}` (selected from the `resolution` widget)

---

### 🐎 HappyHorse 1.0 Image-to-Video

Animate a single start-frame image into a HappyHorse 1.0 video. The model animates outward from the supplied image; the prompt is optional and guides the motion.

| Field | Values | Default |
|-------|--------|---------|
| `api_key` | Optional | — |
| `prompt` | Optional — guides the motion | — |
| `image` | ComfyUI IMAGE (auto-uploaded to muapi) | — |
| `image_url` | Alternative to IMAGE input — direct URL of the start frame | — |
| `aspect_ratio` | `16:9` / `9:16` / `1:1` / `4:3` / `3:4` | `16:9` |
| `duration` | Seconds, integer 4 – 15 | `5` |
| `resolution` | `1080p` / `720p` (720p costs ~half) | `1080p` |

Provide **either** `image` **or** `image_url` (not both). Audio is generated jointly with the video — include sound cues in the prompt for richer output.

**Outputs:** `video_url` · `first_frame` (IMAGE) · `request_id`

**Endpoint:** `POST /api/v1/happy-horse-1-image-to-video-{1080p|720p}` (selected from the `resolution` widget)

---

### 🐎 HappyHorse 1.0 Save Video

Downloads the generated video to ComfyUI's output folder and returns all frames as an IMAGE tensor for use with other nodes (preview, VHS, upscale, etc.).

| Field | Description |
|-------|-------------|
| `video_url` | URL returned by a generation node |
| `save_subfolder` | Subfolder under `ComfyUI/output/` |
| `filename_prefix` | Filename prefix |
| `frame_load_cap` | Optional max frames returned (0 = all) |
| `skip_first_frames` | Skip N frames from the start |
| `select_every_nth` | Stride for frame selection |

**Outputs:** `frames` (IMAGE) · `filepath` (STRING) · `frame_count` (INT)

---

## Example Workflows

Load any `.json` file from this repo via **File → Load** in ComfyUI.

| File | Description |
|------|-------------|
| `HappyHorse_T2V_Example.json` | Basic text-to-video generation |
| `HappyHorse_I2V_Example.json` | Image-to-video animation |

**Text-to-Video:**
```
[🔑 API Key] ──────────────────────────────────────┐
                                                    ↓
[🐎 Text-to-Video] → video_url → [🐎 Save Video] → frames → [Preview Image]
```

**Image-to-Video:**
```
[🔑 API Key] ──────────────────────────────────────────────────────────────┐
                                                                            ↓
[LoadImage] → [🐎 Image-to-Video] → video_url → [🐎 Save Video] → frames → [Preview Image]
```

---

## API

This node pack uses the **muapi.ai** API under the hood:

- **T2V 1080p:** `POST https://api.muapi.ai/api/v1/happy-horse-1-text-to-video-1080p`
- **T2V 720p:**  `POST https://api.muapi.ai/api/v1/happy-horse-1-text-to-video-720p`  *(~half the 1080p cost)*
- **I2V 1080p:** `POST https://api.muapi.ai/api/v1/happy-horse-1-image-to-video-1080p`
- **I2V 720p:**  `POST https://api.muapi.ai/api/v1/happy-horse-1-image-to-video-720p`  *(~half the 1080p cost)*
- **Poll:**      `GET  https://api.muapi.ai/api/v1/predictions/{request_id}/result`
- **Upload:**    `POST https://api.muapi.ai/api/v1/upload_file`

Authentication is a single `x-api-key` header — no session tokens required.

The submit-then-poll flow is identical for both endpoints:

```
POST /api/v1/happy-horse-1-...   →  { "request_id": "abc123" }
GET  /api/v1/predictions/abc123/result
                                  →  { "status": "processing" }       (keep polling)
                                  →  { "status": "completed",
                                       "outputs": ["https://.../video.mp4"] }
```

Status values: `queued`, `pending`, `processing`, `completed`, `failed`.

---

## Requirements

- Python ≥ 3.8
- `requests` ≥ 2.28 · `Pillow` ≥ 9.0 · `numpy` ≥ 1.23 · `torch` ≥ 2.0 · `opencv-python` ≥ 4.7

---

## Want More Models?

This repo is focused on HappyHorse 1.0 only. If you need access to **100+ models** — Kling, Veo3, Flux, HiDream, GPT-image-1.5, Imagen4, Wan, lipsync, audio, image enhancement and more — check out the full MuAPI ComfyUI node pack:

**[SamurAIGPT/muapi-comfyui](https://github.com/SamurAIGPT/muapi-comfyui)** — ComfyUI nodes for every muapi.ai model in one place.

---

## License

MIT © 2026
