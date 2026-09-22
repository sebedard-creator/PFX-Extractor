# PFX Extractor

**PFX Extractor** turns location-recording WAV files into a Production FX stem: it aims to retain usable on-set physical sound—clothing movement, footsteps, props, handling and impacts—while reducing speech, other human sounds, room tone, exterior traffic, weather, music, television/radio, vehicles and other non-PFX material.

It is a Windows-first workflow for post-production:

```text
Raw WAV files → local Drive Bridge → Google Drive → Google Colab GPU
→ processed BWF WAV files → Pro Tools session (.ptx + Audio Files ZIP)
```

The desktop interface is intentionally simple. It uploads files, opens the configured Colab notebook, retrieves processed files, and builds the Pro Tools delivery. The audio processing itself runs in Colab; no GPU is required locally.

> The UI, code comments and Colab notebooks are in French. This README is in English for broader technical reference.

## Current backend choices

| Notebook | Status | Use it when |
| --- | --- | --- |
| `Colab_Backend_PFX_V3_1_2.ipynb` | Stable baseline | You need the most established workflow. |
| `Colab_Backend_PFX_V3_2_0.ipynb` | Listening-tested experiment | You want stronger treatment of sighs, whispers and breathing. |
| `Colab_Backend_PFX_V3_3_0.ipynb` | Current experiment | You also want more mouth-noise reduction and a guarded bodytalk lift. Validate it on representative material before standardizing it. |

The **Open Google Colab** button opens the URL saved in `colab_link.txt`. Use **Advanced Settings** in the local interface to change it to the notebook you intend to run.

V3.3.0 adds two independent controls:

- `DUCK_DEPTH_BOUCHE` — contextual attenuation for mouth noise. Its default is 95%.
- `GAIN_BODYTALK_DB` — up to +2 dB on YAMNet proxies for clothing movement and rubbing, automatically blocked by human and ambience evidence.

See [the V3.3.0 trial guide](ESSAI_V3_3_0.md) before relying on those settings in production. Its mouth and bodytalk detection is temporal, not clip-wide, but remains classification-based: some wanted effects may be reduced and some unwanted sounds may remain.

## What it does

- **Dual source separation:** blends BS-RoFormer and MDX23C instrumental stems. The default blend favors RoFormer (60%) to reduce vocal residue while limiting artifacts.
- **YAMNet event routing:** analyses the untouched merged audio before denoise and separation. All 521 AudioSet classes are explicitly assigned to non-overlapping PFX, human, ambience, outside-PFX, contextual or excluded roles.
- **Time-based masks:** applies soft thresholds and attack/release envelopes per event type—not a single decision for a whole clip. Masks are cached at YAMNet resolution and interpolated in blocks for long recordings.
- **PFX protection:** reduces the effect of denoise and removal masks around physical on-set events. It is intentionally capped: protection never restores the full raw signal.
- **Boom/Lav alignment:** when both are supplied, filenames containing `BOOM` and `LAV` are naturally sorted and paired by position. Their internal sequence numbers do not need to match; the two lists must contain the same number of files.
- **Short-clip handling:** clips are temporarily merged by family for stable inference, then split back to their original durations, names and BWF timecode.
- **Pro Tools delivery:** downloads the processed files and builds one self-contained ZIP containing a `.ptx` session and its `Audio Files` folder. Placement comes from each output file's BWF timestamp.

## Requirements

- Windows 10 or 11, Python 3.10 or newer, and Git.
- A Google account with Google Drive and Google Colab access.
- A Google Cloud OAuth **Desktop app** credential for the local Drive Bridge.
- Internet access for Drive, Colab, TensorFlow Hub and model downloads.
- For Pro Tools delivery: a compatible local `template.ptx` file. It is proprietary and is deliberately not included in this repository.

The tested Pro Tools workflow is **mono, 48 kHz, 23.976 fps**, with two uniquely named tracks: `PFX 01` and `PFX 02`.

## Installation

1. Clone the repository and open its folder.

   ```powershell
   git clone https://github.com/sebedard-creator/PFX-Extractor.git
   cd PFX-Extractor
   ```

