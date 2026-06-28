import os
from pathlib import Path

import drive_auth


drive_auth.ensure_work_dirs()
os.environ.setdefault("GRADIO_TEMP_DIR", str(drive_auth.GRADIO_TEMP_DIR))

import gradio as gr


CONFIG_FILE = Path(__file__).parent / "colab_link.txt"
def get_colab_url():
    if CONFIG_FILE.exists():
        url = CONFIG_FILE.read_text(encoding="utf-8").strip()
        if url: return url
    return "https://colab.research.google.com/drive/19rekAnGgcTPwi_z9j__2NoQeJD2C7Nwq"

COLAB_URL = get_colab_url()
COMPUTE_UNITS_URL = "https://colab.research.google.com/signup"

CSS = """
:root {
    --pfx-compact-gap: 6px;
}
.gradio-container {
    max-width: 940px !important;
    padding: 4px 12px 2px !important;
    margin: 0 auto !important;
}
footer,
.footer,
#footer {
    display: none !important;
}
.block,
.form,
.panel {
    margin-bottom: 6px !important;
}
.pfx-path {
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 0.72rem;
}
.pfx-status textarea {
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 0.76rem;
    line-height: 1.15;
}
.pfx-confirm {
    border: 1px solid #d9dde7;
    border-radius: 6px;
    padding: 6px 8px;
    margin: 2px 0;
}
.pfx-confirm p {
    margin: 0 0 4px 0;
    font-size: 0.78rem;
}
.pfx-footer {
    text-align: right;
    font-size: 0.62rem;
    color: #777;
    margin-top: 0;
    line-height: 1;
}
"""

AUTO_DOWNLOAD_JS = """
() => {
    setTimeout(() => {
        const container = document.querySelector("#pfx_zip_output");
        const link = container?.querySelector("a[download], a[href*='/file='], a[href*='/file/']");
        if (link) {
            link.click();
        }
    }, 800);
}
"""

def _plural(count, singular, plural=None):
    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural or singular + 's'}"


def _names_preview(names, limit=8):
    if not names:
        return ""
    visible = names[:limit]
    suffix = "" if len(names) <= limit else f"\n... +{len(names) - limit} autres fichiers"
    return "\n".join(f"- {name}" for name in visible) + suffix


def upload_raw_files(files):
    if not files:
        raise gr.Error("Depose d'abord les fichiers bruts dans la zone d'upload.")

    try:
        staged_paths = drive_auth.stage_uploaded_files(files)
        if not staged_paths:
            raise gr.Error("Aucun fichier valide n'a ete recu.")

        result = drive_auth.upload_files(staged_paths)
    except gr.Error:
        raise
    except Exception as exc:
        return (
            "Upload interrompu.\n\n"
            f"Erreur: {exc}\n\n"
            "Les copies locales restent dans le dossier de travail."
        ), None

    count = result["count"]
    if count == 0:
        status = "Aucun fichier n'a pu etre uploade vers Google Drive."
        if result["failed"]:
            status += "\n\nErreurs:\n" + _names_preview(result["failed"], limit=8)
        return status, None

    names = [Path(path).name for path in staged_paths]
    status = (
        f"Upload termine: {_plural(count, 'fichier')} envoye(s) vers "
        f"{drive_auth.PARENT_FOLDER_NAME}/{drive_auth.RAW_FOLDER_NAME}.\n\n"
        f"Copies locales:\n{_names_preview(names)}"
    )
    if result["failed"]:
        status += "\n\nCertains fichiers n'ont pas pu etre uploades:\n" + _names_preview(result["failed"], limit=8)
    return status, None


def download_processed_zip():
    try:
        zip_path, result = drive_auth.download_processed_as_zip()
    except Exception as exc:
        return (
            "Download interrompu.\n\n"
            f"Erreur: {exc}"
        ), None

    count = result["count"]
    if not zip_path or count == 0:
        raise gr.Error(
            f"Aucun fichier traite trouve dans "
            f"{drive_auth.PARENT_FOLDER_NAME}/{drive_auth.PROCESSED_FOLDER_NAME}."
        )

    status = (
        f"ZIP cree: {_plural(count, 'fichier')} telecharge(s) depuis Drive.\n"
        f"{zip_path}\n\n"
        f"Contenu:\n{_names_preview(result['names'])}"
    )
    return status, zip_path


def show_clear_confirmation():
    return gr.update(visible=True)


def hide_clear_confirmation():
    return gr.update(visible=False)


