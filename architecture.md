# ARCHITECTURE TECHNIQUE (PFX-EXTRACTOR v1.0)

## 1. VUE D'ENSEMBLE DU SYSTÈME
PFX-EXTRACTOR est une application hybride composée d'une interface locale de gestion de fichiers (le "Drive Bridge" en Gradio) et d'un moteur de traitement audio puissant propulsé par un backend Google Colab. L'application permet de faciliter l'extraction d'effets sonores de production (PFX) à partir de fichiers audio bruts en déléguant l'inférence IA au Cloud.

## 2. FLUX DE TRAVAIL ET SYNCHRONISATION (DRIVE BRIDGE)
L'application locale sert de passerelle fluide entre le poste de travail de l'utilisateur et Google Colab, en utilisant Google Drive comme espace tampon.

1. **Upload (Envoi) :** L'utilisateur dépose ses fichiers bruts (`.wav`) dans l'interface Gradio. L'application les copie dans un dossier de travail local puis les synchronise automatiquement vers Google Drive dans le dossier `PFX_Extractor/1_Bruts_vers_Colab`.
2. **Traitement Colab (IA) :** L'utilisateur lance le backend Google Colab via le bouton dédié. Le notebook Colab est responsable de récupérer les fichiers bruts, d'exécuter l'inférence IA lourde (ex: BS-RoFormer) pour extraire les environnements, et de sauvegarder les pistes traitées sur Drive dans `PFX_Extractor/2_Environnements_IA`.
3. **Download (Récupération) :** Une fois le traitement Colab terminé, l'utilisateur télécharge les fichiers traités directement depuis l'interface locale. L'application récupère les fichiers depuis Drive et génère une archive `.zip` contenant le résultat final.
4. **Flush (Nettoyage) :** L'utilisateur peut vider le cache local et nettoyer les répertoires sur Google Drive en un clic depuis l'interface Gradio pour préparer une nouvelle session de travail.

## 3. ARCHITECTURE DES COMPOSANTS
Le code local est structuré autour de plusieurs modules distincts :

- **Moteur Frontend / Drive Bridge (`app_local.py`) :** Interface web locale développée avec Gradio. Elle ne gère aucun traitement audio directement, mais orchestre l'expérience utilisateur, l'upload, le téléchargement, et le nettoyage des fichiers.
- **Gestionnaire API Drive (`drive_auth.py`) :** Module robuste chargé de l'authentification OAuth 2.0 avec l'API Google Drive. Il s'occupe de la création de la hiérarchie de dossiers requise et des transferts bidirectionnels de fichiers.
- **Module DSP (`dsp_local.py`) :** Bibliothèque de fonctions avancées de traitement numérique du signal (Filtre DC, Masques Multi-résolution via Librosa, réduction de bruit non-stationnaire `noisereduce`). *Note : Ce module contient la logique de post-traitement du signal initialement prévue pour du temps réel, mais agit pour l'instant comme une bibliothèque indépendante dans la version actuelle du Drive Bridge.*
- **Backend Colab (`Colab_Backend_PFX_FINAL_26_Juin_v3.ipynb`) :** Le script exécuté sur les serveurs de Google (GPU), responsable de la séparation de sources (inclut désormais une gestion intelligente des silences et un mode de reprise rapide).
- **Scripts de lancement (`start.bat`, `stop.bat`, `*.vbs`) :** Scripts utilitaires pour instancier le serveur Gradio de manière invisible pour l'utilisateur.

## 4. GESTION DE L'ESPACE DE TRAVAIL LOCAL
L'application crée automatiquement un répertoire `work` à sa racine pour stocker les fichiers de manière transitoire :
- `work/bruts` : Copies locales des fichiers avant upload.
- `work/processed` : Fichiers récupérés depuis Drive avant compression.
- `work/exports` : Archives ZIP finales générées pour l'utilisateur.
- `work/gradio_tmp` : Fichiers temporaires gérés par l'interface Gradio.
