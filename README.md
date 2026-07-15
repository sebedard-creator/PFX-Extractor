# 🎙️ PFX Extractor - Drive Bridge

> **Language note:** This README is written in English, but the codebase itself — all inline comments, variable/function names, print statements, and the Colab notebook's documentation — is written in French.

**PFX Extractor** is a hybrid (local + cloud GPU) toolchain for audio post-production professionals. It automatically extracts production sound effects (PFX) and ambiences from raw location-sound recordings using state-of-the-art AI source-separation models (BS-RoFormer & MDX-Net), combined with a dedicated sound-event detector that catches what those separation models miss — sighs, breaths, screams, and other non-lexical human vocalizations.

To avoid needing a powerful local machine, the app uses a "Drive Bridge" architecture: a lightweight local web interface syncs your files to Google Drive, Google Colab's GPU servers do the heavy processing, and the local interface then retrieves the finished result.

---

## ✨ Features

### Core source separation
* **Dual-model AI separation** — Runs both **BS-RoFormer** and **MDX23C** on every clip and blends their "Instrumental" (non-vocal) outputs with a configurable weighted mix (`RATIO_ROFORMER`, default 60% RoFormer / 40% MDX23C — RoFormer tends to produce cleaner splits with fewer artifacts for PFX work).
* **Configurable AI overlap** (`AI_OVERLAP`) — Controls how much adjacent inference segments overlap. Higher overlap smooths the separation mask over time, reducing audible "pumping" on busy or noisy material, at the cost of extra GPU time.

### Independent vocalization detection (YAMNet)
* **Sound-event detector, decoupled from the separation models** — MDX23C and RoFormer are trained on music (singing vs. instrumental) and often fail to recognize non-lexical human sounds — sighs, gasps, screams, laughs — as "vocal" at all, so they leak straight through into the PFX track. To catch these, the pipeline runs **YAMNet**, a general-purpose AudioSet sound-event classifier, on the untouched merged audio *before* any denoising or AI separation — the point where a sigh still has its full acoustic signature.
* **Self-auditing class selection** — Rather than a hardcoded class list, the notebook matches keyword patterns (e.g. "sigh", "scream", "gasp", "footstep", "rustle") against YAMNet's real 521-class taxonomy at load time, and **prints the exact matched classes** to the log for review before any file is processed.
* **Two independent outputs from one detection pass:**
  * **Anti-vocalization ducking** (`DUCK_DEPTH_SOUPIRS`) — Attenuates the final PFX mix proportionally to detected vocalization confidence (continuous, not a hard gate).
  * **Bodytalk protection** (`PROTECTION_BODYTALK`) — Wherever the detector is confident it's hearing footsteps, cloth, or other body movement, the raw (pre-denoise) signal is restored instead of the denoised one, preventing legitimate production sound from being scrubbed away along with noise.

### Noise reduction
* **Adaptive pre-denoise** (`NIVEAU_DENOISE_POURCENTAGE`, `DENOISE_ADAPTATIF`) — A spectral noise-reduction pass runs before AI separation. `DENOISE_ADAPTATIF` toggles between a stationary noise profile (steadier, better for consistent room tone) and an adaptive one (better suited to noisy, variable exterior scenes — traffic, wind — where a stationary profile can cause audible "pumping").

### Time alignment & clip management
* **Automatic Lav/Boom time-alignment** — Cross-correlates paired microphone recordings (e.g. `Lav-01.wav` / `Boom-01.wav`) of the same take and time-aligns them to sub-sample accuracy before processing.
* **Alignment confidence safeguard** — Computes a normalized correlation confidence score for every proposed alignment. If two clips grouped together turn out to have no real acoustic relationship (e.g. an ambiguous filename accidentally groups two unrelated takes), the alignment is skipped and the clip is copied through untouched rather than being corrupted by a meaningless time-shift.
* **Snowball Merge** — Automatically concatenates short clips from the same take/family until they reach the minimum duration required for stable AI inference (5s), so brief clips still get a clean separation pass instead of introducing artifacts.

### Timecode & delivery
* **BWF Timecode preservation** — Reads the original Broadcast Wave `time_reference` metadata and re-injects it into the final processed file via `ffmpeg`, so the output stays perfectly aligned on your editing timeline.
* **Smart Cache & Fallback** — Silent/empty clips are automatically skipped rather than crashing the batch; if the AI separator fails on a given file, the pipeline falls back to passing the clip through unprocessed rather than losing it.
* **Compute cost tracking** — Prints an estimated Compute Units cost at the end of each Colab session.

