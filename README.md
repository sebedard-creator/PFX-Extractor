# 🎙️ PFX Extractor - Drive Bridge

**PFX Extractor** est une solution hybride (Local + Cloud GPU) conçue pour les professionnels de l'audio et du cinéma. Elle permet d'extraire automatiquement des effets sonores de production (PFX) et des ambiances à partir d'enregistrements bruts de tournage en utilisant des modèles d'intelligence artificielle de pointe (BS-RoFormer & MDX-Net).

Afin d'éviter d'avoir besoin d'un ordinateur surpuissant en local, cette application utilise une architecture "Drive Bridge" :
Une interface web locale très légère synchronise vos fichiers avec Google Drive, puis laisse les serveurs surpuissants de Google Colab faire le traitement lourd avant de rapatrier le résultat final.

---

## ✨ Fonctionnalités Principales

*   **Séparation de Sources Avancée** : Utilise les modèles IA (RoFormer et MDX23C) pour séparer avec une précision chirurgicale la voix des autres sons ambiants.
*   **Auto-Alignement Temporel** : Analyse et aligne automatiquement les pistes de micro-cravates (Lav) avec les pistes perches (Boom) à la milliseconde près avant le traitement.
*   **Préservation du Timecode (BWF)** : Réinjecte les métadonnées de Timecode originales dans les fichiers finaux pour que vos fichiers restent parfaitement synchronisés sur la ligne de temps de votre logiciel de montage.
*   **Pré-nettoyage Intelligent** : Applique un léger Noise Gate spectral non-destructif avant l'IA pour maximiser la clarté.
*   **Smart Cache & Fallback** : Le backend cloud est résilient. Il ignore automatiquement les fichiers 100% muets pour éviter les crashs, et peut reprendre un travail interrompu là où il s'est arrêté sans recommencer à zéro.
*   **Bilan Financier Intégré** : Calcule automatiquement l'équivalent monétaire en *Compute Units* dépensés à chaque passe sur Colab.

---

## 🏗️ Architecture "Drive Bridge"

1.  **L'Interface Locale (Gradio)** : Le script `app_local.py` tourne sur votre ordinateur. Vous y déposez vos fichiers bruts. L'application les synchronise vers Google Drive.
2.  **Le Backend Cloud (Colab)** : Le script `Colab_Backend_PFX_FINAL_26_Juin_v3.ipynb` s'exécute sur les serveurs GPU de Google. Il télécharge les bruts, extrait les PFX, et renvoie le tout sur Drive.
3.  **Le Rapatriement** : L'interface locale télécharge les fichiers traités depuis Drive et vous livre un fichier `.zip` propre contenant le résultat.

---

## 🚀 Installation & Prérequis

### 1. Prérequis
*   Python 3.10+ installé sur votre machine.
*   Un compte Google avec accès à Google Drive et Google Colaboratory.

### 2. Dépendances Locales
Clonez ce dépôt, puis installez les dépendances requises pour l'interface locale :
```bash
pip install -r requirements.txt
```

### 3. Clés d'API Google (OAuth)
Pour que l'application locale puisse écrire dans votre Google Drive :
1. Allez sur la [Google Cloud Console](https://console.cloud.google.com/).
2. Créez des identifiants OAuth 2.0 (Type "Application de bureau").
3. Téléchargez le fichier, renommez-le `credentials.json`, et placez-le à la racine de ce projet.

---

## 📖 Comment l'utiliser ?

1. **Démarrer l'interface locale** : Double-cliquez sur `start.bat` (ou lancez `python app_local.py`). L'interface s'ouvrira dans votre navigateur.
2. **Envoyer les fichiers** : Déposez vos pistes `.wav` dans l'interface et cliquez sur "Upload vers Google Drive".
3. **Lancer le Traitement IA** : Cliquez sur le bouton "Ouvrir Google Colab". Dans Colab, lancez toutes les cellules du notebook `Colab_Backend_PFX_FINAL_26_Juin_v4.ipynb`.
4. **Récupérer le résultat** : Une fois Colab terminé, retournez sur l'interface locale et cliquez sur "Télécharger les fichiers traités en ZIP".
5. **Nettoyer** : Utilisez le bouton rouge "Effacer la cache" pour vider votre Google Drive et préparer la prochaine session de travail.

---

## 🛠️ Configuration Avancée

*   **Changer de fichier Colab** : Si vous modifiez le notebook sur votre Drive, vous pouvez mettre à jour le lien d'accès directement via le menu "⚙️ Paramètres avancés" en bas de l'interface locale.
*   **Suivi des coûts** : À la fin de chaque exécution Colab, un log financier s'imprime pour vous indiquer le coût de traitement estimé de la session en cours.

---
*PFX Extractor v1.0 - 2026*  
*Conçu par Sébastien Bédard*
