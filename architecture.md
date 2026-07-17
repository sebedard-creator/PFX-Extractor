# ARCHITECTURE TECHNIQUE (PFX-EXTRACTOR v3.0)

## 1. VUE D'ENSEMBLE DU SYSTÈME
PFX-EXTRACTOR est une application hybride composée d'une interface locale de gestion de fichiers (le "Drive Bridge" en Gradio) et d'un moteur de traitement audio puissant propulsé par un backend Google Colab. L'application facilite la création d'une piste Production FX à partir de fichiers de tournage : elle conserve les effets synchrones de plateau (pas, vêtements, manipulations, props, impacts) tout en retirant les humains, les ambiances et le contenu éditorial hors PFX. Le backend combine des modèles de **séparation de source** (BS-RoFormer, MDX23C) et un modèle de **détection d'événements sonores** (YAMNet).

## 2. FLUX DE TRAVAIL ET SYNCHRONISATION (DRIVE BRIDGE)
L'application locale sert de passerelle fluide entre le poste de travail de l'utilisateur et Google Colab, en utilisant Google Drive comme espace tampon.

1. **Upload (Envoi) :** L'utilisateur dépose ses fichiers bruts (`.wav`) dans l'interface Gradio. L'application les copie dans un dossier de travail local puis les synchronise automatiquement vers Google Drive dans le dossier `PFX_Extractor/1_Bruts_vers_Colab`.
2. **Traitement Colab (IA) :** L'utilisateur lance le backend Google Colab via le bouton dédié. Le notebook récupère les fichiers bruts, aligne et regroupe les prises, calcule les masques YAMNet sur l'audio intact, applique le pré-denoise avec protection PFX, effectue la séparation RoFormer + MDX23C, applique séparément les retraits humain/ambiance/hors-PFX, réinjecte le timecode BWF, puis sauvegarde les pistes dans `PFX_Extractor/2_Environnements_IA`.
3. **Download et assemblage Pro Tools :** Une fois le traitement Colab terminé, un seul clic récupère les WAV depuis Drive dans `work/processed`, sans créer de ZIP WAV intermédiaire. L'application produit immédiatement une livraison autonome contenant la session `.ptx` et son dossier `Audio Files`, puis remet ce dossier dans un ZIP téléchargeable. Chaque placement vient du timestamp BWF du média; il ne s'agit donc pas d'une décision globale basée sur la durée du clip.
4. **Flush (Nettoyage) :** L'utilisateur peut vider le cache local, les livraisons générées et les répertoires sur Google Drive en un clic depuis l'interface Gradio pour préparer une nouvelle session de travail.

## 3. ARCHITECTURE DES COMPOSANTS
Le code local est structuré autour de plusieurs modules distincts :

- **Moteur Frontend / Drive Bridge (`app_local.py`) :** Interface web locale développée avec Gradio. Elle ne gère aucun traitement audio directement, mais orchestre l'expérience utilisateur, l'upload, le téléchargement, la livraison Pro Tools et le nettoyage des fichiers.
- **Gestionnaire API Drive (`drive_auth.py`) :** Module robuste chargé de l'authentification OAuth 2.0 avec l'API Google Drive. Il s'occupe de la création de la hiérarchie de dossiers requise et des transferts bidirectionnels de fichiers. `download_processed_files()` alimente le flux PTX sans compression intermédiaire; l'ancien helper `download_processed_as_zip()` reste disponible pour compatibilité, mais le frontend ne l'appelle plus.
- **Adaptateur de livraison Pro Tools (`protools_export.py`) :** Couche propre à PFX Extractor. Elle trie les WAV par filename, impose le format `<famille>-Gain_<numéro>_PFX_Ready.wav`, affecte la première famille à `PFX 01` et la seconde à `PFX 02`, puis appelle `build_audio_session()` de `pt_api` 1.3.8+. Une troisième famille est refusée explicitement. La recherche de l'API accepte `PT_API_PATH`, un module installé ou le dépôt frère `pt_api`. Cette politique applicative demeure hors de l'API générique.
- **Template Pro Tools locale (`template.ptx`) :** Modèle natif validé, vide sur la timeline, possédant les pistes `PFX 01`/`PFX 02` et le prototype média requis par le builder. Ce fichier propriétaire est exclu par `.gitignore` et doit être installé séparément à la racine de chaque déploiement. Le flux intégré cible des sessions mono 48 kHz à 23,976 fps. L'utilisateur peut fournir ponctuellement une autre template compatible dans les paramètres avancés.
- **~~Module DSP (`dsp_local.py`)~~ — DÉPRÉCIÉ (V2.1) :** Bibliothèque de fonctions DSP initialement prévue comme couche de post-traitement local. Confirmé inutilisé (aucun import dans `app_local.py`) et retiré de la boucle de traitement — la protection PFX et le denoise sont centralisés dans le backend Colab. Le fichier reste dans le dépôt à titre de référence mais n'est plus appelé nulle part.
- **Backend Colab (`Colab_Backend_PFX_V3_0.ipynb`) :** Le script exécuté sur les serveurs de Google (GPU), responsable de :
  - la séparation de sources (RoFormer + MDX23C, fusion pondérée configurable) ;
  - l'alignement automatique Lav/Boom avec garde-fou de confiance (voir ci-dessous) ;
  - le pré-nettoyage adaptatif avec protection PFX ;
  - la gestion intelligente des silences et le fallback anti-crash ;
  - la réinjection du timecode BWF ;
  - le bilan financier (Compute Units / USD) en fin de session.
