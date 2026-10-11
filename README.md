# PFX Extractor

**PFX Extractor** turns location-recording WAV files into a Production FX stem: it aims to retain usable on-set physical sound—clothing movement, footsteps, props, handling and impacts—while reducing speech, other human sounds, room tone, exterior traffic, weather, music, television/radio, vehicles and other non-PFX material.

It is a Windows-first workflow for post-production:

```text
Raw WAV files → local Drive Bridge → Google Drive → Google Colab GPU
→ processed BWF WAV files → Pro Tools session (.ptx + Audio Files ZIP)
```

The desktop interface is intentionally simple. It uploads files, opens the configured Colab notebook, retrieves processed files, and builds the Pro Tools delivery. The audio processing itself runs in Colab; no GPU is required locally.

> The UI, code comments and Colab notebooks are in French. This README is in English for broader technical reference.

## Current version

### Test V4: cumulative human attenuation with Bandit

[Colab_Backend_PFX_Vtest_V4.ipynb](Colab_Backend_PFX_Vtest_V4.ipynb) is a new copy of Test V3 for a listening comparison. Bandit, independent scenes, adaptive pre-denoise **40%**, detector-only gain **+18 dB**, and maximum bodytalk **+4 dB** are retained. Final human attenuation follows the V3.5.2 sequence: YAMNet masks from the original recording first attenuate the Bandit SFX; residual analysis then observes that already attenuated audio and applies a second reduction. The two gains multiply. At maximum detections, 95% followed by 90% gives about **−46 dB**, versus −26 dB with Test V3's single maximum reduction. Actual attenuation depends on detection; this is not a guarantee of better removal. Simultaneous Foley can be reduced more strongly.

Bodytalk is applied once after both reductions, with the same local peak margin and human/impact vetoes as Test V3. Choose Test V4 in Colab and use the usual ZIP/PTX button when the run finishes. V3.5.2, Test V3 and Test V4 share protocol 2 generation delivery; no manual Drive changes are needed. Earlier results and notebooks are preserved. Tests use synthetic audio and mocked model scores to check cumulative attenuation, detector order, temporal masks, bodytalk, failures and real FFmpeg BWF export. Listening validation in Colab remains necessary.

### V3.5.2: UMID fix for the MDX23C / BS-RoFormer backend

[Colab_Backend_PFX_V3_5_2.ipynb](Colab_Backend_PFX_V3_5_2.ipynb) preserves the **V3.5.1 audio processing chain**, including +3.5 dB maximum bodytalk. Default pre-denoise is now **40%**, matching Test V3 (previously 58%); other audio settings are unchanged. It backports fresh, directly written BWF UMIDs with audio-integrity and uniqueness checks. FFmpeg errors stop the export. It uses the same verified generation-delivery protocol as Test V3, without adopting its Bandit processing. V3.5.1 remains unchanged.

**Switching between V3.5.2 and Test V3 is automatic:** choose the notebook, run it, then use the usual ZIP/PTX button. Nothing to rename or delete on Drive. Each run creates a separate `run_...` folder and updates the common delivery pointer; earlier results are retained. Incomplete or failed runs cannot be downloaded as a finished delivery. Do not run notebooks concurrently. V3.5.2 retains V3.5.1's alignment/Snowball behavior and limitations; detected duration/timecode changes stop publication instead of altering the audio. Use a fresh Pro Tools session for comparison. This interoperability applies to these updated notebooks, not unmodified older versions.

### Test V3: independent scenes and verified deliveries

**October 6 UMID fix — reload the updated Test V3 notebook and restart the local frontend.** Revision `2026-10-06-test-v3-umid` writes fresh UUID-backed basic UMIDs directly into newly rendered BWF headers, after FFmpeg, without passing identities through FFmpeg metadata conversion. Audio samples and timecodes are unchanged. Protocol 2 records source/output identities and rejects duplicate output IDs or IDs reused from the sources. The frontend checks actual file identities before accepting a download, before calling the unmodified `pt_api`, and on the resulting Audio Files before ZIP creation. Protocol 1/legacy deliveries also receive the actual-file duplicate check; old defective lots are refused, not silently repaired. V3.5.2 also includes the UMID export fix; V3.5.1 and earlier variants do not.