2. Put your Google OAuth Desktop-app client file at the project root as `credentials.json`.

3. If you need Pro Tools export, put the separately supplied native session template at the root as `template.ptx`.

4. Run `start.bat`. On the first run it creates `.venv` and installs [requirements.txt](requirements.txt).

5. Open [http://127.0.0.1:7862](http://127.0.0.1:7862) in a browser if it does not open automatically. The first action requiring Drive opens the Google OAuth consent flow and creates a local `token.json`.

For a pre-existing virtual environment, install updated dependencies explicitly after pulling changes:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`PFXExtractor_start_hidden.vbs` starts the already-installed interface in the background. Its logs are written below `work\`.

### Google OAuth setup

Create OAuth 2.0 credentials of type **Desktop app** in the [Google Cloud Console](https://console.cloud.google.com/), download the JSON file and rename it `credentials.json`.

The Drive Bridge requests full Google Drive access because Colab writes the processed files outside the local application's own upload operation. Treat `credentials.json` and `token.json` as private credentials. Both are excluded from Git.

## Standard workflow

1. Start the local interface and drop the raw `.wav` files.
2. Click **Upload vers Google Drive**. Files are copied locally, then uploaded to `PFX_Extractor/1_Bruts_vers_Colab` on Drive.
3. Click **Ouvrir Google Colab** and run the selected notebook's cells in order. Do not run two notebook versions simultaneously against the same Drive folders.
4. After Colab completes, click **Télécharger les fichiers traités en ZIP**. The interface downloads Drive outputs, builds the Pro Tools session, and downloads a ZIP with this layout:

   ```text
   <session name>/
   ├── <session name>.ptx
   └── Audio Files/
       └── *.wav
   ```

5. Extract the ZIP before opening the `.ptx` file in Pro Tools.
6. After confirming the delivery, use **Effacer la cache** to remove temporary local files, generated deliveries and the two Drive working folders. This action asks for confirmation.

### Input and output conventions

- The intended production workflow uses **mono 48 kHz BWF WAV** files. Preserve BWF timestamps in source material whenever timeline placement matters.
- If a batch contains both microphone families, use `BOOM` and `LAV` somewhere in the filenames. The backend accepts a single family; when both exist their counts must match.
- The backend creates processed names in the form `<family>-Gain_<number>_PFX_Ready.wav`.
- For the Pro Tools export, files are sorted alphabetically. The first discovered family maps to `PFX 01`; the second maps to `PFX 02`. A third family is rejected rather than silently losing material.
- BWF timestamp overlaps on a track are intentionally retained. They are not mixed or dropped by the export builder.

## Colab controls

The notebook's first control cell is the supported place to tune processing. Start with the defaults and adjust only after listening to a representative batch—not a single clip.

| Control | Default | Purpose |
| --- | ---: | --- |
| `NIVEAU_DENOISE_POURCENTAGE` | 58% | Strength of the adaptive pre-denoise pass. |
| `DENOISE_ADAPTATIF` | On | Uses a changing noise profile; usually better for exterior and variable noise. |
| `RATIO_ROFORMER` | 0.60 | RoFormer proportion in the dual-model blend. |
| `AI_OVERLAP` | 12 | Higher overlap may reduce pumping, at a GPU-time cost. |
| `DUCK_DEPTH_HUMAIN` | 75% | General human-sound attenuation. |
| `DUCK_DEPTH_SOUFFLES` | 95% | V3.2+/V3.3+ priority treatment for whispering, sighs and breathing. |
| `DUCK_DEPTH_BOUCHE` | 95% | V3.3 only: contextual mouth-noise attenuation. |
| `GAIN_BODYTALK_DB` | +2 dB | V3.3 only: guarded lift for bodytalk proxies; set to 0 dB to disable. |
| `DUCK_DEPTH_AMBIANCE` | 70% | Ambience, weather, traffic, room tone and hum attenuation. |
| `DUCK_DEPTH_HORS_PFX` | 85% | Music, TV/radio, vehicles, sirens and similar content attenuation. |
| `PROTECTION_PFX` | 70% | Local protection of PFX evidence during denoise and masking. |

V3.3.0 returns to V3.2.0 audio behavior when both `DUCK_DEPTH_BOUCHE` is set to 0% and `GAIN_BODYTALK_DB` to 0 dB.

## Pro Tools delivery

The local export uses [pt_api](https://github.com/sebedard-creator/pt_api), pinned in [requirements.txt](requirements.txt) to the validated `v1.3.8` tag.

A compatible `template.ptx` must be supplied locally. The validated template is an empty mono 48 kHz / 23.976 fps Pro Tools session with `PFX 01` and `PFX 02` tracks plus the media prototype required by `pt_api`. The template is ignored by Git because it is proprietary.

Exports are transactional: if building the session fails, no incomplete ZIP is published. The already-downloaded WAV files remain in `work/processed` for diagnosis. Existing delivery archives are not overwritten.

The complete PTX workflow was validated on a real 62-file BWF batch: media hashes, timestamps, durations, placements and ZIP integrity were verified; the session then opened, played, saved, closed and reopened in Pro Tools without warning.

## Troubleshooting

| Situation | What to check |
| --- | --- |
| Drive authentication fails | Confirm that `credentials.json` is at the project root. Delete `token.json` only if you intentionally need to authorize again. |
| The interface starts but is not visible | Browse to [http://127.0.0.1:7862](http://127.0.0.1:7862). Review `work/app.log` and `work/server.log` if you used the hidden launcher. |
| Colab fails before the batch begins | Re-run its model preflight cell and inspect the reported missing resource. V3.1.2+ performs preflight before it purges temporary audio work. |
| No processed files are found | Confirm that the Colab run completed and that `PFX_Extractor/2_Environnements_IA` in the same Google Drive account contains the outputs. |
| PTX export is rejected | Verify the local `template.ptx`, mono 48 kHz/23.976 compatibility, BWF metadata and the processed filename convention. |
| Two microphone lists refuse to pair | Check that both family tokens are present and that the number of `BOOM` and `LAV` files is identical. |

## Project layout

| Path | Role |
| --- | --- |
| `app_local.py` | Local Gradio Drive Bridge. |
| `drive_auth.py` | OAuth authentication, Drive transfers and cache cleanup. |
| `protools_export.py` | PFX filename routing and transactional PTX delivery orchestration. |
| `Colab_Backend_PFX_V*.ipynb` | GPU processing backends. |
| `ESSAI_V3_2_0.md`, `ESSAI_V3_3_0.md` | Trial-specific controls, risks and listening protocol. |
| `architecture.md` | Detailed technical architecture and delivery contract. |
| `changelog.md` | Historical changes. |
| `work/` | Local runtime cache, logs, downloaded WAV files and generated deliveries. Ignored by Git. |
| `template.ptx` | Local proprietary Pro Tools template. Ignored by Git. |

## Limitations

PFX Extractor is an assistive restoration workflow, not a perfect source-isolation system.

- A detected human sound can overlap desired clothing or prop detail; stronger removal can reduce both.
- A wanted effect can be misclassified, and an unwanted sound can remain undetected.
- V3.3.0’s bodytalk control raises detected portions of the already processed mix; it cannot restore detail removed earlier in source separation.
- Pro Tools delivery currently supports a maximum of two filename families/tracks.
- The Colab backend, GPU availability, third-party model hosting and Google services are external dependencies. Retain your original recordings and evaluate a trial batch before processing a whole production.

## Documentation

- [Architecture](architecture.md)
- [Changelog](changelog.md)
- [V3.2.0 trial notes](ESSAI_V3_2_0.md)
- [V3.3.0 trial notes](ESSAI_V3_3_0.md)
- [pt_api](https://github.com/sebedard-creator/pt_api)

## License and attribution

Copyright © 2026 sebedard-creator.

This project is licensed under the [Attribution Assurance License](LICENSE). Use, modification and redistribution are permitted under its conditions. A redistributed executable program—or a program dependent on it—must visibly show this attribution at launch:

> PFX Extractor by sebedard-creator — https://github.com/sebedard-creator/PFX-Extractor

The attribution requirement does not grant permission to imply endorsement by sebedard-creator.

---

Designed by Sébastien Bédard.
