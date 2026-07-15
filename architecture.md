# ARCHITECTURE TECHNIQUE (PFX-EXTRACTOR v2.1)

## 1. VUE D'ENSEMBLE DU SYSTÈME
PFX-EXTRACTOR est une application hybride composée d'une interface locale de gestion de fichiers (le "Drive Bridge" en Gradio) et d'un moteur de traitement audio puissant propulsé par un backend Google Colab. L'application permet de faciliter l'extraction d'effets sonores de production (PFX) à partir de fichiers audio bruts en déléguant l'inférence IA au Cloud. Depuis la V2.0, le backend Colab combine deux familles de modèles IA distinctes : des modèles de **séparation de source** (BS-RoFormer, MDX23C) pour isoler la piste non-vocale, et un modèle de **détection d'événements sonores** (YAMNet) pour repérer les vocalisations humaines non-lexicales (soupirs, cris, chants) que les modèles de séparation laissent passer.

## 2. FLUX DE TRAVAIL ET SYNCHRONISATION (DRIVE BRIDGE)
L'application locale sert de passerelle fluide entre le poste de travail de l'utilisateur et Google Colab, en utilisant Google Drive comme espace tampon.

1. **Upload (Envoi) :** L'utilisateur dépose ses fichiers bruts (`.wav`) dans l'interface Gradio. L'application les copie dans un dossier de travail local puis les synchronise automatiquement vers Google Drive dans le dossier `PFX_Extractor/1_Bruts_vers_Colab`.
2. **Traitement Colab (IA) :** L'utilisateur lance le backend Google Colab via le bouton dédié. Le notebook Colab récupère les fichiers bruts, aligne et regroupe les prises, exécute une passe de détection YAMNet (vocalisations humaines / bodytalk), applique le pré-denoise (avec protection bodytalk), effectue l'inférence IA lourde de séparation (RoFormer + MDX23C), applique le ducking anti-vocalisation sur le mix final, réinjecte le timecode BWF, puis sauvegarde les pistes traitées sur Drive dans `PFX_Extractor/2_Environnements_IA`.
3. **Download (Récupération) :** Une fois le traitement Colab terminé, l'utilisateur télécharge les fichiers traités directement depuis l'interface locale. L'application récupère les fichiers depuis Drive et génère une archive `.zip` contenant le résultat final.
4. **Flush (Nettoyage) :** L'utilisateur peut vider le cache local et nettoyer les répertoires sur Google Drive en un clic depuis l'interface Gradio pour préparer une nouvelle session de travail.

## 3. ARCHITECTURE DES COMPOSANTS
Le code local est structuré autour de plusieurs modules distincts :

- **Moteur Frontend / Drive Bridge (`app_local.py`) :** Interface web locale développée avec Gradio. Elle ne gère aucun traitement audio directement, mais orchestre l'expérience utilisateur, l'upload, le téléchargement, et le nettoyage des fichiers.
- **Gestionnaire API Drive (`drive_auth.py`) :** Module robuste chargé de l'authentification OAuth 2.0 avec l'API Google Drive. Il s'occupe de la création de la hiérarchie de dossiers requise et des transferts bidirectionnels de fichiers.
- **~~Module DSP (`dsp_local.py`)~~ — DÉPRÉCIÉ (V2.1) :** Bibliothèque de fonctions DSP (Filtre DC, Masques Multi-résolution via Librosa, réduction de bruit non-stationnaire) initialement prévue comme couche de post-traitement local. Confirmé inutilisé (aucun import dans `app_local.py`) et retiré de la boucle de traitement — toute la logique équivalente (protection du bodytalk, denoise) a été réintégrée directement dans le backend Colab, qui centralise maintenant l'ensemble du traitement. Le fichier reste dans le dépôt à titre de référence mais n'est plus appelé nulle part.
- **Backend Colab (`Colab_Backend_PFX_V2.1_YAMNet.ipynb`) :** Le script exécuté sur les serveurs de Google (GPU), responsable de :
  - la séparation de sources (RoFormer + MDX23C, fusion pondérée configurable) ;
  - l'alignement automatique Lav/Boom avec garde-fou de confiance (voir ci-dessous) ;
  - le pré-nettoyage adaptatif avec protection bodytalk ;
  - la gestion intelligente des silences et le fallback anti-crash ;
  - la réinjection du timecode BWF ;
  - le bilan financier (Compute Units / USD) en fin de session.
- **Détecteur d'événements sonores (YAMNet, intégré au backend Colab, V2.0+) :** Modèle de classification audio générique (521 classes AudioSet), indépendant des modèles de séparation de source. Tourne sur l'audio fusionné brut, avant tout traitement, pour détecter deux catégories de classes (sélectionnées par correspondance de mots-clés sur la vraie taxonomie du modèle, imprimées en logs pour audit) :
  - *Vocalisations humaines* (soupir, cri, chant, respiration...) → pilote le ducking du mix final ;
  - *Bodytalk* (pas, tissu...) → pilote la restauration du signal brut pendant le pré-denoise, pour éviter que le nettoyage n'attaque le bodytalk légitime.

  Remplace le sidechain V1.22 (basé sur le stem "Vocals" jeté par les modèles de séparation), abandonné après confirmation que ces modèles ne détectent quasiment aucune trace vocale sur des sons non-lexicaux comme les soupirs.
- **Garde-fou de confiance sur l'alignement (V2.1) :** L'auto-alignement Lav/Boom (basé sur une corrélation croisée) calcule désormais un score de confiance normalisé avant d'appliquer un décalage temporel. Si deux clips regroupés sous le même identifiant de prise n'ont en réalité aucun rapport acoustique (ex. collision de nommage), l'alignement est ignoré et le clip est copié tel quel plutôt que d'être corrompu.
- **Scripts de lancement (`start.bat`, `stop.bat`, `*.vbs`) :** Scripts utilitaires pour instancier le serveur Gradio de manière invisible pour l'utilisateur.

## 4. GESTION DE L'ESPACE DE TRAVAIL LOCAL
L'application crée automatiquement un répertoire `work` à sa racine pour stocker les fichiers de manière transitoire :
- `work/bruts` : Copies locales des fichiers avant upload.
- `work/processed` : Fichiers récupérés depuis Drive avant compression.
- `work/exports` : Archives ZIP finales générées pour l'utilisateur.
- `work/gradio_tmp` : Fichiers temporaires gérés par l'interface Gradio.