The production incident was traced to 63 output WAVs sharing one UMID; modeling the resulting length clamp reproduces the observed `00:26:09:16` exactly at 23.976 fps. Regression tests use synthetic UMIDs with high unsigned 64-bit words to reproduce the collision. For manual confirmation, import the new run into a **fresh Pro Tools session**, avoiding cached associations from defective media. Existing audio files/ZIPs are not repaired or overwritten by this code change. Audio processing settings remain unchanged (40% pre-denoise, +4 dB maximum bodytalk).

[Colab_Backend_PFX_Vtest_V3.ipynb](Colab_Backend_PFX_Vtest_V3.ipynb) remains the comparison reference with non-cumulative attenuation. **Restart the updated local frontend before downloading its results.** Open the notebook in a fresh Colab T4 runtime, process the same source WAVs, then use the usual **Télécharger les fichiers traités en ZIP** button. There is no separate manual ZIP workflow.

- Adaptive pre-denoising defaults to **40%**, following the user's listening comparison. Each WAV is processed independently: no BOOM/LAV waveform alignment, no cross-scene concatenation, no post-separation scene recutting.
- Raw YAMNet masks protect pre-denoising only. Final masks and amplified residual detection both analyze the unattenuated Bandit SFX; attenuation depths combine by maximum, not multiplication. Simultaneous Foley can still be attenuated, and voice removal needs listening validation.
- Maximum bodytalk gain remains **+4 dB**, with local peak headroom and a detected-footstep/impact veto. This is guarded time-varying gain, not an isolated clothing stem; undetected simultaneous sounds can still rise.
- Before model processing, inputs must have an unambiguous BOOM or LAV name, mono 48 kHz PCM/float audio, BWF timestamp/basic UMID and a supported exact length. Sequence numbers and scene prefixes need not match. If both microphone types are present, counts must agree, but no waveform pairing is performed. The current conservative PTX profile accepts 1,024–16,777,215 samples per file (about 21 ms–349.5 s); files outside it fail early rather than being padded/truncated. RF64 is unsupported. Test V3 maps BOOM/LAV roles to at most two PTX tracks regardless of scene prefixes.
- Outputs live under `2_Environnements_IA/run_<id>/`. The root `PFX_delivery.json` changes from running to complete only after verification of every WAV. The updated frontend checks the exact output set, SHA-256, lengths and timestamps, then checks the manifest again. It refuses incomplete/changed/corrupt lots and ignores stale root-level WAVs. Old local processed files are retained under `work/processed_previous_*/processed` until manually cleaned up.

The older notebooks remain unchanged. Their manifest-less downloads still work, with an explicit unverified-lot warning. **Do not run notebooks concurrently.** If Colab terminated abruptly, confirm that the old runtime is stopped before enabling `REMPLACER_RUN_INTERROMPU`; rerun the setup cells to obtain a fresh run ID. To return to an older notebook after Test V3, explicitly archive/remove the root V3 manifest first; otherwise the verified V3 generation remains selected. Generation folders are retained, use Drive storage, and are not automatically purged by the legacy cache cleaner.

Validation: **88 local tests pass**, including a real `pt_api` build/readback with the local template and synthetic audio, exact independent-scene geometry, single attenuation, local gain/vetoes, and incomplete/corrupt/changing delivery rejection. No Test V3 Colab/GPU listening validation or manual Pro Tools import validation has been performed yet. The reported nine-frame discrepancy after timeline import is **not confirmed fixed**. `pt_api` itself was not modified. Validation completed October 6: FFmpeg output headers are made compatible with the required float32 WAVE_EXTENSIBLE profile without changing audio data, duration or BWF metadata; a second normalization leaves the file byte-identical.

### Earlier comparison notebooks and production baseline