### Local interface (Drive Bridge)
* **Lightweight Gradio UI** (`app_local.py`) — Drop raw `.wav` files, upload to Drive, open the Colab notebook, and download the finished results as a ready-to-use ZIP, all from a local browser tab.
* **One-click cache clearing** — Wipes both local working files and the corresponding Drive folders, with an explicit confirmation step before anything is deleted.
* **Configurable Colab link** — Point the "Open Google Colab" button at a new notebook version at any time via the "⚙️ Advanced Settings" panel, without touching code.

---

## 🏗️ Architecture

1. **Local interface (Gradio)** — `app_local.py` runs on your machine. You drop raw files in; `drive_auth.py` handles Google Drive authentication and syncs them up.
2. **Cloud backend (Colab)** — `Colab_Backend_PFX_V2.1_YAMNet.ipynb` runs on Google's GPU servers. It downloads the raw files, aligns/merges/denoises them, runs the dual AI separation + YAMNet detection pipeline, and uploads the finished PFX tracks back to Drive.
3. **Retrieval** — The local interface downloads the processed files from Drive and delivers a clean `.zip`.

---

## 🚀 Installation & Requirements

### 1. Requirements
* Python 3.10+
* A Google account with access to Google Drive and Google Colaboratory.

### 2. Local dependencies
Clone this repository, then install the local interface's dependencies:
```bash
pip install -r requirements.txt
```

### 3. Google API credentials (OAuth)
For the local app to write to your Google Drive:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create OAuth 2.0 credentials (type "Desktop app").
3. Download the file, rename it `credentials.json`, and place it at the root of this project.

---

## 📖 How to Use

1. **Start the local interface** — Double-click `start.bat` (or run `python app_local.py`). The interface opens in your browser.
2. **Send your files** — Drop your `.wav` tracks in the interface and click "Upload vers Google Drive".
3. **Run the AI processing** — Click "Ouvrir Google Colab". In Colab, adjust the parameters in the control panel cell if needed, then run every cell in `Colab_Backend_PFX_V2.1_YAMNet.ipynb` in order.
4. **Retrieve the result** — Once Colab finishes, go back to the local interface and click "Télécharger les fichiers traités en ZIP".
5. **Clean up** — Use the red "Effacer la cache" button to clear your Drive and local working folders and prepare the next session.

---

## 🎛️ Colab Control Panel Reference

All processing parameters live in a single control-panel cell at the top of the notebook — nothing else needs to be edited by hand.

| Parameter | Default | What it does |
|---|---|---|
| `NIVEAU_DENOISE_POURCENTAGE` | 58% | Strength of the pre-denoise pass applied before AI separation. |
| `DENOISE_ADAPTATIF` | On | Adaptive (non-stationary) vs. stationary noise profile — adaptive is more robust on noisy/variable exterior scenes. |
| `RATIO_ROFORMER` | 0.60 | Blend weight between RoFormer and MDX23C outputs. |
| `AI_OVERLAP` | 12 | Overlap between AI inference segments — higher values smooth the separation mask over time (less pumping, more GPU time). |
| `DUCK_DEPTH_SOUPIRS` | 75% | Strength of the YAMNet-driven anti-vocalization duck (sighs, screams, singing, etc.). |
| `PROTECTION_BODYTALK` | 70% | Strength of the YAMNet-driven bodytalk protection (footsteps, cloth) during denoise. |

---

## 🧠 What's New

**V2.1**
* Added a normalized-confidence safeguard to the auto-alignment step, preventing unrelated clips from being corrupted by a forced (meaningless) time-shift.
* Removed the A/B comparison-file generation feature — each clip now produces a single `_PFX_Ready.wav` output.

**V2.0**
* Replaced the V1.x sidechain (which relied on the AI separator's own discarded "Vocals" stem — a dead end, since the models detect essentially no vocal content on non-lexical sounds like sighs) with an independent YAMNet-based sound-event detector.
* Added bodytalk protection during denoise, driven by the same detector.
* Added `DENOISE_ADAPTATIF` and increased default `AI_OVERLAP` to reduce pumping artifacts on noisy exterior scenes.
* Retired the local `dsp_local.py` DSP module — all processing is now centralized in the Colab notebook.

---
*PFX Extractor v2.1 - 2026*
*Designed by Sébastien Bédard*
