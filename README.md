# HappyHorse 1.0 ComfyUI Nodes

> **ComfyUI custom nodes for HappyHorse 1.0** — Alibaba's #1 ranked AI video generation model (1392 Elo I2V, 1333 Elo T2V on Artificial Analysis).
> Generate native 1080p HD videos with integrated audio directly inside ComfyUI using the [muapi.ai](https://muapi.ai) API.
> If you wish to use the Python API directly, check the [HappyHorse 1.0 API](https://github.com/Anil-matcha/HappyHorse-1.0-API)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![HappyHorse 1.0](https://img.shields.io/badge/Model-HappyHorse%201.0-green)](https://muapi.ai)

---

## What is HappyHorse 1.0?

HappyHorse 1.0 is Alibaba's state-of-the-art AI video generation model, built by the Future Life Lab team at Taotian Group. It debuted on April 7, 2026, instantly claiming the top spot in both Text-to-Video and Image-to-Video categories on the Artificial Analysis leaderboard.

- **#1 Ranked**: 1333 Elo T2V, 1392 Elo I2V — surpassing every competitor on the Artificial Analysis leaderboard
- **Native 1080p HD**: Full HD output without upscaling, powered by a 15B-parameter 40-layer Transformer
- **Integrated Audio-Video**: Jointly generates video and audio in a single forward pass — no separate audio pipeline
- **Blazing Fast**: ~10 seconds average generation time
- **Video Edit**: Edit existing videos using natural language prompts

---

## Nodes

| Node | Description |
|------|-------------|
| 🔑 HappyHorse 1.0 API Key | Set your key once — wire to all nodes |
| 🐎 HappyHorse 1.0 Text-to-Video | Generate native 1080p video from a text prompt |
| 🐎 HappyHorse 1.0 Image-to-Video | Animate up to 9 reference images |
| 🐎 HappyHorse 1.0 Text-to-Video + Audio | T2V with jointly generated audio in one pass |
| 🐎 HappyHorse 1.0 Image-to-Video + Audio | I2V with jointly generated audio in one pass |
| 🐎 HappyHorse 1.0 Extend | Seamlessly extend any generated video |
| 🐎 HappyHorse 1.0 Video Edit | Edit existing videos with natural language |
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

1. Sign up at [muapi.ai](https://muapi.ai) and go to **Dashboard → API Keys → Create Key**
2. Right-click the ComfyUI canvas → **Add Node** → **🐎 HappyHorse 1.0**
3. Add a **🔑 HappyHorse 1.0 API Key** node, paste your key, and wire its output to any generation node
4. Write a prompt and hit **Queue Prompt**

> **Tip:** If you use the [MuAPI CLI](https://github.com/SamurAIGPT/muapi-cli), run `muapi auth configure --api-key YOUR_KEY` once and all nodes will pick it up automatically — no need to paste the key anywhere.

---

## Node Reference

### 🔑 HappyHorse 1.0 API Key

Set your muapi.ai API key once and wire the output to all generation nodes. Alternatively, leave every `api_key` field blank — nodes automatically read from `~/.muapi/config.json` if you've authenticated via the CLI.

---

### 🐎 HappyHorse 1.0 Text-to-Video

Generate a native 1080p HD video from a text prompt.

| Field | Values | Default |
|-------|--------|---------|
| `api_key` | Optional — leave blank if using the API Key node or CLI config | — |
| `prompt` | Text describing the video | — |
| `aspect_ratio` | 16:9 / 9:16 / 1:1 | 16:9 |
| `duration` | 5 / 10 seconds | 10 |
| `quality` | 1080p / 4k | 1080p |

**Outputs:** `video_url` · `first_frame` (IMAGE) · `request_id`

---

### 🐎 HappyHorse 1.0 Image-to-Video

Animate reference images into a video. Connect up to 9 images via `image_1` … `image_9` and reference them in the prompt using `@image1` … `@image9`.

**Example prompt:**
```
@image1 comes alive — waves crashing, seagulls calling, ocean breeze, cinematic motion
```

| Field | Values | Default |
|-------|--------|---------|
| `prompt` | Text with optional `@imageN` references | — |
| `aspect_ratio` | 16:9 / 9:16 / 1:1 | 16:9 |
| `duration` | 5 / 10 seconds | 10 |
| `quality` | 1080p / 4k | 1080p |
| `image_1` … `image_9` | Optional — ComfyUI IMAGE tensors (auto-uploaded) | — |

**Outputs:** `video_url` · `first_frame` (IMAGE) · `request_id`

---

### 🐎 HappyHorse 1.0 Text-to-Video + Audio

HappyHorse 1.0's standout feature: jointly generate video and audio in a single Transformer forward pass. Include explicit sound cues in your prompt for richer output.

**Example prompt:**
```
A busy Tokyo street at night, neon signs, rain, traffic noise, jazz music drifting from a bar
```

> **Tip**: Include sound descriptors like "waves crashing", "crowd cheering", "piano melody", "engine roaring" for more accurate and richer audio generation.

---

### 🐎 HappyHorse 1.0 Image-to-Video + Audio

Animate images with jointly generated audio. Reference images with `@image1`, `@image2`, etc.

**Example prompt:**
```
@image1 — waves begin to crash, seagulls cry in the distance, wind howling
```

---

### 🐎 HappyHorse 1.0 Extend

Seamlessly extend any completed HappyHorse 1.0 video. Connect the `request_id` output from any generation node.

| Field | Description |
|-------|-------------|
| `request_id` | From a completed T2V or I2V generation |
| `prompt` | Optional — guide the continuation |
| `duration` | 5 / 10 seconds to add |
| `quality` | 1080p / 4k |

---

### 🐎 HappyHorse 1.0 Video Edit

Edit existing videos using natural language prompts and optional reference images. Provide up to 3 video URLs. Reference images can be used for style guidance.

| Field | Description |
|-------|-------------|
| `prompt` | Describe the desired edits |
| `video_file_1` … `video_file_3` | Pick video from ComfyUI/input/ dropdown |
| `video_url_1` … `video_url_3` | Optional override: http(s) URL or absolute path |
| `image_1` … `image_3` | Optional reference images for style guidance |
| `aspect_ratio` | 16:9 / 9:16 / 1:1 |
| `quality` | 1080p / 4k |

**Example prompts:**
```
Change the weather to a dramatic thunderstorm
Make it look like a vintage 1970s film
Turn day into night with neon city lights
```

---

### 🐎 HappyHorse 1.0 Save Video

Downloads the generated video to ComfyUI's output folder and returns all frames as an IMAGE tensor for use with other nodes (preview, VHS, upscale, etc.).

---

## Example Workflows

Load any `.json` file from this repo via **File → Load** in ComfyUI.

| File | Description |
|------|-------------|
| `HappyHorse_T2V_Example.json` | Basic text-to-video generation |
| `HappyHorse_I2V_Example.json` | Image-to-video animation |

**Text-to-Video:**
```
[🔑 API Key] ──────────────────────────────────┐
                                                ↓
[🐎 Text-to-Video] → video_url → [🐎 Save Video] → frames → [Preview Image]
```

**Image-to-Video with Audio:**
```
[🔑 API Key] ──────────────────────────────────────────────────────────────┐
                                                                            ↓
[LoadImage] → [🐎 Image-to-Video + Audio] → video_url → [🐎 Save Video] → frames → [Preview Image]
               [prompt with audio cues]
```

---

## API

This node pack uses the **muapi.ai** API under the hood:
- **T2V:** `POST https://api.muapi.ai/api/v1/happyhorse-1.0-t2v`
- **I2V:** `POST https://api.muapi.ai/api/v1/happyhorse-1.0-i2v`
- **T2V + Audio:** `POST https://api.muapi.ai/api/v1/happyhorse-1.0-t2v-audio`
- **I2V + Audio:** `POST https://api.muapi.ai/api/v1/happyhorse-1.0-i2v-audio`
- **Extend:** `POST https://api.muapi.ai/api/v1/happyhorse-1.0-extend`
- **Video Edit:** `POST https://api.muapi.ai/api/v1/happyhorse-1.0-video-edit`
- **Poll:** `GET https://api.muapi.ai/api/v1/predictions/{id}/result`
- **Upload:** `POST https://api.muapi.ai/api/v1/upload_file`

Authentication is a single `x-api-key` header — no session tokens required.

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
