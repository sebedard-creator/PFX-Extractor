"""Construction locale d'une livraison Pro Tools depuis les WAV traités."""

import importlib
import importlib.util
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_PATH = BASE_DIR / "template.ptx"
DEFAULT_TRACK_NAMES = ("PFX 01", "PFX 02")

_PROCESSED_FILENAME = re.compile(
    r"^(?P<family>.+)-Gain_(?P<sequence>\d+)_PFX_Ready\.wav$",
    re.IGNORECASE,
)
_INVALID_WINDOWS_FILENAME = re.compile(r'[<>:"/\\|?*]')
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def _path_from_value(value):
    """Normalise les valeurs Path/Gradio usuelles sans accepter un objet vide."""
    if value is None:
        return None
    if isinstance(value, (str, os.PathLike)):
        return Path(value)
    if isinstance(value, dict):
        candidate = value.get("path") or value.get("name")
        return Path(candidate) if candidate else None
    candidate = getattr(value, "name", None)
    return Path(candidate) if candidate else None


def _load_pt_api_from_file(module_path):
    module_path = Path(module_path).resolve()
    if module_path.is_dir():
        module_path = module_path / "pt_api.py"
    if not module_path.is_file():
        return None

    spec = importlib.util.spec_from_file_location(
        "_pfx_extractor_pt_api", module_path
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    builder = getattr(module, "build_audio_session", None)
    return builder if callable(builder) else None


def resolve_pt_api_builder():
    """Trouve l'API installée, explicitement configurée ou dans le dépôt frère."""
    configured_path = os.environ.get("PT_API_PATH")
    if configured_path:
        builder = _load_pt_api_from_file(configured_path)
        if builder is not None:
            return builder
        raise RuntimeError(
            "PT_API_PATH ne pointe pas vers un module pt_api.py compatible."
        )

    try:
        module = importlib.import_module("pt_api")
    except ImportError:
        module = None
    if module is not None:
        builder = getattr(module, "build_audio_session", None)
        if callable(builder):
            return builder

    sibling_module = BASE_DIR.parent / "pt_api" / "pt_api.py"
    builder = _load_pt_api_from_file(sibling_module)
    if builder is not None:
        return builder

    raise RuntimeError(
        "pt_api 1.3.8+ est introuvable. Installez le paquet ou définissez "
        "PT_API_PATH vers pt_api.py."
    )


def resolve_template_path(template_path=None):
    """Retourne le template fourni ou le template.ptx livré avec l'application."""
    path = _path_from_value(template_path) or DEFAULT_TEMPLATE_PATH
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Template Pro Tools introuvable: {path}"
        )
    if path.suffix.lower() != ".ptx":
        raise ValueError("Le template Pro Tools doit avoir l'extension .ptx.")
    return path


