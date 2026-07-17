# 🎙️ PFX Extractor - Drive Bridge

> **Language note:** This README is written in English, but the codebase itself — all inline comments, variable/function names, print statements, and the Colab notebook's documentation — is written in French.

**PFX Extractor** is a hybrid (local + cloud GPU) toolchain for audio post-production professionals. It creates a production-FX stem from raw location recordings: synchronized physical sounds such as footsteps, clothing, props, manipulations, and impacts are preserved, while human sounds, roomtone, exterior traffic, weather, music, and other ambience are reduced.

To avoid needing a powerful local machine, the app uses a "Drive Bridge" architecture: a lightweight local web interface syncs your files to Google Drive, Google Colab's GPU servers do the heavy processing, and the local interface then retrieves the finished result.

---

## ✨ Features

### Core source separation
* **Dual-model AI separation** — Runs both **BS-RoFormer** and **MDX23C** on every clip and blends their "Instrumental" (non-vocal) outputs with a configurable weighted mix (`RATIO_ROFORMER`, default 60% RoFormer / 40% MDX23C — RoFormer tends to produce cleaner splits with fewer artifacts for PFX work).
* **Configurable AI overlap** (`AI_OVERLAP`) — Controls how much adjacent inference segments overlap. Higher overlap smooths the separation mask over time, reducing audible "pumping" on busy or noisy material, at the cost of extra GPU time.

### Production-FX event routing (YAMNet)
* **Sound-event detector, decoupled from the separation models** — The pipeline runs **YAMNet** on the untouched merged audio before denoising or source separation. It catches non-lexical human sounds and also distinguishes production effects from ambience and other content that does not belong in the PFX stem.
* **Exact, exhaustive class partition** — All **521 YAMNet/AudioSet indices** are assigned explicitly to one of six non-overlapping roles. The notebook validates the expected group counts and aborts if the model taxonomy changes. Substring matching (`hum`, `run`, etc.) is no longer used.
* **Separate thresholded masks** — Raw class maxima no longer drive gain directly. Human, ambience, outside-PFX, and PFX-protection evidence use independent soft thresholds and attack/release envelopes:
  * **Human removal** (`DUCK_DEPTH_HUMAIN`) — voices, vocalizations, breathing, physiological sounds, and applause.
  * **Ambience removal** (`DUCK_DEPTH_AMBIANCE`) — nature/weather, roadway traffic, roomtone-like noise, static, and hum.
  * **Outside-PFX removal** (`DUCK_DEPTH_HORS_PFX`) — music, TV/radio content, vehicles, sirens, and low-frequency/vibration classes.
  * **PFX protection** (`PROTECTION_PFX`) — footsteps, cloth, props, manipulations, impacts, tools, and other production effects reduce denoise and mask depth locally; restoration of raw audio is capped below 100%.
  * **Contextual classes** — isolated foreground animals and short electronic tones are preserved, while persistent/diffuse occurrences are routed to removal using temporal persistence.
  * **Context-only classes** — `Inside`, `Outside`, `Reverberation`, `Echo`, `Field recording`, and `Silence` never drive a local gain curve.
* **Memory-bounded processing** — Frame-level YAMNet masks are cached and interpolated in 30-second blocks, avoiding several full-resolution mask arrays on long recordings.

### Noise reduction
* **Adaptive pre-denoise** (`NIVEAU_DENOISE_POURCENTAGE`, `DENOISE_ADAPTATIF`) — A spectral noise-reduction pass runs before AI separation. `DENOISE_ADAPTATIF` toggles between a stationary noise profile (steadier, better for consistent room tone) and an adaptive one (better suited to noisy, variable exterior scenes — traffic, wind — where a stationary profile can cause audible "pumping").

### Time alignment & clip management
* **Automatic Lav/Boom time-alignment** — Cross-correlates paired microphone recordings (e.g. `Lav-01.wav` / `Boom-01.wav`) of the same take and time-aligns them to integer-sample accuracy before processing.
* **Alignment confidence safeguard** — Computes a normalized correlation confidence score for every proposed alignment. If two clips grouped together turn out to have no real acoustic relationship (e.g. an ambiguous filename accidentally groups two unrelated takes), the alignment is skipped and the clip is copied through untouched rather than being corrupted by a meaningless time-shift.
* **Snowball Merge** — Temporarily concatenates short clips from the same take/family until they reach the minimum duration required for stable AI inference (5s), while recording every source boundary. After processing, the merged result is split back into one output per original clip, preserving each clip's name, duration, and BWF timecode.

