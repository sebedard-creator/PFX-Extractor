# Changelog - PFX Extractor

## Unreleased

### Progression du nettoyage des caches (2026-10-13)

- Le bouton de confirmation transmet la progression Gradio : connexion/inventaire Drive, fichiers supprimés, puis nettoyage local. Noms, compteurs et bilan des erreurs affichés; la barre couvre les deux phases.
- Suppression locale détaillée fichier par fichier dans les caches ciblés, avec maintien des dossiers racines, refus hors périmètre et traitement des liens sans suivre leur cible. Un fichier verrouillé est signalé; le nettoyage poursuit les autres éléments.
- Périmètre Drive inchangé : fichiers à la racine des dossiers de travail; anciennes générations conservées. Aucun cache utilisateur réel supprimé pendant la vérification, tests locaux en répertoires temporaires et Drive simulé.

### Progression de l'upload Drive (2026-10-13)

- Le bouton Upload transmet désormais l'objet de progression Gradio à Drive, comme le téléchargement ZIP. Affichage du fichier en cours, du pourcentage transféré et du nombre de fichiers envoyés.
- Upload reprenable par blocs de 8 Mo, avec trois reprises pour les erreurs prises en charge par le client Google. Les échecs restent séparés des fichiers envoyés; fermeture des handles après chaque transfert.
- Tests simulés de progression intermédiaire, compteur final, poursuite après échec et branchement du callback frontend; aucun upload réel requis pour ces tests.

### Noms explicites des backends utilisables (2026-10-12)

- Deux variantes distribuées au choix : `Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb` et `Colab_Backend_PFX_Bandit_V4.ipynb`. Bandit quitte la désignation « Test »; modèles, DSP et réglages inchangés. Nouveau label de manifeste Bandit_V4, protocole2 identique et anciens lots compatibles.
- Ancien `Colab_Backend_PFX_Vtest_V3.ipynb` conservé sur disque mais retiré du suivi Git et ajouté à .gitignore. Les tests de référence peuvent reconstruire son moteur depuis les sources conservées si ce notebook privé est absent.
- Documentation et liens des deux backends actualisés; même sélection Colab et même bouton ZIP/PTX.

### Version minimale Pro Tools API 1.6.2 (2026-10-12)

- Dépendance épinglée au tag `v1.6.2` (commit `e0a7cb6ab645ee1a763ecea875f88344c496868d`), installée dans `.venv`. Le resolver refuse toute version inférieure à **1.6.2**, quelle que soit la source (paquet installé, `PT_API_PATH`, dépôt frère); les versions stables supérieures sont acceptées.
- Messages et documentation actualisés. Tests des bornes de version et d'une vraie livraison synthétique à 131 clips, avec contrôle de l'ordre chronologique des événements sérialisés malgré les noms triés alphabétiquement.
- Le correctif de playlist est fourni par la nouvelle release de l'API; aucun changement dans son dépôt ni dans les notebooks Colab. Redémarrer le frontend pour charger le nouveau paquet et le nouveau garde-fou.

### Dépendance Pro Tools API 1.6.1 (2026-10-12)

- `requirements.txt` épingle `pt_api` au tag GitHub `v1.6.1`, commit `8c91eb9e82d03bbaf629c901cc68a730fd96b046`, au lieu de `v1.3.8`. Paquet installé dans l'environnement local du frontend pour le prochain comparatif.
- Le resolver exige au minimum 1.6.1, y compris via `PT_API_PATH` ou dépôt frère, et consigne version/chemin réellement chargés. Une API ancienne est refusée explicitement; priorité de résolution conservée.
- Vérification de construction/relecture PTX synthétique avec l'API installée. Le problème utilisateur de timeline parfois incomplet reste à vérifier sur son lot réel après redémarrage du frontend. Aucun changement des traitements Colab ni du dépôt de l'API.

### Test V4 — Bandit et retrait humain cumulatif (2026-10-06)