For a controlled pre-cleaning comparison, use [Colab_Backend_PFX_Vtest_sans_prenettoyage.ipynb](Colab_Backend_PFX_Vtest_sans_prenettoyage.ipynb). It bypasses spectral pre-denoising entirely: Bandit reads aligned/merged WAVs directly. All other processing and settings match the current Vtest (crying removal and +4 dB maximum bodytalk gain included). The existing Vtest and V3.5.1 notebooks are preserved. Use the usual ZIP/PTX workflow below and retain the first delivery before running the other variant. More background noise may remain; listening comparison is required. Local tests verify unchanged input samples to Bandit, unchanged finishing, and delivery/export contracts.

**V3.5.2** is the UMID-corrected production backend: [Colab_Backend_PFX_V3_5_2.ipynb](Colab_Backend_PFX_V3_5_2.ipynb). [V3.5.1](Colab_Backend_PFX_V3_5_1.ipynb) is retained for reference, without this fix. Earlier changes are recorded in [changelog.md](changelog.md).

A separate comparison notebook is available: [Colab_Backend_PFX_Vtest.ipynb](Colab_Backend_PFX_Vtest.ipynb). It replaces MDX23C/RoFormer with the **SFX output of official multilingual Bandit v2 trained on DnR v3**. The October 5 revision adds targeted crying/sobbing/whimpering/moaning removal (`DUCK_DEPTH_PLEURS=95`), on raw-event masks and residual detection, and raises maximum bodytalk gain to **+4 dB** (+0.5 dB), retaining human/ambience vetoes and peak-headroom protection; other settings are unchanged. Set the crying control to 0 to disable both targeted crying additions, while retaining general human removal. It can also attenuate simultaneous Foley. It is not the DnR-nonverbal research model or MVSEP's proprietary ensemble. V3.5.1 is unchanged; no frontend URL is switched automatically.

Vtest uses **exactly the usual workflow**: select the other notebook in Colab, process the same inputs, then use the frontend's **Télécharger les fichiers traités en ZIP** button for the Pro Tools delivery. Both notebooks write BWF WAVs to `PFX_Extractor/2_Environnements_IA`. **Download and retain the first delivery before running the second notebook**, which replaces same-named WAVs on Drive. Do not clear the frontend cache between runs, run the notebooks simultaneously, or download before processing succeeds. Diagnostics are saved outside the delivery folder, under `0_Model_Cache/Bandit_v2/manifests/`; Colab does not create a separate ZIP.

Audio is processed inside Colab without a separation API or upload to MVSEP. Only public code, dependencies and weights are downloaded from external hosts. Use a fresh T4 runtime. GPU performance and audible improvement must be checked on the comparison project; no improvement is promised.

Validation: local tests cover repeated delivery, BWF timecode/duration, targeted crying and exact source cuts even when a simulated separator output has an extra tail. The official checkpoint was also tested on an eight-second synthetic signal on CPU. The user reports a favorable Colab comparison, with residual crying and three allegedly overlong clips. Crying tuning still needs listening validation; the length discrepancy on long clips has not been reproduced. Input/output sample counts remain available in each run's manifest for diagnosis.

The **Open Google Colab** button opens the URL saved in `colab_link.txt`. Use **Advanced Settings** in the local interface to change it to the notebook you intend to run.

The backend combines priority respiratory treatment, contextual mouth-noise attenuation and a residual-human analysis of the cleaned mix. That analysis merges native-level scores with scores from locally amplified copies (up to +18 dB by default), then applies one residual removal mask. The amplification is reserved for detection.

