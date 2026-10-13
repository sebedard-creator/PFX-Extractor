# PFX Extractor

Create a **Production FX** track from location recordings: retain clothing movement, footsteps, handling and props while reducing dialogue, breathing, mouth noises and unwanted ambience.

The Windows frontend transfers files through Google Drive. Audio processing runs in Google Colab; the final download is a Pro Tools session with its audio files.

## Choose a backend

Both backends are supported and use the same workflow. Choose by listening to the results on your recordings.

| | Bandit V4 | MDX23C + BS-RoFormer V3.5.2 |
| --- | --- | --- |
| Separation | One model trained for film dialogue/music/effects separation; uses its SFX output | Two models whose instrumental outputs are blended |
| Scene handling | Each WAV processed independently | Aligns BOOM/LAV when paired; temporarily groups short clips, then splits them back |
| Bodytalk gain | Up to +4 dB, with local peak headroom | Up to +3.5 dB, with peak headroom for the processed group |
| When to choose | For speed and processing each scene independently | An alternative when its human-sound removal sounds better on your footage |

- [Bandit V4 notebook](Colab_Backend_PFX_Bandit_V4.ipynb)
- [MDX23C + BS-RoFormer V3.5.2 notebook](Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb)

Both default to **40% adaptive pre-cleaning** and cumulative YAMNet removal: detection on the raw recording first, then residual detection on the cleaned output. The residual detector uses temporary gain up to **+18 dB**; this does not raise the output volume. Bodytalk gain targets clothing-movement detections, not footsteps.

Neither backend removes every human sound. Strong removal can also reduce simultaneous Foley; listening and manual finishing remain necessary.

## Setup

Requires **Windows, Python 3.10+, Git, Google Drive and a GPU-enabled Colab runtime**. A T4 is the usual processing configuration.

1. Download or clone this repository.
2. Place Google OAuth **Desktop app** credentials at the root as `credentials.json`, and supply a compatible `template.ptx`. The template is proprietary and not distributed here; its profile is documented in [architecture.md](architecture.md).
3. Run `start.bat`. It creates the Python environment and installs dependencies on first launch.
4. Open [localhost:7862](http://127.0.0.1:7862) and authorize Drive when prompted.

To update an existing installation, run this in the project folder, then restart the frontend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pro Tools export requires **[pt_api](https://github.com/sebedard-creator/pt_api) 1.6.2 or later**. Dependencies install v1.6.2; older or unidentified loaded versions are refused.

## Workflow

1. Add **mono 48 kHz BWF WAV** files with their original timestamps. Names must contain `BOOM` or `LAV`; if both types are present, their file counts must match.
2. Click **Upload vers Google Drive**. The progress bar shows the current file, its transfer percentage and the number of files sent.
3. Open either backend in Colab and run its cells in order. You can save its URL in **Paramètres avancés** for the **Ouvrir Google Colab** button.
4. Once processing finishes, click **Télécharger les fichiers traités en ZIP**.
5. Extract the ZIP and open the `.ptx` session. It includes `Audio Files/`, with clips placed at their BWF timestamps on up to two PFX tracks, at **48 kHz / 23.976 fps**.

Switching backends requires no manual Drive changes. Previous output generations are retained; incomplete or inconsistent deliveries are refused. Run only one notebook at a time.

Keep the ZIPs you need before using **Effacer la cache**: it removes local working files/exports and the Drive input/output folders after confirmation.

## Files and troubleshooting

Audio stays in your Colab/Drive workflow; no recording is sent to an external separation service. Credentials, tokens, audio caches and the proprietary template are excluded from Git.

If download or export fails, inspect the status and `work/app.log`. Check that Colab completed, the WAV format is supported, and the local template and API version are compatible. Downloaded WAVs remain available for diagnosis after an export failure.

Technical details: [architecture.md](architecture.md). Version history: [changelog.md](changelog.md).

Historical notebooks V3.5.1 and Test V3 are local-only archives, excluded from Git. The two supported backends are linked above.

## License

Created by **Sébastien Bédard / sebedard-creator**. Use, modification and redistribution are governed by the [Attribution Assurance License](LICENSE).

Redistribution must retain the license. Redistributed executables and dependent programs must display the required attribution at launch:

> sebedard-creator — PFX Extractor developer — https://github.com/sebedard-creator/PFX-Extractor
