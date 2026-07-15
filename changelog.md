# Changelog - PFX Extractor

## 2026-07-14
### Backend Colab (V1.22 → V2.1)
- **Nouveau : Détecteur YAMNet indépendant** — Remplacement du sidechain V1.22 basé sur le stem "Vocals" de MDX23C/RoFormer, abandonné après confirmation sur du matériel réel que les modèles de séparation ne détectent quasiment aucune trace vocale sur un soupir, un cri ou un chant — angle mort inhérent à des modèles entraînés pour de la musique. Intégration de YAMNet (classificateur d'événements sonores, 521 classes AudioSet), qui tourne sur l'audio fusionné brut avant tout traitement. Les classes retenues sont sélectionnées par correspondance de mots-clés sur la vraie taxonomie du modèle et imprimées dans les logs pour audit avant tout traitement de fichier.
- **Nouveau : Protection Bodytalk** — Le même détecteur identifie les classes liées au mouvement physique (ex. *Walk, footsteps*) pour restaurer le signal brut à ces endroits pendant le pré-denoise, évitant que le nettoyage n'attaque le bodytalk légitime.
- **Nouveau : Anti-pumping** — `DENOISE_ADAPTATIF` (profil de bruit non-stationnaire, mieux adapté aux scènes extérieures variables — vent, trafic) et `AI_OVERLAP` (chevauchement des segments d'inférence relevé, masque de séparation plus lissé dans le temps) ajoutés au panneau de contrôle pour cibler le pumping observé sur les scènes bruyantes.
- **Correctif : défaut `RATIO_ROFORMER`** — Le défaut (0.50) ne correspondait pas à la recommandation déjà documentée dans le panneau de contrôle lui-même ("0.60 = Favorise RoFormer, recommandé pour PFX"). Corrigé à 0.60.
- **Correctif : garde-fou de confiance sur `initial_mic_alignment`** — Le regroupement par "take" se fait sur le dernier nombre trouvé dans le nom de fichier, ce qui peut faire collisionner deux prises non-apparentées si leurs noms partagent le même suffixe numérique final. Dans ce cas, le code tentait d'aligner les deux clips par corrélation croisée malgré l'absence de rapport réel, produisant un fichier corrompu. Un score de confiance normalisé est maintenant calculé après chaque corrélation ; en dessous du seuil (`ALIGNMENT_CONFIDENCE_MIN = 0.15`), l'alignement est ignoré et le clip est copié tel quel, avec avertissement en log.
- **Ajouté puis retiré : version de comparaison A/B** — `GENERER_VERSION_COMPARAISON` a brièvement généré une paire de fichiers par clip (`_PFX_Ready.wav` + `_PFX_Ready_NoDuck.wav`) pour comparer l'effet du duck directement dans Pro Tools. Retiré à la demande de l'utilisateur une fois son utilité de test épuisée — chaque clip produit de nouveau un seul fichier de sortie.
- **Retiré : sauvegarde du stem Vocals dans `process_batch`** — Redevenue inutile une fois le sidechain YAMNet en place (indépendant du split vocal/instrumental) ; `process_batch` ne conserve à nouveau que le stem Instrumental.
- **Renommage de fichier** : `Colab_Backend_PFX_FINAL_26_Juin_v4.ipynb` → `Colab_Backend_PFX_V2.1_YAMNet.ipynb`. La convention de version passe d'un suffixe date (`_FINAL_26_Juin_vX`) à un numéro sémantique (`V2.1`).

### Documentation
- **`README.md`** : Traduction complète en anglais, avec note en tête de fichier précisant que le code et la documentation inline restent en français. Ajout d'un tableau de référence du panneau de contrôle Colab et d'une section "What's New" (changelog condensé). Correctif au passage : le README référençait deux noms de fichiers Colab différents (`_v3`/`_v4`) selon la section ; uniformisé vers le nom de fichier réel actuel.
- **`architecture.md`** : Mis à jour — `dsp_local.py` marqué formellement déprécié (confirmé inutilisé), nouvelle entrée dédiée pour le détecteur YAMNet, description du backend Colab étoffée, garde-fou d'alignement documenté, version du document passée à v2.1.
- **`handoff.md`** : Nouvelle entrée de session ajoutée (voir document séparé).

---

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