V3.5.1 increases the maximum clothing-movement lift from +2 to **+3.5 dB**. Zipper, rubbing, crumpling and rustling trigger this control; footsteps and taps do not. Human/ambience guards and peak headroom may reduce the actual gain. All these controls are temporal. Human finishing remains necessary, as detection can miss unwanted sounds or attenuate wanted effects.

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
3. Click **Ouvrir Google Colab** and run the current notebook's cells in order. Do not run two processing sessions simultaneously against the same Drive folders.
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
| `NIVEAU_DENOISE_POURCENTAGE` | 40% | Strength of the adaptive pre-denoise pass. |
| `DENOISE_ADAPTATIF` | On | Uses a changing noise profile; usually better for exterior and variable noise. |
| `RATIO_ROFORMER` | 0.60 | RoFormer proportion in the dual-model blend. |
| `AI_OVERLAP` | 12 | Higher overlap may reduce pumping, at a GPU-time cost. |
| `DUCK_DEPTH_HUMAIN` | 75% | General human-sound attenuation. |
| `DUCK_DEPTH_SOUFFLES` | 95% | Priority treatment for whispering, sighs and breathing. |
| `PROFIL_RESPIRATOIRE_RENFORCE` | On | Includes sniffs, snorts, gasps and panting; strengthens intermediate detections. |
| `DUCK_DEPTH_RESIDUS` | 90% | Up to −20 dB additional attenuation on human residues in the already-cleaned mix. 0% skips residual analysis entirely. |
| `GAIN_ANALYSE_RESIDUS_DB` | +18 dB | Maximum local gain for residual detection only, peak-limited per window. 0 dB uses only native-level scores. |
| `DUCK_DEPTH_BOUCHE` | 95% | Contextual mouth-noise attenuation. |
| `GAIN_BODYTALK_DB` | +3.5 dB | Guarded lift for clothing-movement proxies; set to 0 dB to disable or 2 dB for the previous gain. |
| `DUCK_DEPTH_AMBIANCE` | 70% | Ambience, weather, traffic, room tone and hum attenuation. |
| `DUCK_DEPTH_HORS_PFX` | 85% | Music, TV/radio, vehicles, sirens and similar content attenuation. |
| `PROTECTION_PFX` | 70% | Local protection of PFX evidence during denoise and masking. |

Respiratory and residual removal can accumulate: maximal masks at the defaults produce about −46 dB of combined gain, in addition to separation and denoise. This applies locally where detected, not uniformly to the clip. Residual detection adds short YAMNet calls but does not rerun the separators. The control value is a maximum: masks, guards and available headroom determine the actual clothing lift.

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
| `Colab_Backend_PFX_V3_5_2.ipynb` | MDX23C / BS-RoFormer backend with corrected BWF UMIDs. |
| `Colab_Backend_PFX_V3_5_1.ipynb` | Preserved previous backend, without the UMID fix. |
| `Colab_Backend_PFX_Vtest_V3.ipynb` | Bandit with single maximum human attenuation. |
| `Colab_Backend_PFX_Vtest_V4.ipynb` | Bandit with successive raw-mask and residual attenuation. |
| `architecture.md` | Detailed technical architecture and delivery contract. |
| `changelog.md` | Historical changes. |
| `work/` | Local runtime cache, logs, downloaded WAV files and generated deliveries. Ignored by Git. |
| `template.ptx` | Local proprietary Pro Tools template. Ignored by Git. |

## Limitations

PFX Extractor is an assistive restoration workflow, not a perfect source-isolation system.

- A detected human sound can overlap desired clothing or prop detail; stronger removal can reduce both.
- A wanted effect can be misclassified, and an unwanted sound can remain undetected.
- The bodytalk control raises detected portions of the already processed mix; simultaneous sounds may also rise. It cannot restore detail removed earlier in source separation.
- Pro Tools delivery currently supports a maximum of two filename families/tracks.
- The Colab backend, GPU availability, third-party model hosting and Google services are external dependencies. Retain your original recordings and evaluate a trial batch before processing a whole production.

## Documentation

- [Architecture](architecture.md)
- [Changelog](changelog.md)
- [pt_api](https://github.com/sebedard-creator/pt_api)

## License and attribution

Copyright © 2026 sebedard-creator.

This project is licensed under the [Attribution Assurance License](LICENSE). Use, modification and redistribution are permitted under its conditions. A redistributed executable program—or a program dependent on it—must visibly show this attribution at launch:

> PFX Extractor by sebedard-creator — https://github.com/sebedard-creator/PFX-Extractor

The attribution requirement does not grant permission to imply endorsement by sebedard-creator.

---

Designed by Sébastien Bédard.