- Nouvelle copie `Colab_Backend_PFX_Bandit_V4.ipynb`, avec sources embarquées `backend_test/v4_processing.py` et `backend_test/v4_workflow.py`. Test V3 et V3.5.2 conservées.
- Même séparation Bandit, pré-nettoyage 40 %, détection résiduelle avec gain maximal +18 dB, bodytalk maximal +4 dB et scènes indépendantes. La finition utilise les masques du brut sur les SFX, puis analyse le rendu déjà atténué et applique un deuxième retrait cumulatif, comme le principe de V3.5.2.
- Maximum entre catégories au premier retrait, puis multiplication des deux passes : 95 % et 90 % peuvent atteindre environ −46 dB si les deux détections sont maximales. Le bodytalk est relevé une seule fois après le cumul, avec les veto et la marge locale de Test V3. Coût possible : perte accrue de Foley simultané.
- Workflow ZIP/PTX et protocole 2 commun inchangés; aucune manipulation Drive en changeant de notebook. UMID uniques, N/TC/empreintes vérifiés, anciennes générations conservées, erreur de détecteur bloquante. Aucun changement dans pt_api.
- Tests synthétiques du cumul et de l'ordre des analyses, des zones temporelles, bodytalk, désactivation des résidus, puis workflow avec IA simulée et export FFmpeg réel. La qualité auditive sur le projet sera évaluée par l'utilisateur dans Colab.

### V3.5.2 — rétroportage UMID sur V3.5.1 (2026-10-06)

- Nouveau `Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb`; V3.5.1 conservée à l'identique. Modèles, fonctions DSP, YAMNet et gain bodytalk (+3,5 dB) conservés. À la demande de l'utilisateur, pré-nettoyage par défaut abaissé de 58 % à 40 %, comme Test V3; autres réglages inchangés.
- Exclusion de l'UMID du transfert FFmpeg, écriture binaire d'un nouvel identifiant UUID4 par rendu; contrôle du hash audio avant/après, relecture, unicité du lot et non-réutilisation des identités sources. Helpers identiques à ceux validés pour Test V3.
- Export dans un fichier temporaire; FFmpeg doit réussir et les contrôles UMID passer avant remplacement du WAV final. Une erreur conserve le précédent fichier de destination.
- Bascule automatique V3.5.2 ↔ Test V3 : protocole 2 commun, dossier par génération et pointeur running/failed/complete. Aucune manipulation manuelle du manifeste. Les anciens résultats sont conservés; les runs incomplets ou remplacés ne sont pas publiés.
- DSP historique conservé, dont alignement/Snowball, sans modification de pt_api. La livraison vérifie durées, TC, empreintes et UMID; normalisation du seul fmt WAV si nécessaire. Tests de bascule des deux notebooks, modèle en échec, lot incomplet et concurrence, avec IA simulée; export FFmpeg réel et parité DSP vérifiés. Validation auditive Colab non effectuée localement.

### Test V3 — correction des collisions UMID (2026-10-06)

- Défaut reproduit sur le lot réel : 63 WAV partageaient un UMID altéré. Le premier média silencieux de 8 s 6 images explique les clips tronqués/silencieux; la somme avec cette limitation correspond exactement aux 26:09:16 observées.
- UMID retiré du transfert de métadonnées FFmpeg, nouvel identifiant par rendu écrit en binaire dans le BWF. Contrôle de l'identité et du chunk audio avant/après. Durée, timecode et DSP inchangés.
- Manifeste protocole 2 avec UMID sources/sorties, unicité et interdiction de réutiliser les identités sources. Frontend refuse les collisions dans les WAV réels, avant API et après copie vers Audio Files. L'API n'a pas été modifiée.
- 88 tests réussis : débordement signé, collisions, conservation audio/TC, unicité entre runs, manifeste et refus avant API. Anciennes livraisons conservées; aucune réparation de fichiers utilisateur effectuée. Recharger Test V3 et redémarrer le frontend; validation d'import en session Pro Tools neuve à effectuer.

### Test V3 — scènes indépendantes et cinq points d'audit (2026-10-05)

- Nouveau `Colab_Backend_PFX_Vtest_V3.ipynb`, anciens notebooks conservés. Pré-nettoyage 40 % après comparaison utilisateur; aucun alignement BOOM/LAV ni fusion entre scènes.
- Retrait YAMNet sur le SFX de Bandit; observation résiduelle du même signal non atténué, profondeurs combinées par maximum. Plus de cumul brut × résidu.
- Bodytalk +4 dB maximum avec marge locale et veto pas/impacts détectés; gain temporel, pas séparation parfaite des vêtements.
- Livraison par génération complète avec manifeste, empreintes SHA-256, durées et TC. Frontend refuse les lots incomplets/corrompus/changés et conserve la précédente copie locale. Redémarrage frontend nécessaire; bouton ZIP/PTX inchangé. Retour aux notebooks historiques après V3 : archiver/retirer explicitement le manifeste racine. Les générations ne sont pas automatiquement purgées.
- Validation anticipée des entrées BWF/mono48k, noms BOOM/LAV libres et limites PTX. Export V3 mappé par microphone, sans obligation de préfixes ou numérotation identiques.
- Validation complétée le 6 octobre : normalisation compatible du seul en-tête float32 des rendus FFmpeg, sans modification des échantillons ni du BWF. Test d’export réel à 1483482 samples et TC 1823255434.
- 83 tests réussis, dont construction/relecture PTX réelle sur audio synthétique. API inchangée. Pas de garantie sur la qualité auditive ni de correctif confirmé pour les neuf images supplémentaires après import dans la timeline utilisateur.