def collect_processed_manifest(processed_dir, track_names=DEFAULT_TRACK_NAMES):
    """Crée le manifeste pt_api dans l'ordre alphabétique des fichiers."""
    processed_dir = Path(processed_dir).resolve()
    if not processed_dir.is_dir():
        raise FileNotFoundError(
            f"Dossier de fichiers traités introuvable: {processed_dir}"
        )
    if not track_names:
        raise ValueError("Au moins une piste Pro Tools cible est requise.")

    audio_paths = sorted(
        (
            path for path in processed_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".wav"
            and not path.name.startswith("._")
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )
    if not audio_paths:
        raise ValueError("Aucun WAV traité n'est disponible pour l'export Pro Tools.")

    seen_filenames = set()
    family_tracks = {}
    families = []
    descriptors = []
    for path in audio_paths:
        filename_key = path.name.casefold()
        if filename_key in seen_filenames:
            raise ValueError(
                f"Filename WAV dupliqué sans tenir compte de la casse: {path.name}"
            )
        seen_filenames.add(filename_key)

        match = _PROCESSED_FILENAME.fullmatch(path.name)
        if match is None:
            raise ValueError(
                "Filename traité non reconnu; format attendu: "
                "<famille>-Gain_<numéro>_PFX_Ready.wav. "
                f"Reçu: {path.name}"
            )
        family = match.group("family")
        family_key = family.casefold()
        if family_key not in family_tracks:
            family_index = len(family_tracks)
            if family_index >= len(track_names):
                raise ValueError(
                    f"{family_index + 1} familles détectées, mais seulement "
                    f"{len(track_names)} pistes Pro Tools sont configurées."
                )
            family_tracks[family_key] = track_names[family_index]
            families.append({
                "family": family,
                "track": track_names[family_index],
                "count": 0,
            })

        track_name = family_tracks[family_key]
        for entry in families:
            if entry["family"].casefold() == family_key:
                entry["count"] += 1
                break
        descriptors.append({
            "audio_path": path,
            "track_name": track_name,
        })

    return descriptors, families


def sanitize_session_name(session_name):
    """Valide un basename Windows utilisable comme dossier et fichier PTX."""
    if not isinstance(session_name, str):
        raise TypeError("Le nom de session doit être une chaîne.")
    name = session_name.strip()
    if name.lower().endswith(".ptx"):
        name = name[:-4].rstrip()
    if (
        not name
        or "\x00" in name
        or _INVALID_WINDOWS_FILENAME.search(name)
        or name.endswith((" ", "."))
    ):
        raise ValueError("Nom de session Pro Tools invalide.")
    if name.partition(".")[0].upper() in _WINDOWS_RESERVED_NAMES:
        raise ValueError("Nom de session réservé sous Windows.")
    return name


def suggest_session_name(families):
    """Propose un nom stable tout en laissant le frontend l'override."""
    names = [entry["family"] for entry in families]
    if not names:
        return "PFX_Session"

    if len(names) == 1:
        base = re.sub(
            r"(?:[_-](?:boom|lav|lavalier))$", "", names[0],
            flags=re.IGNORECASE,
        )
    else:
        base = os.path.commonprefix(names).rstrip(" _-")
    if not base:
        base = names[0]
    return sanitize_session_name(f"{base}_PFX")


def _unique_delivery_directory(exports_dir, session_name):
    candidate = exports_dir / session_name
    if not candidate.exists() and not candidate.with_suffix(".zip").exists():
        return candidate
    for index in range(1, 1000):
        candidate = exports_dir / f"{session_name}_{index:03d}"
        if not candidate.exists() and not candidate.with_suffix(".zip").exists():
            return candidate
    raise FileExistsError(
        f"Impossible de trouver un nom de livraison libre pour {session_name}."
    )


def _archive_session_directory(session_directory):
    """Crée atomiquement un ZIP dont la racine est le dossier de session."""
    final_path = session_directory.parent / f"{session_directory.name}.zip"
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{session_directory.name}.",
        suffix=".zip.tmp",
        dir=session_directory.parent,
    )
    os.close(descriptor)
    try:
        with zipfile.ZipFile(
            temporary_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
        ) as archive:
            for path in sorted(
                session_directory.rglob("*"),
                key=lambda item: str(item.relative_to(session_directory)).casefold(),
            ):
                if path.is_file():
                    archive.write(
                        path,
                        arcname=Path(session_directory.name)
                        / path.relative_to(session_directory),
                    )
        if final_path.exists():
            raise FileExistsError(f"Archive de livraison déjà existante: {final_path}")
        os.replace(temporary_path, final_path)
        temporary_path = None
        return final_path
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def create_protools_delivery(
    processed_dir,
    exports_dir,
    template_path=None,
    session_name=None,
    *,
    builder=None,
    track_names=DEFAULT_TRACK_NAMES,
):
    """Construit le dossier PTX/Audio Files et son ZIP téléchargeable."""
    descriptors, families = collect_processed_manifest(
        processed_dir, track_names=track_names
    )
    template = resolve_template_path(template_path)
    if session_name is None or (
        isinstance(session_name, str) and not session_name.strip()
    ):
        requested_name = suggest_session_name(families)
    else:
        requested_name = sanitize_session_name(session_name)

    exports_dir = Path(exports_dir).resolve()
    exports_dir.mkdir(parents=True, exist_ok=True)
    session_directory = _unique_delivery_directory(exports_dir, requested_name)
    delivered_name = session_directory.name
    builder = builder or resolve_pt_api_builder()

    try:
        result = builder(
            template,
            descriptors,
            session_directory,
            session_name=delivered_name,
        )
        if result.get("track_count") != len(families):
            raise ValueError(
                "Le nombre de pistes retourné par pt_api ne correspond pas "
                "aux familles détectées."
            )
        if len(result.get("clips", [])) != len(descriptors):
            raise ValueError(
                "Le nombre de clips retourné par pt_api est incohérent."
            )
        archive_path = _archive_session_directory(session_directory)
    except Exception:
        if session_directory.is_dir():
            shutil.rmtree(session_directory)
        raise

    return {
        **result,
        "session_directory": str(session_directory),
        "archive_path": str(archive_path),
        "families": families,
        "processed_count": len(descriptors),
    }
