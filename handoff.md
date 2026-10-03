# Handoff - PFX Extractor

## Date de session : 2026-10-03 — documentation consolidée

- V3.5.1 est la version courante. À la demande de l'utilisateur, les versions ne sont plus présentées comme des essais; l'historique reste dans changelog.md.
- L'utilisateur a supprimé les anciens notebooks et les guides par version. Le README et l'architecture contiennent les réglages et limites courants; les références aux guides supprimés ont été retirées, y compris dans l'en-tête Colab.
- Les tests backend chargent maintenant V3.5.1. Les comparaisons aux notebooks historiques absents ont été remplacées par des attentes explicites, sans reproduire artificiellement leur code. Suite complète : 39/39 réussis. Les anciens noms des fichiers de tests désignent leurs groupes de fonctionnalités, pas le notebook chargé.
- Les notes ci-dessous décrivent l'état à leur date; les mentions de fichiers anciens sont historiques.

## Date de session : 2026-10-03 — V3.5.1, mouvements de vêtements

- L'utilisateur rapporte une nette amélioration, tout en acceptant une finition humaine, puis demande +1,5 dB sur les mouvements/body foley/vêtements, hors body taps et footsteps.
- Nouveau notebook V3.5.1 : `GAIN_BODYTALK_DB=3.5` au lieu de 2.0. Même sélection 372/470/473/481, mêmes gardes et mêmes fonctions DSP. Le supplément réel dépend du masque, du veto et de la marge de crête; c'est un gain maximal.
- README, architecture et changelog actualisés. Retour au réglage V3.5.0 avec le slider à 2 dB. Les rendus existants ne changent pas rétroactivement; lancer le nouveau notebook pour une nouvelle sortie. Validation auditive avec ce gain encore à faire.
- Vérification locale : cellules DSP/orchestration identiques à V3.5.0, compilation valide, supplément mesuré de 1,5000 dB sur un masque maximal sans veto, exclusions footsteps/Tap/Thump/Slap, gardes et limite de crête vérifiées; retour bit-identique au gain 2 dB. Aucun nouveau rendu GPU.

## Date de session : 2026-09-23 — V3.5.0

- L'utilisateur juge la V3.4 insuffisante et fournit 15 repères humains. L'essai sur la sortie réelle confirme que l'amplification réservée à YAMNet rend plusieurs indices faibles plus détectables. Ne pas confondre scores et qualité auditive; absence de témoins foley seuls validés.
- Après accord : `Colab_Backend_PFX_V3_5_0.ipynb`, gain d'analyse local maximal +18 dB, fusion maximale avec scores initiaux, un seul retrait résiduel. Réglages/classes V3.4 inchangés. Réglages documentés dans l'architecture courante; anciens notebooks conservés à cette date.
- Préécoute approximative calculée avec le vrai modèle sous `work/diagnostic_mpm05/preview_v350`, sans relancer les séparateurs. Environ −20 dB supplémentaires sur sept repères, mais quasi aucun changement sur plusieurs autres, dont deux bruits de bouche. Rapport `verification.json`. Originaux inchangés; WAV d'écoute sans BWF, longueur de la sortie V3.3 fournie (un échantillon de moins que la référence V3.4).
- TC interprétés provisoirement à 23,976 i/s, nominal 24, origine début WAV. Confirmer la mention « 23.28 » avant analyse image par image. Run GPU complet et écoute utilisateur restent à faire. Tests dédiés `tests/test_backend_v350.py`; pas de changement frontend/API/dépendances applicatives.
- Validation locale : 39/39 tests réussis, dont 8 dédiés V3.5; `git diff --check` sans erreur. Les tests frontend simulent des échecs et en écrivent les messages dans le journal applicatif : ne pas les interpréter comme des incidents utilisateur.

## Date de session : 2026-09-23 — V3.4.0

- Diagnostic CPU réel sur le couple MPM_05_Boom-Gain_12 fourni : respiration beaucoup mieux classée après séparation vers 01:23; Sniff sous le seuil général vers 03:35. Scores et rapport sous `work/diagnostic_mpm05`.
- Après accord utilisateur : notebook V3.4.0, profil respiratoire élargi et seconde analyse humaine résiduelle avant bodytalk. Réglages documentés dans l'architecture courante; V3.3.0 conservée à cette date, retour exact par désactivation des deux ajouts.
- Préécoutes sous `work/diagnostic_mpm05/preview_v340` : résidus seuls et combinaison approximative basée sur la sortie V3.3 (pas un nouveau run complet des séparateurs). Longueur conservée, WAV d'écoute sans métadonnées BWF. Retrait mesuré ≈20 dB vers 01:23, ≈12,5 dB vers 03:35 dans la combinaison.
- Tests dédiés `tests/test_backend_v340.py`. Validation auditive et run Colab complet à faire. Diagnostic installé dans un environnement isolé sous `work/yamnet_diagnostic_env`; frontend/API inchangés.