### Vtest sans pré-nettoyage (2026-10-05)

- Variante séparée `Colab_Backend_PFX_Vtest_sans_prenettoyage.ipynb`, avec contournement complet du pré-denoise : lecture directe des WAV alignés/regroupés par Bandit, sans filtrage ni restauration brute préalable. Pas seulement un slider à zéro.
- Analyse YAMNet brute, finition, retrait pleurs, gain bodytalk +4 dB et workflow ZIP/PTX inchangés. Vtest à 58 % et V3.5.1 conservées. Variante identifiée dans le manifeste; sauvegarder la première livraison avant le second run.
- 69 tests locaux réussis, dont vérification des échantillons transmis à Bandit et export BWF. Effet audible à comparer dans Colab; aucune amélioration garantie.

### Vtest — renfort ciblé des pleurs (2026-10-05)

- À la demande de l'utilisateur, gain bodytalk maximal par défaut porté de +3,5 à +4 dB dans Vtest seulement. Même sélection de mouvements, mêmes veto humain/ambiant et limite de crête; le supplément effectif dépend du masque et de la marge disponible. Tests du supplément +0,5 dB, de l'application unique et de la limite de crête.
- Après comparaison favorable de l'utilisateur : retrait prioritaire des pleurs/sanglots/gémissements (classes YAMNet 19–22), slider 95 %, renfort dans les résidus et veto du gain bodytalk. Aucun changement de Bandit, du workflow ou de V3.5.1. Réglage 0 pour désactiver les deux ajouts ciblés.
- Tests dédiés de ciblage, désactivation et protection contre le boost. Vérification du découpage avec queue artificiellement trop longue : longueurs source préservées. Incident des trois clips longs non reproduit, cause inconnue sans fichiers ou manifeste; aucun raccourcissement arbitraire appliqué.

### Comparatif Vtest — Bandit v2 dans Colab (2026-10-03)

- Notebook autonome `Colab_Backend_PFX_Vtest.ipynb`; V3.5.1 de production conservée sans modification.
- Séparation remplacée par le SFX de Bandit v2 multilingue officiel / DnR v3. Aucun MVSEP, aucune API de traitement externe; ce n'est pas DnR-nonverbal. Finition YAMNet et réglages bodytalk/denoise conservés.
- Sources épinglées, poids vérifiés, preflight réel, échecs sans bypass; reconstruction mono 48 kHz à durée exacte et timecodes BWF conservés.
- Workflow identique à V3.5.1 : WAV dans `2_Environnements_IA`, puis bouton ZIP/PTX habituel du frontend. Dossier de comparaison séparé retiré à la demande de l'utilisateur; conserver la première livraison avant que le prochain run remplace les WAV de même nom. Manifeste hors livraison dans la cache modèle; aucun ZIP Colab séparé. Aucun changement frontend, pt_api ou requirements locaux.
- Tests de reconstruction, appels réseau du runtime, cohérence notebook/runtime, référence inchangée et export BWF réel ajoutés. Qualité auditive et exécution T4 à confirmer sur le projet de comparaison.

### Documentation et entretien du dépôt (2026-10-03)

- V3.5.1 présentée comme version courante; les versions évolueront au fil des améliorations, sans statut « essai ».
- Anciens notebooks et guides par version retirés du dossier de travail par l'utilisateur. Historique conservé ici; contrôles et limites regroupés dans README et architecture. Liens obsolètes retirés.
- Tests backend adaptés au notebook courant pour fonctionner sans les versions supprimées. Les comparaisons interversions ont été remplacées par des vérifications explicites de désactivation et de gain; elles ne prétendent plus comparer des sources historiques absentes.

### Backend V3.5.1 — gain des mouvements de vêtements (2026-10-03)