def clear_cache():
    try:
        result = drive_auth.clear_all_cache(include_runtime=True)
    except Exception as exc:
        drive_auth.ensure_work_dirs()
        status = (
            "Effacement interrompu.\n\n"
            f"Erreur: {exc}\n\n"
            "Aucun fichier systeme n'a ete supprime. "
            "Si Google demande une autorisation, relance l'action apres avoir termine la connexion."
        )
        return status, None, None, gr.update(visible=False)

    status = (
        "Cache effacee.\n"
        f"Elements locaux supprimes: {result['local_deleted']}\n"
        f"Fichiers Drive supprimes: {result['drive_deleted']}\n"
        f"Dossier conserve: {drive_auth.WORK_DIR}"
    )
    if result["drive_failed"]:
        status += (
            "\n\nCertains fichiers Drive n'ont pas pu etre supprimes:\n"
            + _names_preview(result["drive_failed"], limit=5)
        )
    return status, None, None, gr.update(visible=False)


with gr.Blocks(title="PFX Extractor - Drive Bridge", css=CSS) as demo:
    gr.Textbox(
        label="Dossier de travail local",
        value=str(drive_auth.WORK_DIR),
        interactive=False,
        elem_classes=["pfx-path"],
    )

    raw_files = gr.File(
        label="Deposer les fichiers bruts",
        file_count="multiple",
        file_types=[".wav", ".WAV"],
        type="filepath",
        height=118,
    )

    with gr.Row():
        upload_btn = gr.Button("Upload vers Google Drive", variant="primary", size="lg")
        colab_btn = gr.Button("Ouvrir Google Colab", variant="secondary", size="lg")
        gr.Button("➕ Compute Units", link=COMPUTE_UNITS_URL, variant="secondary", size="lg")

    with gr.Row():
        download_btn = gr.Button("Telecharger les fichiers traites en ZIP", variant="primary", size="lg")
        clear_btn = gr.Button("Effacer la cache", variant="stop", size="lg")

    with gr.Group(visible=False, elem_classes=["pfx-confirm"]) as clear_confirmation:
        gr.Markdown(
            "Confirmer la suppression des fichiers locaux de travail et des fichiers Drive dans "
            "`PFX_Extractor/1_Bruts_vers_Colab` et `PFX_Extractor/2_Environnements_IA`."
        )
        with gr.Row():
            confirm_clear_btn = gr.Button("Confirmer", variant="stop", size="sm")
            cancel_clear_btn = gr.Button("Annuler", variant="secondary", size="sm")

    colab_link_box = gr.Textbox(visible=False, value=COLAB_URL)

    status_box = gr.Textbox(
        label="Statut",
        value="Pret.",
        interactive=False,
        lines=4,
        elem_classes=["pfx-status"],
    )

    zip_output = gr.File(
        label="ZIP pret a telecharger",
        interactive=False,
        elem_id="pfx_zip_output",
    )

    upload_btn.click(
        fn=upload_raw_files,
        inputs=raw_files,
        outputs=[status_box, raw_files],
        show_api=False,
    )

    download_event = download_btn.click(
        fn=download_processed_zip,
        inputs=None,
        outputs=[status_box, zip_output],
        show_api=False,
    )
    download_event.then(fn=None, js=AUTO_DOWNLOAD_JS)

    clear_btn.click(
        fn=show_clear_confirmation,
        inputs=None,
        outputs=clear_confirmation,
        show_api=False,
    )
    cancel_clear_btn.click(
        fn=hide_clear_confirmation,
        inputs=None,
        outputs=clear_confirmation,
        show_api=False,
    )
    confirm_clear_btn.click(
        fn=clear_cache,
        inputs=None,
        outputs=[status_box, raw_files, zip_output, clear_confirmation],
        show_api=False,
    )

    with gr.Accordion("⚙️ Paramètres avancés", open=False):
        gr.Markdown("Si vous avez créé une nouvelle version du notebook Colab, collez son URL ici pour mettre à jour le bouton principal.")
        with gr.Row():
            colab_url_input = gr.Textbox(label="Nouveau lien Google Colab", value=COLAB_URL, scale=4)
            save_url_btn = gr.Button("Sauvegarder le lien", variant="secondary", scale=1)

    def save_colab_url(new_url):
        CONFIG_FILE.write_text(new_url.strip(), encoding="utf-8")
        return new_url.strip(), "Lien Colab mis à jour avec succès et sauvegardé pour les prochaines sessions !"

    save_url_btn.click(
        fn=save_colab_url,
        inputs=colab_url_input,
        outputs=[colab_link_box, status_box],
        show_api=False,
    )

    # Ouvre le lien dynamiquement en lisant la dernière version sauvegardée
    colab_btn.click(
        fn=None,
        inputs=[colab_link_box],
        outputs=None,
        js="(url) => { window.open(url, '_blank'); }",
        show_api=False,
    )

    gr.HTML("<div class='pfx-footer'>PFX Extractor v1.0 - 2026</div>")


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="0.0.0.0",
        server_port=7862,
        inbrowser=False,
        allowed_paths=[str(drive_auth.WORK_DIR)],
        show_api=False,
    )