---

## Date de session : 2026-09-22 — V3.3.0

- L'utilisateur confirme une amélioration avec V3.2.0; demande moins de becs/smacks et un peu plus de bodytalk.
- Nouveau notebook `Colab_Backend_PFX_V3_3_0.ipynb` : retrait buccal prioritaire 95 %, gain bodytalk maximal +2 dB avec veto humain/ambiant et marge avant saturation. Les seuils et limites du traitement courant sont documentés dans architecture.md.
- V3.2.0 et V3.1.2 intactes, aucun changement frontend/API. Les nouveaux contrôles à zéro retrouvent le traitement V3.2.0, testé bit-identique.
- Tests synthétiques reproductibles : `tests/test_backend_v330.py`. Ne pas confondre réussite des tests avec validation perceptive : premier traitement Colab V3.3.0 encore à faire.
- Résultat : 11/11 tests V3.3.0, 19/20 sur la suite complète. Échec préexistant du test frontend `test_download_builds_and_returns_protools_delivery` : il attend un appel sans argument, le code passe `progress=...`. `app_local.py` et son test sont inchangés depuis HEAD; correction hors de cet essai.

---

## Date de session : 2026-07-17 — V3.0

### Ce qui a été accompli
1. **Passage à V3.0** : le backend courant est renommé `Colab_Backend_PFX_V3_0.ipynb`; son en-tête et toute la documentation courante utilisent maintenant la même version.
2. **Refonte Production FX/YAMNet** : les 521 classes sont réparties par indices exacts entre conservation PFX, retrait humain, retrait d'ambiance, retrait hors-PFX, traitement contextuel et exclusion des masques directs. La recherche par sous-chaînes et le ducking piloté par maximum brut sont supprimés.
3. **Architecture multi-masques** : seuils et enveloppes propres aux humains, ambiances et sons hors-PFX; protection prioritaire des pas, vêtements, manipulations, props, impacts et outils; traitement temporel des animaux et tonalités.
4. **Robustesse structurelle** : validation des paramètres `audio-separator`, conventions de lag corrigées, rééchantillonnage explicite, redécoupage Snowball par clip source et conservation du timecode BWF.
5. **Revue des réglages par défaut** : le profil 58 % denoise adaptatif, 60 % RoFormer, overlap 12, 75 % humain, 70 % ambiance, 85 % hors-PFX et 70 % protection PFX est conservé comme point de départ équilibré; des plages recommandées sont documentées dans le notebook et le README.
6. **Livraison Pro Tools intégrée en un clic** : le bouton `Télécharger les fichiers traités en ZIP` de `app_local.py` récupère les WAV depuis Drive, puis appelle immédiatement `protools_export.py` et remet le ZIP autonome `.ptx` + `Audio Files`. Le bouton Pro Tools séparé a été retiré. L'adaptateur trie les sorties par filename, mappe au plus deux familles vers `PFX 01`/`PFX 02` et appelle le builder générique de `pt_api`. `requirements.txt` épingle désormais la release GitHub `v1.3.8`; `PT_API_PATH` et le dépôt frère restent des fallbacks de développement. La template native validée reste locale sous `template.ptx`; ce format propriétaire est ignoré par Git et doit être fourni séparément. Une autre template compatible et un nom de session restent optionnels.

### État actuel
- Le JSON du notebook est valide et les cellules Python principales compilent.
- La partition a été comparée à la grille finale : 521/521 classes, sans trou, chevauchement ni classe encore à arbitrer.
- Des tests synthétiques valident les seuils, les enveloppes, l'interpolation par blocs et la priorité de protection PFX.
- Les 9 tests unitaires du flux PTX passent, y compris le parcours combiné téléchargement → builder, l'absence de médias Drive, le nettoyage d'un build partiel et le non-écrasement d'une archive existante. L'interface Gradio se charge avec le bouton unique et résout automatiquement l'API depuis le dépôt frère.
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