- Gain bodytalk maximal par défaut porté de +2 à +3,5 dB à la demande de l'utilisateur, après son retour positif sur V3.5.0.
- Mêmes déclencheurs zipper/frottements/froissements; footsteps, taps et impacts ne déclenchent pas ce gain. Gardes humaines/ambiantes, marge de crête et détection des résidus conservées.
- Nouveau notebook `Colab_Backend_PFX_V3_5_1.ipynb`. Retour au gain V3.5.0 à réglages identiques avec bodytalk à 2 dB; aucune étape de calcul supplémentaire.

### Backend V3.5.0 — détection résiduelle à deux niveaux

- Nouveau notebook autonome, V3.4 intacte. Gain d'analyse local maximal +18 dB par défaut, limité en crête et réservé au classificateur; aucune amplification du rendu.
- Fusion maximale des scores initiaux/amplifiés avant un seul retrait résiduel; groupes et seuils V3.4 conservés. Gain nul pour retrouver V3.4, profondeur résiduelle nulle pour sauter l'analyse secondaire.
- Tests dédiés et préécoute locale sur les repères utilisateur. Retrait supplémentaire mesuré sur plusieurs voix/soupirs; plusieurs bruits de bouche restent peu affectés. Amélioration à l'écoute confirmée par l'utilisateur le 3 octobre; une finition humaine reste nécessaire.

### Backend V3.4.0 — respirations et résidus humains
- Groupe prioritaire élargi à Sniff, Snort, Gasp et Pant, activation plus sensible et plus forte aux scores intermédiaires.
- Seconde détection YAMNet sur le mix déjà atténué, ciblée sur les résidus humains, avant le gain bodytalk. Réglage indépendant à 90 %; aucune nouvelle séparation MDX/RoFormer.
- Nouveau notebook autonome, V3.3.0 intacte à cette date. Profil renforcé désactivé et résidus à zéro : comportement V3.3.0 exact. Tests dédiés et préécoutes locales sur la scène fournie; l'utilisateur a ensuite jugé le retrait insuffisant, motivant V3.5.0.

### Local Drive Bridge — transfert vers Pro Tools
- Correctif : l'objet de progression Gradio n'est plus évalué comme un booléen pendant les uploads, téléchargements ou effacements Drive. Sur certains callbacks, cette évaluation appelait `__len__` sur une liste vide et interrompait le téléchargement avec `list index out of range` avant la création PTX.
- Couverture ajoutée : simulation de ce comportement Gradio, téléchargement Drive de bout en bout avec progression, et mise à jour du test d'intégration du bouton de livraison.

## 2026-09-22
### Backend V3.3.0 — bruits de bouche et gain bodytalk
- Nouveau notebook autonome `Colab_Backend_PFX_V3_3_0.ipynb`; V3.2.0 et V3.1.2 conservées intactes.
- Retrait buccal prioritaire à 95 % : indices buccaux directs et clics/smacks/pops uniquement avec contexte humain proche, marge temporelle pour les amorces de phrase.
- Gain bodytalk jusqu'à +2 dB, freiné par les indices indésirables et limité par la marge avant saturation; pas de restauration brute supplémentaire ni de boost explicite des footsteps.
- Deux contrôles indépendants; tous deux à zéro rendent le traitement V3.2.0. Partition YAMNet, séparation, fichiers/timecodes et frontend/PTX inchangés.
- Tests DSP synthétiques reproductibles dans `tests/test_backend_v330.py`; validation auditive Colab encore requise à cette date.

## 2026-09-10
### Backend V3.2.0 — souffles et chuchotements
- Masque prioritaire Whispering / Sigh / Breathing, seuil 0,10–0,30 et retrait à 95 % sans veto PFX. Nouveau notebook séparé de V3.1.2 à cette date.
- Amélioration à l'écoute rapportée par l'utilisateur le 22 septembre; bruits de bouche résiduels motivant V3.3.0.