### Timecode & delivery
* **BWF Timecode preservation** — Reads the original Broadcast Wave `time_reference` metadata and re-injects it into the final processed file via `ffmpeg`, so the output stays perfectly aligned on your editing timeline.
* **Template-driven Pro Tools delivery** — The local interface can turn the WAV files currently stored in `work/processed` into a self-contained Pro Tools delivery: one `.ptx` session plus an `Audio Files` folder, wrapped in a downloadable ZIP. Placement uses each file's BWF timestamp, so it is sample-accurate rather than clip-relative.
* **Deterministic track routing** — Processed filenames must follow `<family>-Gain_<number>_PFX_Ready.wav`. Files are sorted alphabetically; the first family is routed to `PFX 01`, the second to `PFX 02`, and a third family is rejected explicitly. Same-track overlaps are preserved, including one-sample boundary overlaps.
* **Smart Cache & Fallback** — Silent/empty clips are automatically skipped rather than crashing the batch; if the AI separator fails on a given file, the pipeline falls back to passing the clip through unprocessed rather than losing it.
* **Compute cost tracking** — Prints an estimated Compute Units cost at the end of each Colab session.

### Local interface (Drive Bridge)
* **Lightweight Gradio UI** (`app_local.py`) — Drop raw `.wav` files, upload to Drive, open the Colab notebook, download the finished WAV files, and create the Pro Tools delivery, all from a local browser tab.
* **One-click cache clearing** — Wipes both local working files and the corresponding Drive folders, with an explicit confirmation step before anything is deleted.
* **Configurable Colab link** — Point the "Open Google Colab" button at a new notebook version at any time via the "⚙️ Advanced Settings" panel, without touching code.

---

## 🏗️ Architecture

1. **Local interface (Gradio)** — `app_local.py` runs on your machine. You drop raw files in; `drive_auth.py` handles Google Drive authentication and syncs them up.
2. **Cloud backend (Colab)** — `Colab_Backend_PFX_V3_0.ipynb` runs on Google's GPU servers. It downloads the raw files, aligns/merges/denoises them, runs the dual AI separation + YAMNet multi-mask pipeline, and uploads the finished PFX tracks back to Drive.
3. **Retrieval and Pro Tools assembly** — One frontend action downloads the processed WAV files from Drive without creating an intermediate WAV archive. `protools_export.py` then applies PFX Extractor's filename sorting and track-routing policy and calls the generic `pt_api` 1.3.8+ template builder. The browser receives a single ZIP containing the `.ptx` session and its `Audio Files` folder. A local `template.ptx` at the repository root is used by default; an alternate compatible template can be selected in Advanced Settings.

---

## 🚀 Installation & Requirements

### 1. Requirements
* Python 3.10+
* Git, used by `pip` to install the pinned `pt_api` dependency from GitHub.
* A Google account with access to Google Drive and Google Colaboratory.

### 2. Local dependencies
Clone this repository, then install the local interface's dependencies:
```bash
pip install -r requirements.txt
```

`requirements.txt` installs the validated `pt_api` release directly from the immutable Git tag `v1.3.8`. PFX Extractor resolves the runtime in this order: `PT_API_PATH`, the installed `pt_api` module, then a sibling repository named `pt_api` next to this repository. The final option remains a development fallback; normal installations use the pinned package.

After pulling a revision that changes `requirements.txt` into an existing virtual environment, update it once with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Place a compatible native Pro Tools template at the repository root as `template.ptx`. This proprietary file is intentionally excluded by `.gitignore` and must be provisioned separately on every installation that needs PTX export. The validated local template is an empty mono 48 kHz / 23.976 fps session with uniquely named `PFX 01` and `PFX 02` tracks and the imported-media prototype required by `pt_api`.

### 3. Google API credentials (OAuth)
For the local app to write to your Google Drive:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create OAuth 2.0 credentials (type "Desktop app").
3. Download the file, rename it `credentials.json`, and place it at the root of this project.

---

## 📖 How to Use

1. **Start the local interface** — Double-click `start.bat` (or run `python app_local.py`). The interface opens in your browser.
2. **Send your files** — Drop your `.wav` tracks in the interface and click "Upload vers Google Drive".
3. **Run the AI processing** — Click "Ouvrir Google Colab". In Colab, adjust the parameters in the control panel cell if needed, then run every cell in `Colab_Backend_PFX_V3_0.ipynb` in order.
4. **Retrieve the Pro Tools result** — Once Colab finishes, go back to the local interface and click "Télécharger les fichiers traités en ZIP". This single action downloads the WAV files from Drive, creates the Pro Tools session, and downloads the final ZIP. The default template routes the first filename family to `PFX 01` and a second family to `PFX 02`; Advanced Settings can override the template or session name. Unpack the returned ZIP before opening its `.ptx` file.
5. **Clean up** — Use the red "Effacer la cache" button to clear your Drive and local working folders, generated Pro Tools deliveries, and prepare the next session.

