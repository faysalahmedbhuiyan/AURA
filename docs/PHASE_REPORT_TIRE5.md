# Tier 5 — AI Generation Engine — Status Report

**Last updated:** 2026-07-27
**Status:** ✅ Image generation WORKING (CPU). GPU (DirectML) attempted, not viable with current model/hardware combo — documented below so nobody re-tries the same dead ends.

---

## Hardware

```
CPU: Intel i5 11th Gen
RAM: 8GB
GPU: Intel Iris Xe (Shared 3.9GB VRAM), DirectML available
Disk D:\: models stored here
OS: Windows
```

---

## Working Configuration (DO NOT casually change these)

| Component              | Value                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| Model                  | `stabilityai/sd-turbo` (**not** SDXL Turbo — see "Why not SDXL Turbo" below)                |
| Export format          | ONNX, **fp32** (fp16 conversion attempted, broke type consistency — see below)              |
| Execution provider     | **CPUExecutionProvider** (DirectML fails at generation time — see below)                    |
| Resolution             | 512x512                                                                                     |
| Steps                  | 1 (schema allows 1-4)                                                                       |
| Guidance scale         | 0.0 (required for Turbo models)                                                             |
| First generation time  | ~117 seconds (includes one-time pipeline load into RAM)                                     |
| Subsequent generations | Should be faster — pipeline stays cached until `/image/unload` is called or server restarts |

### Key dependency versions (frozen — see requirements notes below)

```
torch==2.2.2 (CPU build)
optimum==1.19.1
diffusers==0.27.2
transformers==4.40.2
onnxruntime-directml==1.19.0
huggingface_hub==0.21.4
numpy<2 (1.26.4)
setuptools<81
onnx==1.22.0
```

⚠️ **Run `pip freeze > requirements-tier5.txt` in the working venv and commit it.** This exact combination took many hours of trial and error to get compatible — don't let it drift.

---

## What we tried and why it didn't work (so nobody repeats this)

1. **SDXL Turbo, local PyTorch export** (`export=True`) — silently OOM-crashed
   (no traceback, Windows just killed the process). SDXL-XL fp32 needs
   ~7-8GB RAM to load before export even starts. Not viable on 8GB RAM.

2. **SDXL Turbo, pre-converted Olive/DirectML ONNX build**
   (`softwareweaver/Sdxl-Turbo-Olive-Onnx`) — downloaded fine, but:

   - Failed to even _load_ on DirectML: `Not enough memory resources`
     (UNet alone is 5.13GB fp32 — too big for 3.9GB shared VRAM).
   - Failed to fall back to CPU either: `NOT_IMPLEMENTED: GroupNorm(1)` —
     Olive-optimized builds use DirectML-only fused kernels, no real
     CPU path exists for them.
   - **Conclusion: any Olive-optimized ("-Olive-Onnx") model on
     HuggingFace is DirectML-only, no CPU fallback. Avoid for this
     hardware unless VRAM headroom is confirmed generous.**

3. **SD Turbo (non-XL), local export, fp16** (`torch_dtype=float16, variant="fp16"` kwargs) — `optimum==1.19.1`'s `from_pretrained`
   doesn't accept these kwargs in this version. Removed them → exported
   fp32 instead (this is the current working state, larger than ideal).

4. **SD Turbo, fp32 export, DirectML load** — pipeline _loads_
   successfully on DirectML, but generation itself fails mid-run:
   `Expand node ... Not enough memory resources`. fp32 SD-Turbo (UNet +
   VAE + text encoder + diffusion activation buffers for a 512x512
   image) exceeds the 3.9GB shared VRAM budget during actual inference,
   even though loading alone fit.

5. **Post-export fp16 conversion** (`onnxconverter-common`,
   `float16.convert_float_to_float16`) — introduced type mismatches
   (`Div` node type conflict, `Cast` output type conflict) in the VAE
   decoder / text encoder graphs. Root cause: `disable_shape_infer=True`
   skipped necessary type-consistency passes. **Not resolved** — would
   need `disable_shape_infer=False` (untested) or a different
   conversion tool (e.g. `onnxruntime.transformers.float16` helper, or
   re-exporting via `optimum-cli` with proper fp16 support in a newer
   `optimum` version — but upgrading `optimum` risks breaking the
   currently-working `torch 2.2.2` compatibility).

**Bottom line:** on this exact hardware (3.9GB shared VRAM, Iris Xe),
**CPU generation is the only path that has been proven to reliably
work end-to-end.** GPU is left as an opt-in experiment
(`image_try_gpu` setting) with automatic fallback to the known-working
CPU path — see `image_service.py`.

---

## API Endpoints (Tier 5)

```
POST /api/v1/image/generate   — generate an image (prompt, negative_prompt, steps 1-4, seed)
GET  /api/v1/image/file/{name} — fetch a generated image
GET  /api/v1/image/status      — pipeline load state, active provider, free RAM
POST /api/v1/image/unload      — free the pipeline from RAM (call before heavy chat use)
```

## Chat Integration

Saying things like _"generate an image of a red bicycle"_ or
_"ছবি বানাও একটা লাল বাইসাইকেলের"_ in the main AURA chat now triggers
image generation directly (deterministic intent, bypasses the LLM —
same pattern as search/system/save intents). The reply contains an
`[[IMAGE:url]]` marker, which the existing frontend `MessageBubble.jsx`
already knows how to render (same mechanism used for document page
previews) — no new frontend component was needed for this.

⚠️ Frontend chat request timeout was bumped from 120s → 300s
(`frontend/src/services/api.js`) since a cold-start CPU generation
(~117s) was uncomfortably close to the old 120s ceiling.

## RAM Safety

- Ollama's `aura-brain` model is force-unloaded (`keep_alive: 0`)
  immediately before every image generation, to avoid having the LLM
  and the diffusion pipeline in RAM simultaneously.
- If free RAM drops under 800MB when generation is requested, the
  service returns an error instead of attempting generation.
- The diffusion pipeline itself stays loaded in RAM after first use
  (for speed on repeat generations). Call `POST /api/v1/image/unload`
  before returning to heavy chat/agent use to free that RAM back up.
  This isn't automatic yet — worth adding as a scheduled/idle-timeout
  unload in a future pass.

## Known Limitations / Next Steps

- **Quality**: fp32 CPU generation at 512x512, 1 step. Prompt
  engineering (photorealistic keywords, detailed negative prompts) is
  currently the main quality lever — see conversation notes for
  examples. Raising `steps` to 2-4 improves detail at a roughly linear
  time cost.
- **GPU**: `image_try_gpu` config flag exists for future experimentation
  but defaults to `False`. If revisiting, the fp16 conversion issue
  (#5 above) is the actual blocker to solve, not DirectML itself.
- **Video generation** (other half of Tier 5): not started. Planned
  approach: free-tier cloud APIs with auto-fallback chain (no local
  GPU needed, per original Tier 5 architecture doc). Needs API
  key(s)/account(s) before implementation can start.
- **Auto-unload idle pipeline**: pipeline currently stays in RAM
  indefinitely after first generation until manually unloaded or
  server restart. A background idle-timeout unload (e.g. after 5 min
  of no generation requests) would make RAM management fully hands-off.