## 2026-08-17
### Backend Colab V3.1.2 — fiabilité de préparation et appariement des microphones
- **Prévol et cache persistant des modèles** — MDX23C, BS-RoFormer et leurs YAML sont validés avant toute purge ou analyse audio, puis conservés dans `PFX_Extractor/0_Model_Cache` sur Drive. Une ressource indisponible échoue donc immédiatement, et non après le calcul du batch.
- **WAV ultra-courts importables** — Les rendus inférieurs à 1024 échantillons reçoivent un court padding de silence avant l'ancrage BWF; le fichier de sortie est ensuite contrôlé afin d'éviter un WAV vide refusé par `pt_api`.
- **Appariement séquentiel Boom/Lav** — Les numéros internes des deux micros ne sont plus comparés. Les listes `BOOM` et `LAV` sont triées naturellement et associées par position; leurs comptes doivent être égaux. Les sidecars macOS `._*.wav` sont exclus de l'ingestion.
- **Version du notebook** — `Colab_Backend_PFX_V3_1_2.ipynb` remplace la révision V3.1.1 non publiée.

---

## 2026-07-17
### Backend Colab V3.0 — refonte Production FX
- **Partition exacte 521/521** — Suppression de la sélection par sous-chaînes, qui pouvait confondre des classes comme `Hum`/`Humming` ou produire des faux positifs avec `run`. Les indices YAMNet sont maintenant répartis dans six groupes non chevauchants, avec assertions sur les comptes attendus.
- **Masques indépendants** — Ajout de masques distincts pour les humains, les ambiances, le contenu hors PFX et la protection PFX. Chaque masque possède ses propres seuils doux et constantes d'attaque/relâchement; le maximum brut des scores ne pilote plus directement le gain.
- **Politique Production FX** — Retrait de la musique, TV/radio, véhicules, sirènes, nature/météo et graves/vibrations; conservation des PFX de plateau; animaux et tonalités arbitrés automatiquement par persistance; classes de contexte exclues des courbes de gain.
- **Protection et mémoire** — La protection PFX est appliquée au pré-denoise et comme veto pondéré sur les retraits, avec restauration brute plafonnée à 90 %. Les masques sont conservés au pas YAMNet et interpolés par blocs de 30 secondes pour les longues prises.
- **Nouveaux contrôles** — `DUCK_DEPTH_HUMAIN`, `DUCK_DEPTH_AMBIANCE`, `DUCK_DEPTH_HORS_PFX` et `PROTECTION_PFX` remplacent les anciens contrôles vocalisation/bodytalk.
- **Revue des défauts V3.0** — Les valeurs 58 % denoise adaptatif, 60 % RoFormer, overlap 12, 75 % humain, 70 % ambiance, 85 % hors-PFX et 70 % protection PFX sont conservées comme profil équilibré. Les plages de départ et les atténuations maximales résultantes sont maintenant documentées.
- **Reproductibilité du denoise** — `noisereduce` est figé à la version 3.0.3 afin que la force de réduction et le mode adaptatif gardent la même sémantique d'un lancement Colab à l'autre.
- **Robustesse du pipeline** — Validation explicite des paramètres `audio-separator`, correction des conventions de lag, rééchantillonnage contrôlé des stems et des fusions, et redécoupage Snowball fiable vers chaque clip source avec son timecode BWF.
- **Passage à V3.0** — Le notebook est renommé `Colab_Backend_PFX_V3_0.ipynb`; son en-tête, le README, l'architecture et le handoff sont harmonisés sur la nouvelle version majeure.

### Frontend local V3.0 — livraison Pro Tools
- **Téléchargement et assemblage PTX en un clic** — Le bouton existant `Télécharger les fichiers traités en ZIP` récupère maintenant les WAV depuis Drive, les transforme immédiatement en livraison autonome `.ptx` + `Audio Files`, puis télécharge le ZIP Pro Tools. Le bouton séparé `Créer la session Pro Tools` est retiré comme redondant et aucun ZIP WAV intermédiaire n'est créé par le frontend.
- **Adaptateur applicatif générique** — Nouveau module `protools_export.py`. Il applique uniquement la convention de PFX Extractor (`<famille>-Gain_<numéro>_PFX_Ready.wav`), l'ordre alphabétique et l'affectation maximale à `PFX 01`/`PFX 02`, tandis que toute mutation binaire demeure déléguée à l'API générique `pt_api` 1.3.8+.
- **Template validée locale** — Le frontend utilise par défaut un `template.ptx` natif mono 48 kHz/23,976 à deux pistes placé à la racine. Ce format propriétaire est exclu par `.gitignore` et doit être fourni séparément; une autre template compatible et un nom de session peuvent être sélectionnés dans les paramètres avancés.
- **Dépendance API reproductible** — `requirements.txt` installe maintenant `pt_api` depuis le tag GitHub immuable `v1.3.8`, validé sur le commit `ac97994`. La résolution par `PT_API_PATH` ou dépôt frère reste disponible uniquement comme fallback de développement.
- **Livraison sûre** — Les exports existants ne sont jamais écrasés; les échecs retirent le nouveau dossier incomplet et ne publient aucun ZIP partiel. Le nettoyage local inclut déjà `work/exports` et couvre donc aussi les sessions générées.
- **Validation complète sur sortie réelle** — Construction réussie à partir de 62 WAV (`A144_Boom`) : 62 hashes audio identiques, 62 entrées de catalogue/clips/placements sur `PFX 01`, timestamps et longueurs BWF exacts, 27 overlaps d'un échantillon, aucun gap, index média 0–61, records fixes 48/104 octets, ZIP 63 membres avec CRC valide et sauvegarde no-op du PTX bit-perfect. La session s'est ensuite ouverte et lue normalement dans Pro Tools; le Save As, la fermeture et la réouverture ont également réussi sans avertissement. Les artefacts de ce test ont été nettoyés après validation.