- **Détecteur d'événements sonores (YAMNet, intégré au backend Colab) :** Modèle AudioSet indépendant des séparateurs. Les 521 indices sont partitionnés exactement, sans mots-clés ni chevauchement, en six rôles audités au chargement :
  - `RETIRER_HUMAIN` (61 classes) → masque humain rapide et seuil calibré ;
  - `RETIRER_AMBIANCE` (26 classes) → masque plus lent pour nature/météo, trafic et fonds continus ;
  - `RETIRER_HORS_PFX` (211 classes) → musique, TV/radio, véhicules, sirènes et graves/vibrations ;
  - `CONSERVER_PFX` (146 classes) → protection locale des pas, vêtements, props, impacts et outils ;
  - `TRAITER_CONTEXTE` (68 classes) → animaux et tonalités, arbitrés par persistance/transitoires ;
  - `EXCLURE_MASQUE_DIRECT` (9 classes) → contexte acoustique et silence, jamais convertis en gain local.

  Les scores passent par des seuils doux et des enveloppes attaque/relâchement propres à chaque rôle. La protection PFX réduit surtout le masque d'ambiance et ne restaure jamais 100 % du signal brut. Les masques restent au pas temporel YAMNet dans le cache et sont interpolés par blocs de 30 secondes pour limiter la mémoire.

  Remplace le sidechain V1.22 (basé sur le stem "Vocals" jeté par les modèles de séparation), abandonné après confirmation que ces modèles ne détectent quasiment aucune trace vocale sur des sons non-lexicaux comme les soupirs.
- **Garde-fou de confiance sur l'alignement (V2.1) :** L'auto-alignement Lav/Boom (basé sur une corrélation croisée) calcule désormais un score de confiance normalisé avant d'appliquer un décalage temporel. Si deux clips regroupés sous le même identifiant de prise n'ont en réalité aucun rapport acoustique (ex. collision de nommage), l'alignement est ignoré et le clip est copié tel quel plutôt que d'être corrompu.
- **Scripts de lancement (`start.bat`, `stop.bat`, `*.vbs`) :** Scripts utilitaires pour instancier le serveur Gradio de manière invisible pour l'utilisateur.

## 4. GESTION DE L'ESPACE DE TRAVAIL LOCAL
L'application crée automatiquement un répertoire `work` à sa racine pour stocker les fichiers de manière transitoire :
- `work/bruts` : Copies locales des fichiers avant upload.
- `work/processed` : Fichiers récupérés depuis Drive avant compression.
- `work/exports` : Archives WAV, dossiers de sessions Pro Tools autonomes et ZIP de livraison générés pour l'utilisateur. Une livraison Pro Tools contient `<session>/<session>.ptx` et `<session>/Audio Files/*.wav`.
- `work/gradio_tmp` : Fichiers temporaires gérés par l'interface Gradio.

## 5. CONTRAT DE LIVRAISON PRO TOOLS

`protools_export.py` conserve exactement l'ordre alphabétique des fichiers comme ordre de manifeste. Les familles sont découvertes dans cet ordre et le nombre maximal de pistes applicatif est deux. Les fichiers d'une même famille partagent la même piste; les overlaps provenant de leurs timestamps BWF sont conservés et le clip ultérieur reste le dernier événement ajouté.

La mutation PTX et la copie des WAV sont transactionnelles dans `pt_api` : toutes les sources et la template sont validées avant publication du dossier. PFX Extractor vérifie ensuite le nombre de pistes et de clips retournés, puis crée atomiquement le ZIP avec un dossier de session racine. En cas d'échec après le début du build, le nouveau dossier incomplet est supprimé; aucune archive incomplète n'est publiée. Les livraisons existantes ne sont pas écrasées : un suffixe numérique est attribué au prochain export.

Le flux complet a été validé le 17 juillet 2026 avec 62 médias BWF réels sur `PFX 01` : structure et hashes vérifiés automatiquement, puis ouverture, lecture, Save As, fermeture et réouverture réussis dans Pro Tools sans avertissement. Les artefacts `A144_PFX` générés pour ce test ont ensuite été retirés de `work/exports`.
