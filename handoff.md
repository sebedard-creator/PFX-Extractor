# Handoff - PFX Extractor

## Date de session : 2026-07-17 — V3.0

### Ce qui a été accompli
1. **Passage à V3.0** : le backend courant est renommé `Colab_Backend_PFX_V3_0.ipynb`; son en-tête et toute la documentation courante utilisent maintenant la même version.
2. **Refonte Production FX/YAMNet** : les 521 classes sont réparties par indices exacts entre conservation PFX, retrait humain, retrait d'ambiance, retrait hors-PFX, traitement contextuel et exclusion des masques directs. La recherche par sous-chaînes et le ducking piloté par maximum brut sont supprimés.
3. **Architecture multi-masques** : seuils et enveloppes propres aux humains, ambiances et sons hors-PFX; protection prioritaire des pas, vêtements, manipulations, props, impacts et outils; traitement temporel des animaux et tonalités.
4. **Robustesse structurelle** : validation des paramètres `audio-separator`, conventions de lag corrigées, rééchantillonnage explicite, redécoupage Snowball par clip source et conservation du timecode BWF.
5. **Revue des réglages par défaut** : le profil 58 % denoise adaptatif, 60 % RoFormer, overlap 12, 75 % humain, 70 % ambiance, 85 % hors-PFX et 70 % protection PFX est conservé comme point de départ équilibré; des plages recommandées sont documentées dans le notebook et le README.
6. **Livraison Pro Tools intégrée** : `app_local.py` expose maintenant `Créer la session Pro Tools`. Le nouveau `protools_export.py` trie les sorties par filename, mappe au plus deux familles vers `PFX 01`/`PFX 02`, appelle le builder générique de `pt_api` 1.3.8+ et remet un ZIP autonome. La template native validée reste locale sous `template.ptx`; ce format propriétaire est ignoré par Git et doit être fourni séparément. Une autre template compatible et un nom de session restent optionnels.

### État actuel
- Le JSON du notebook est valide et les cellules Python principales compilent.
- La partition a été comparée à la grille finale : 521/521 classes, sans trou, chevauchement ni classe encore à arbitrer.
- Des tests synthétiques valident les seuils, les enveloppes, l'interpolation par blocs et la priorité de protection PFX.
- Les 6 tests unitaires du nouvel adaptateur PTX passent, y compris le nettoyage d'un build partiel et le non-écrasement d'une archive existante. L'interface Gradio se charge avec les nouveaux contrôles et résout automatiquement l'API depuis le dépôt frère.
- Un test intégré sur les 62 fichiers réels de `work/processed` a produit une livraison `A144_PFX`. Le parseur de l'API a confirmé 62 médias, clips et placements sur `PFX 01`; les 62 WAV étaient bit-identiques, tous les timestamps/durées correspondaient aux BWF, les index allaient de 0 à 61, les 27 overlaps faisaient exactement un échantillon, le ZIP passait son CRC et une sauvegarde no-op était bit-perfect.
- **Validation Pro Tools réussie** : la session générée s'est ouverte et lue normalement; le Save As, la fermeture et la réouverture ont également fonctionné sans avertissement. Les artefacts temporaires `A144_PFX` ont ensuite été retirés de `work/exports` et sont récupérables depuis la Corbeille si nécessaire.
- **Non testé sur GPU réel** : la V3.0 doit encore effectuer un traitement complet dans Colab sur du matériel de tournage représentatif.

### Prochaine validation recommandée
- Tester un batch comprenant voix/soupirs, pas et vêtements, props/impacts, trafic, météo, musique/TV, véhicule, animal ponctuel et ambiance animale diffuse.
- Examiner les logs `Top YAMNet`, les pourcentages de masques actifs et `YAMNet DIAG`, puis écouter les transitions et la préservation des transitoires.
- Ajuster d'abord dans les plages documentées; ne modifier les seuils internes qu'après plusieurs prises représentatives.

---

## Date de session : 2026-07-14