---

## 2026-07-14
### Backend Colab (V1.22 → V2.1)
- **Nouveau : Détecteur YAMNet indépendant** — Remplacement du sidechain V1.22 basé sur le stem "Vocals" de MDX23C/RoFormer, abandonné après confirmation sur du matériel réel que les modèles de séparation ne détectent quasiment aucune trace vocale sur un soupir, un cri ou un chant — angle mort inhérent à des modèles entraînés pour de la musique. Intégration de YAMNet (classificateur d'événements sonores, 521 classes AudioSet), qui tourne sur l'audio fusionné brut avant tout traitement. Les classes retenues sont sélectionnées par correspondance de mots-clés sur la vraie taxonomie du modèle et imprimées dans les logs pour audit avant tout traitement de fichier.
- **Nouveau : Protection Bodytalk** — Le même détecteur identifie les classes liées au mouvement physique (ex. *Walk, footsteps*) pour restaurer le signal brut à ces endroits pendant le pré-denoise, évitant que le nettoyage n'attaque le bodytalk légitime.
- **Nouveau : Anti-pumping** — `DENOISE_ADAPTATIF` (profil de bruit non-stationnaire, mieux adapté aux scènes extérieures variables — vent, trafic) et `AI_OVERLAP` (chevauchement des segments d'inférence relevé, masque de séparation plus lissé dans le temps) ajoutés au panneau de contrôle pour cibler le pumping observé sur les scènes bruyantes.
- **Correctif : défaut `RATIO_ROFORMER`** — Le défaut (0.50) ne correspondait pas à la recommandation déjà documentée dans le panneau de contrôle lui-même ("0.60 = Favorise RoFormer, recommandé pour PFX"). Corrigé à 0.60.
- **Correctif : garde-fou de confiance sur `initial_mic_alignment`** — Le regroupement par "take" se fait sur le dernier nombre trouvé dans le nom de fichier, ce qui peut faire collisionner deux prises non-apparentées si leurs noms partagent le même suffixe numérique final. Dans ce cas, le code tentait d'aligner les deux clips par corrélation croisée malgré l'absence de rapport réel, produisant un fichier corrompu. Un score de confiance normalisé est maintenant calculé après chaque corrélation ; en dessous du seuil (`ALIGNMENT_CONFIDENCE_MIN = 0.15`), l'alignement est ignoré et le clip est copié tel quel, avec avertissement en log.
- **Ajouté puis retiré : version de comparaison A/B** — `GENERER_VERSION_COMPARAISON` a brièvement généré une paire de fichiers par clip (`_PFX_Ready.wav` + `_PFX_Ready_NoDuck.wav`) pour comparer l'effet du duck directement dans Pro Tools. Retiré à la demande de l'utilisateur une fois son utilité de test épuisée — chaque clip produit de nouveau un seul fichier de sortie.
- **Retiré : sauvegarde du stem Vocals dans `process_batch`** — Redevenue inutile une fois le sidechain YAMNet en place (indépendant du split vocal/instrumental) ; `process_batch` ne conserve à nouveau que le stem Instrumental.
- **Renommage de fichier** : `Colab_Backend_PFX_FINAL_26_Juin_v4.ipynb` → `Colab_Backend_PFX_V_2_1.ipynb`. La convention de version passe d'un suffixe date (`_FINAL_26_Juin_vX`) à un numéro sémantique (`V2.1`).

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