The validated local template and builder currently target mono, 48 kHz, 23.976 fps sessions. Input WAV files must be mono 48 kHz, 32-bit float WAVE_EXTENSIBLE files with valid BWF metadata and must respect the format limits documented by `pt_api`. Export is transactional: an error does not publish an incomplete delivery.

---

## 🎛️ Colab Control Panel Reference

All processing parameters live in a single control-panel cell at the top of the notebook — nothing else needs to be edited by hand.

| Parameter | Default | What it does |
|---|---|---|
| `NIVEAU_DENOISE_POURCENTAGE` | 58% | Strength of the pre-denoise pass applied before AI separation. |
| `DENOISE_ADAPTATIF` | On | Adaptive (non-stationary) vs. stationary noise profile — adaptive is more robust on noisy/variable exterior scenes. |
| `RATIO_ROFORMER` | 0.60 | Blend weight between RoFormer and MDX23C outputs. |
| `AI_OVERLAP` | 12 | Overlap between AI inference segments — higher values smooth the separation mask over time (less pumping, more GPU time). |
| `DUCK_DEPTH_HUMAIN` | 75% | Strength of human-sound removal (speech, vocalizations, breathing, physiological sounds, applause). |
| `DUCK_DEPTH_AMBIANCE` | 70% | Strength of ambience removal (nature/weather, traffic, roomtone-like noise, static, hum). |
| `DUCK_DEPTH_HORS_PFX` | 85% | Strength of non-PFX content removal (music, TV/radio, vehicles, sirens, low-frequency/vibration classes). |
| `PROTECTION_PFX` | 70% | Local protection of footsteps, cloth, props, manipulations, impacts, and tools; capped at 90%. |

### V3.0 default-profile rationale

The defaults are deliberately strong enough to create a useful PFX stem without turning the masks into hard gates. At full mask confidence and without overlapping PFX protection, they yield approximately **−12.0 dB** for human content, **−10.5 dB** for ambience, and **−16.5 dB** for outside-PFX content. With a full PFX-protection event, the corresponding reductions relax to roughly **−7.3 dB**, **−2.9 dB**, and **−6.4 dB**, preserving physical transients.

Recommended starting ranges are 70–80% human, 60–75% ambience, 80–90% outside-PFX, and 60–75% PFX protection. `NIVEAU_DENOISE_POURCENTAGE=58`, adaptive denoise, `RATIO_ROFORMER=0.60`, and `AI_OVERLAP=12` remain the balanced defaults; final tuning should be based on a representative production-sound batch rather than a single clip.

---

## 🧠 What's New

**V3.0**
* Replaced YAMNet keyword matching and raw-max ducking with an exact 521-class partition, separate thresholded masks, contextual animal/tone handling, and block-based PFX protection.
* Added independent controls for human, ambience, and outside-PFX removal, plus capped PFX restoration.
* Hardened separator parameter validation, lag conventions, sample-rate handling, and Snowball re-splitting/timecode delivery.
* Added self-contained Pro Tools session delivery from processed BWF files through the generic `pt_api` 1.3.8+ template builder.
* Validated the complete Pro Tools path on a real 62-file batch: generation, native opening, playback, Save As, closing, and reopening all succeeded without warning.

**V2.1**
* Added a normalized-confidence safeguard to the auto-alignment step, preventing unrelated clips from being corrupted by a forced (meaningless) time-shift.
* Removed the A/B comparison-file generation feature — each clip now produces a single `_PFX_Ready.wav` output.

**V2.0**
* Replaced the V1.x sidechain (which relied on the AI separator's own discarded "Vocals" stem — a dead end, since the models detect essentially no vocal content on non-lexical sounds like sighs) with an independent YAMNet-based sound-event detector.
* Added bodytalk protection during denoise, driven by the same detector.
* Added `DENOISE_ADAPTATIF` and increased default `AI_OVERLAP` to reduce pumping artifacts on noisy exterior scenes.
* Retired the local `dsp_local.py` DSP module — all processing is now centralized in the Colab notebook.

---
*PFX Extractor v3.0 - 2026*
*Designed by Sébastien Bédard*