### Ce qui a été accompli
1. **Diagnostic et abandon du sidechain V1.22 (stem Vocals)** : Confirmé avec l'utilisateur que MDX23C/RoFormer ne détectent essentiellement aucune trace vocale sur les soupirs/cris/vocalisations non-lexicales (le stem Vocals était vide à ces endroits) — l'approche de ducking basée sur ce stem était un cul-de-sac. Diagnostic instrumenté (logs `🔍 DUCK DIAG`) avant confirmation par l'utilisateur.
2. **Refonte V2.0 — Détecteur YAMNet indépendant** : Remplacement complet du sidechain par un classificateur d'événements sonores (YAMNet, 521 classes AudioSet) tournant sur l'audio fusionné brut, indépendamment du split vocal/instrumental. Deux usages : ducking anti-vocalisation sur le mix final + protection bodytalk (footsteps/tissu) pendant le pré-denoise. Sélection de classes par mots-clés avec audit imprimé dans les logs plutôt qu'une liste codée en dur.
3. **Refonte V2.0 — Anti-pumping** : Ajout de `DENOISE_ADAPTATIF` (profil de bruit non-stationnaire) et augmentation de `AI_OVERLAP` pour cibler le pumping rapporté sur les scènes extérieures bruyantes.
4. **Correctif V2.1 — Bug de regroupement des prises** : Diagnostiqué et confirmé (via simulation du regex sur les vrais noms de fichiers de l'utilisateur) que `initial_mic_alignment` peut regrouper des prises non-apparentées si leurs noms de fichiers partagent le même suffixe numérique final, causant un alignement forcé sans rapport réel. Cause identifiée comme une erreur de manipulation ponctuelle côté utilisateur pour ce cas précis, mais garde-fou de confiance normalisé ajouté quand même en prévention (`ALIGNMENT_CONFIDENCE_MIN`).
5. **Nettoyage V2.1** : Retrait de la fonctionnalité de version de comparaison A/B (`GENERER_VERSION_COMPARAISON`), devenue inutile après la phase de test.
6. **Documentation** : `README.md` traduit en anglais et étoffé (fonctionnalités complètes, tableau du panneau de contrôle, section "What's New"). `dsp_local.py` confirmé inutilisé et formellement marqué déprécié dans `architecture.md`. `changelog.md` et le présent `handoff.md` mis à jour.

### État actuel
- Le notebook Colab est maintenant à la version **V2.1** (`Colab_Backend_PFX_V_2_1.ipynb`) — toutes les cellules compilent, le JSON du notebook est valide, et le contenu a été vérifié (présence du garde-fou d'alignement, absence de toute trace de la fonctionnalité de comparaison retirée).
- **⚠️ Non testé sur GPU réel** : les changements de cette session (YAMNet, protection bodytalk, anti-pumping, garde-fou d'alignement) n'ont pas encore été validés sur un vrai run Colab avec du matériel de tournage. Seules des vérifications statiques (compilation, structure JSON, simulation de regex) ont été faites.
- La liste `BODYTALK_CLASS_IDX` n'est confirmée fiable que pour la classe *"Walk, footsteps"* — les autres mots-clés (rustle, cloth, zipper, fabric) n'ont pas pu être vérifiés avec certitude contre la taxonomie exacte de YAMNet et pourraient ne matcher aucune classe réelle. Le notebook imprime un avertissement explicite si la liste s'avère vide.

### Bugs connus
- Aucun bug bloquant confirmé sur du matériel réel — à valider au premier run V2.1.
- Risque documenté (pas un bug confirmé) : `BODYTALK_CLASS_IDX` pourrait être vide ou trop courte si les mots-clés ne matchent pas la taxonomie YAMNet exacte.

### Prochaines étapes suggérées
- Rouler `Colab_Backend_PFX_V_2_1.ipynb` sur un vrai batch de tournage (idéalement incluant une scène avec soupir/cri clair ET une scène extérieure bruyante) et vérifier :
  - les classes imprimées par le détecteur YAMNet (Cellule 5) — confirmer que `BODYTALK_CLASS_IDX` n'est pas vide ;
  - les logs `🔍 DUCK DIAG` et `👟 Protection bodytalk` pour confirmer que le duck et la protection s'activent réellement sur du vrai contenu ;
  - à l'oreille, si le pumping sur scènes extérieures est réduit par rapport à la V1.x.
- Si YAMNet s'avère insuffisant sur les sons subtils (soupirs, toux), explorer un modèle spécialisé de type VocalSound plutôt qu'un classificateur générique AudioSet.
- Si la V2.1 est validée, envisager d'harmoniser la convention de version à travers tout le projet (le notebook est passé de `_FINAL_26_Juin_v4` à `V2.1` ; vérifier si `app_local.py`/`drive_auth.py` devraient suivre la même convention).

---

## Date de session : 2026-06-26

### Ce qui a été accompli
1. **Stabilisation majeure du backend Colab** : Le script cloud (`Colab_Backend_PFX_FINAL_26_Juin_v4.ipynb`) a reçu plusieurs correctifs critiques : compatibilité forcée CUDA 12 pour `onnxruntime-gpu`, système anti-crash pour les fichiers audio vides, et logique de reprise (skipping des fichiers déjà traités). Un calculateur de coût de session (Compute Units/USD) a également été ajouté à la fin du traitement. Un slider de ratio dynamique (RoFormer/MDX23C) a été implémenté.
2. **Amélioration UI du Drive Bridge** : Le service local Gradio (`app_local.py`) possède maintenant un menu de configuration permettant à l'utilisateur de modifier et de persister le lien du notebook Colab via l'interface, résolvant le problème des changements d'ID de fichier sur Google Drive.
3. **Mise en conformité documentaire** : Le fichier d'architecture a été mis à jour et renommé correctement (`architecture.md`). Un `changelog.md` a été initié.

### État actuel
- Le système "Drive Bridge" (Upload local -> Traitement Colab -> Download ZIP) est entièrement fonctionnel, robuste contre les plantages ponctuels de Colab, et synchronisé avec le dernier fichier Colab `v4`.
- Tous les bugs rapportés aujourd'hui (Erreur d'importation CUDA, Erreur Libsndfile) sont résolus.

### Bugs connus
- Aucun bug critique identifié à ce stade.

### Prochaines étapes suggérées
- Faire une passe de traitement complète (A à Z) sur un vrai batch de fichiers complexes pour valider l'expérience utilisateur et les logs financiers.
- Si le système est validé, on pourra passer à de futures optimisations du pipeline de "denoise" ou à des améliorations d'interface (ex: barre de progression Drive).
