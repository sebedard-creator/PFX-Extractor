import io
import os
import shutil
import zipfile
import json
import tempfile
from datetime import datetime
from pathlib import Path
from delivery_contract import (DELIVERY_MANIFEST, validate_delivery_manifest,
                               verify_delivery_file, verify_unique_wave_umids)

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR / "work"
RAW_DIR = WORK_DIR / "bruts"
PROCESSED_DIR = WORK_DIR / "processed"
EXPORTS_DIR = WORK_DIR / "exports"
GRADIO_TEMP_DIR = WORK_DIR / "gradio_tmp"

PARENT_FOLDER_NAME = "PFX_Extractor"
RAW_FOLDER_NAME = "1_Bruts_vers_Colab"
PROCESSED_FOLDER_NAME = "2_Environnements_IA"

# Full Drive scope is required because Colab creates processed files outside this app.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def ensure_work_dirs():
    for folder in [WORK_DIR, RAW_DIR, PROCESSED_DIR, EXPORTS_DIR, GRADIO_TEMP_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def _as_path(file_obj):
    if file_obj is None:
        return None
    if isinstance(file_obj, str):
        return Path(file_obj)
    if isinstance(file_obj, dict):
        path_value = file_obj.get("path") or file_obj.get("name")
        return Path(path_value) if path_value else None
    name = getattr(file_obj, "name", None)
    return Path(name) if name else None


def _unique_path(folder, filename):
    target = folder / Path(filename).name
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = folder / f"{stem}_{counter:03d}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def stage_uploaded_files(files):
    ensure_work_dirs()
    if not files:
        return []

    staged_paths = []
    for file_obj in files:
        source = _as_path(file_obj)
        if not source or not source.exists() or not source.is_file():
            continue

        destination = _unique_path(RAW_DIR, source.name)
        shutil.copy2(source, destination)
        staged_paths.append(str(destination))

    return staged_paths


def authenticate_drive():
    creds = None
    token_path = BASE_DIR / "token.json"
    credentials_path = BASE_DIR / "credentials.json"

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    missing_scope = bool(creds and not creds.has_scopes(SCOPES))
    if not creds or not creds.valid or missing_scope:
        if creds and creds.expired and creds.refresh_token and not missing_scope:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None

        if not creds or not creds.valid:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    "Le fichier credentials.json est introuvable a la racine de PFX Extractor."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


def _escape_query(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


def get_or_create_folder(service, folder_name, parent_id=None):
    safe_name = _escape_query(folder_name)
    query = (
        f"name='{safe_name}' and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=10,
    ).execute()
    items = results.get("files", [])

    if items:
        return items[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def get_pfx_folders(service):
    parent_id = get_or_create_folder(service, PARENT_FOLDER_NAME)
    raw_id = get_or_create_folder(service, RAW_FOLDER_NAME, parent_id)
    processed_id = get_or_create_folder(service, PROCESSED_FOLDER_NAME, parent_id)
    return parent_id, raw_id, processed_id


def _list_files_in_folder(service, folder_id):
    files = []
    page_token = None
    query = (
        f"'{folder_id}' in parents and trashed=false and "
        "mimeType!='application/vnd.google-apps.folder'"
    )

    while True:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            pageToken=page_token,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def _report_progress(progress, value, description):
    """Informe Gradio sans évaluer son objet Progress comme un booléen.

    Certaines versions de Gradio évaluent ``bool(progress)`` via ``__len__``.
    Pendant un callback, cette liste peut être vide et lever IndexError. Une
    présence explicite est donc la seule vérification sûre ici.
    """
    if progress is not None:
        progress(value, desc=description)


def upload_files(filepaths, progress=None):
    if not filepaths:
        return {"count": 0, "names": [], "failed": []}

    service = authenticate_drive()
    _, raw_folder_id, _ = get_pfx_folders(service)

    uploaded_names = []
    failed = []
    total = len(filepaths)
    for index, filepath in enumerate(filepaths, start=1):
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            failed.append(f"{path}: fichier introuvable")
            _report_progress(progress, index / total, f"Fichier {index}/{total} introuvable : {path.name}")
            continue

        _report_progress(
            progress,
            (index - 1) / max(total, 1),
            f"Envoi {index}/{total} : {path.name} — {len(uploaded_names)} fichier(s) envoyé(s)",
        )

        metadata = {"name": path.name, "parents": [raw_folder_id]}
        media = None
        try:
            media = MediaFileUpload(str(path), mimetype="audio/wav",
                                    chunksize=8 * 1024 * 1024, resumable=True)
            request = service.files().create(body=metadata, media_body=media, fields="id")
            response = None
            while response is None:
                chunk_status, response = request.next_chunk(num_retries=3)
                if chunk_status is not None:
                    fraction = min(1.0, max(0.0, chunk_status.progress()))
                    _report_progress(
                        progress, ((index - 1) + fraction) / total,
                        f"Envoi {index}/{total} : {path.name} — {fraction:.0%} "
                        f"({len(uploaded_names)} fichier(s) envoyé(s))",
                    )
            uploaded_names.append(path.name)
            _report_progress(progress, index / total,
                             f"{len(uploaded_names)}/{total} fichier(s) envoyé(s) — {path.name}")
        except Exception as exc:
            failed.append(f"{path.name}: {exc}")
            _report_progress(progress, index / total,
                             f"Échec {index}/{total} : {path.name}")
        finally:
            if media is not None:
                media.stream().close()

    _report_progress(progress, 1.0,
                     f"Upload terminé : {len(uploaded_names)}/{total} fichier(s) envoyé(s)"
                     + (f" — {len(failed)} échec(s)" if failed else ""))

    return {"count": len(uploaded_names), "names": uploaded_names, "failed": failed}


def download_processed_files(progress=None):
    """Télécharge les sorties Drive dans work/processed sans créer d'archive."""
    ensure_work_dirs()
    service = authenticate_drive()
    _, _, processed_folder_id = get_pfx_folders(service)

    files = _list_files_in_folder(service, processed_folder_id)
    pointers = [item for item in files if item['name'] == DELIVERY_MANIFEST]
    if pointers:
        if len(pointers) != 1:
            raise ValueError('Plusieurs manifestes de livraison sur Drive; lot ambigu.')
        return _download_verified_generation(service, processed_folder_id, pointers[0], progress)
    files = [item for item in files if item['name'].lower().endswith('.wav')
             and not item['name'].startswith('._')]
    if not files:
        return [], {"count": 0, "names": []}

    _clear_directory_contents(PROCESSED_DIR)
    downloaded_paths = []
    total = len(files)

    for index, item in enumerate(files, start=1):
        destination = _unique_path(PROCESSED_DIR, item["name"])
        _report_progress(
            progress,
            (index - 1) / max(total, 1),
            f"Download {index}/{total}: {item['name']}",
        )

        request = service.files().get_media(fileId=item["id"])
        with io.FileIO(destination, "wb") as handle:
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        downloaded_paths.append(destination)

    verify_unique_wave_umids(downloaded_paths)
    _report_progress(progress, 1.0, "Fichiers traites telecharges")

    return downloaded_paths, {
        "count": len(downloaded_paths),
        "names": [path.name for path in downloaded_paths],
        "verified": False,
    }


def _download_verified_generation(service, parent_id, pointer, progress=None):
    """Fail closed for V3; preserve previous local delivery until all checks pass."""
    content = service.files().get_media(fileId=pointer['id']).execute()
    manifest = json.loads(content)
    outputs = validate_delivery_manifest(manifest)
    query = (f"'{_escape_query(parent_id)}' in parents and trashed=false and "
             f"name='{_escape_query(manifest['run_folder'])}' and "
             "mimeType='application/vnd.google-apps.folder'")
    folders = service.files().list(q=query, fields='files(id,name)', pageSize=1000).execute().get('files', [])
    if len(folders) != 1:
        raise ValueError('Dossier du lot absent ou ambigu.')
    items = _list_files_in_folder(service, folders[0]['id'])
    by_name = {}
    for item in items:
        if item['name'].lower().endswith('.wav'):
            if item['name'].casefold() in by_name:
                raise ValueError('WAV dupliqué dans le lot Drive.')
            by_name[item['name'].casefold()] = item
    if set(by_name) != {entry['name'].casefold() for entry in outputs}:
        raise ValueError('Liste des WAV différente du manifeste; livraison refusée.')
    # TemporaryDirectory removes only this call's staging on failure, never old results.
    with tempfile.TemporaryDirectory(prefix='download_v3_', dir=WORK_DIR) as temporary:
        staging = Path(temporary) / 'processed'
        staging.mkdir()
        for index, entry in enumerate(outputs):
            _report_progress(progress, index / len(outputs), f"Vérification {index + 1}/{len(outputs)}: {entry['name']}")
            destination = staging / entry['name']
            request = service.files().get_media(fileId=by_name[entry['name'].casefold()]['id'])
            with destination.open('wb') as handle:
                downloader = MediaIoBaseDownload(handle, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            verify_delivery_file(destination, entry)
        verify_unique_wave_umids([staging / e['name'] for e in outputs],
                                 forbidden=[e['umid'] for e in manifest.get('inputs', []) if 'umid' in e])
        # Detect a run switch/failure during download, including a replaced pointer file.
        current = [item for item in _list_files_in_folder(service, parent_id)
                   if item['name'] == DELIVERY_MANIFEST]
        if len(current) != 1:
            raise ValueError('Manifeste modifié pendant le téléchargement.')
        latest = service.files().get_media(fileId=current[0]['id']).execute()
        if json.loads(latest) != manifest:
            raise ValueError('Le traitement a changé pendant le téléchargement; recommencez après sa fin.')
        (staging / DELIVERY_MANIFEST).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        backup = None
        if PROCESSED_DIR.exists():
            backup = Path(tempfile.mkdtemp(prefix='processed_previous_', dir=WORK_DIR)) / 'processed'
            PROCESSED_DIR.rename(backup)
        try:
            staging.rename(PROCESSED_DIR)
        except Exception:
            if backup is not None:
                backup.rename(PROCESSED_DIR)
            raise
    _report_progress(progress, 1.0, 'Lot complet vérifié : empreintes, durées, timecodes et UMID distincts')
    return [PROCESSED_DIR / e['name'] for e in outputs], {
        'count': len(outputs), 'names': [e['name'] for e in outputs],
        'verified': True, 'run_id': manifest['run_id'],
    }


def download_processed_as_zip(progress=None):
    """Compatibilité: télécharge les sorties puis crée l'ancien ZIP de WAV."""
    downloaded_paths, result = download_processed_files(progress=progress)
    if not downloaded_paths:
        return None, result

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = EXPORTS_DIR / f"PFX_processed_{timestamp}.zip"
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as archive:
        for path in downloaded_paths:
            archive.write(path, arcname=path.name)

    return str(zip_path), result


def clear_local_cache(include_runtime=False):
    ensure_work_dirs()
    deleted = 0
    for folder in [RAW_DIR, PROCESSED_DIR, EXPORTS_DIR]:
        deleted += _clear_directory_contents(folder)
    if include_runtime:
        deleted += _clear_directory_contents(GRADIO_TEMP_DIR)
    ensure_work_dirs()
    return deleted


def clear_drive_cache(progress=None):
    service = authenticate_drive()
    _, raw_folder_id, processed_folder_id = get_pfx_folders(service)

    deleted = 0
    failed = []
    folders = [
        (RAW_FOLDER_NAME, raw_folder_id),
        (PROCESSED_FOLDER_NAME, processed_folder_id),
    ]

    for folder_index, (folder_name, folder_id) in enumerate(folders, start=1):
        files = _list_files_in_folder(service, folder_id)
        total = len(files)
        for file_index, item in enumerate(files, start=1):
            base = (folder_index - 1) / len(folders)
            span = 1 / len(folders)
            _report_progress(
                progress,
                base + (file_index - 1) / max(total, 1) * span,
                f"Effacement Drive {folder_name}: {file_index}/{total}",
            )
            try:
                service.files().delete(
                    fileId=item["id"],
                    supportsAllDrives=True,
                ).execute()
                deleted += 1
            except HttpError as exc:
                failed.append(f"{folder_name}/{item.get('name', item['id'])}: {exc}")
            except Exception as exc:
                failed.append(f"{folder_name}/{item.get('name', item['id'])}: {exc}")

    _report_progress(progress, 1.0, "Cache effacee")

    return {"deleted": deleted, "failed": failed}


def clear_all_cache(progress=None, include_runtime=False):
    drive_result = clear_drive_cache(progress=progress)
    local_deleted = clear_local_cache(include_runtime=include_runtime)
    return {
        "local_deleted": local_deleted,
        "drive_deleted": drive_result["deleted"],
        "drive_failed": drive_result["failed"],
    }


def _clear_directory_contents(folder):
    ensure_work_dirs()
    folder = Path(folder).resolve()
    work_root = WORK_DIR.resolve()
    if folder != work_root and work_root not in folder.parents:
        raise RuntimeError(f"Refus d'effacer hors du dossier de travail: {folder}")

    deleted = 0
    if not folder.exists():
        return deleted

    for child in folder.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        deleted += 1
    return deleted
