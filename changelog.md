# Changelog - PFX Extractor

## 2026-06-26
### Backend Colab (v4)
- **Ratio IA Dynamique** : Ajout d'un curseur (slider) dans la Cellule 1 pour contrôler finement la proportion de mixage entre BS-RoFormer et MDX23C (défaut: 50/50), permettant de privilégier la suppression vocale ou la préservation des textures.
- **Correctif CUDA** : Ajout d'une désinstallation/réinstallation forcée de `onnxruntime-gpu` pour pointer vers le dépôt spécifique CUDA 12, corrigeant l'erreur `libcudart.so.13` sur Google Colab.
- **Gestion des Silences (Fallback)** : Ajout d'un contrôle de sécurité dans `process_batch` pour contourner le plantage (`LibsndfileError`) causé par l'optimisation de `audio-separator` qui ignore les fichiers muets (bypass automatique de l'IA pour les fichiers silencieux).
- **Reprise après plantage (Smart Cache)** : Modification du script pour éviter de purger les fichiers IA temporaires et ignorer l'inférence des fichiers déjà traités si le script est relancé.
- **Bilan Financier (Cellule 7)** : Ajout d'un script de fin de traitement qui lit `/proc/uptime`, détecte le GPU alloué et calcule le coût estimé en Compute Units et en USD.

### Frontend Local (Drive Bridge)
- **Correctif Javascript (Bouton Colab)** : Résolution d'un bug où le bouton "Ouvrir Google Colab" ne se mettait pas à jour dynamiquement ou ouvrait un onglet vide après un changement d'URL. Implémentation d'un listener JS connecté à une variable d'état cachée pour un rechargement fiable à 100%.
- **Bouton Compute Units** : Ajout d'un bouton redirigeant vers la page d'achat de Compute Units Colab.
- **Paramètres Avancés** : Ajout d'un menu déroulant permettant de mettre à jour dynamiquement et de sauvegarder (`colab_link.txt`) le lien vers le notebook Colab sans avoir à modifier le code source.

### Documentation
- **architecture.md** : Création/Mise à jour complète reflétant l'architecture "Drive Bridge" actuelle et le nouveau nom du fichier Colab (`Colab_Backend_PFX_FINAL_26_Juin_v4.ipynb`).
