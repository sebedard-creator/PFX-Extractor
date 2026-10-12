# ARCHITECTURE TECHNIQUE (PFX-EXTRACTOR v3.5.2)

Les deux backends distribués sont `Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb` et `Colab_Backend_PFX_Bandit_V4.ipynb`. Ils sont utilisables au choix avec le même workflow ZIP/PTX. L'ancienne Test V3 reste uniquement locale et ignorée par Git. Le renommage n'altère aucun paramètre ou algorithme audio; les identifiants historiques des lots restent lisibles. Les nouveaux lots Bandit utilisent `backend=Bandit_V4`, toujours avec le protocole2 commun.

## Bandit V4 — retrait humain cumulatif avec Bandit (2026-10-06)

`Colab_Backend_PFX_Bandit_V4.ipynb` est le backend Bandit utilisable, dérivé de l'ancienne variante Test V3. Même Bandit/cache, scènes indépendantes, pré-denoise adaptatif 40 %, seuils/indices YAMNet, gain d'analyse résiduelle +18 dB et bodytalk maximal +4 dB. Test V3 et V3.5.2 restent intactes.

La finition `backend_test/v4_processing.py` remplace l'analyse finale du SFX non atténué par une analyse du snapshot brut, scène par scène. `apply_v4_raw_masks` applique le maximum des retraits bruts (humain, souffle, pleurs, bouche, ambiance, hors-PFX) avec les mêmes protections PFX. `_analyze_residual_audio` reçoit ensuite ce SFX déjà atténué; son analyse native/amplifiée conserve les scores maximaux, puis `apply_v4_residual_and_bodytalk` multiplie une seconde atténuation. Les gains successifs sont `(1-r_brut) × (1-r_residu)`, avec planchers de 0,03 et 0,05 par passe. À détection maximale, 95 % puis 90 % = facteur 0,005 (environ −46 dB). Le gain bodytalk local de Test V3 est appliqué une seule fois après les deux retraits, avec veto brut/résiduel et marge de crête.

Le brut est analysé pour protéger le pré-nettoyage, puis réanalysé au moment de la finition, remplaçant l'analyse SFX de Test V3. Pas de cache mémoire de masques pour toutes les scènes ni de nouveau passage de séparation. Cette séquence reproduit le principe de retrait de V3.5.2; modèle de séparation, renfort pleurs et gain bodytalk restent ceux de Test V3. Le cumul peut davantage réduire le Foley simultané. Aucun résultat auditif garanti sans comparaison Colab.

`backend_test/v4_workflow.py` reprend les contrôles de durée/timecode/UMID et la publication protocole 2 de Test V3. Métadonnées `backend=Bandit_V4`, révision `2026-10-06-test-v4-cumulative`, `human_finishing=raw_then_residual_cumulative`. Le frontend existant reconnaît ce contrat; choisir le notebook suffit pour changer de variante. Anciens dossiers run et WAV conservés. Aucune modification de l'API. Tests : ordre réel de finition avec IA simulée, cumul, temporalité, veto/marge bodytalk, résidus désactivés, export FFmpeg BWF et refus de lot échoué.

## V3.5.2 — export UMID corrigé sur la chaîne historique (2026-10-06)

`Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb` reprend le DSP, MDX23C/BS-RoFormer et le bodytalk +3,5 dB de V3.5.1. Seul réglage audio modifié : pré-nettoyage par défaut à 40 % au lieu de 58 %, comme Test V3. Le contrat complet `delivery_contract.py` et `backend_test/v352_delivery.py` sont embarqués et vérifiés par tests. FFmpeg reçoit `umid=` pour supprimer la copie de l'identifiant, puis le rendu reçoit directement un UMID UUID4. Relecture, hash data inchangé et unicité vis-à-vis des sources/rendus sont requis. Compatibilité fmt float32 extensible normalisée sans modifier l'audio ni le BWF.

Le DSP historique, dont alignement/Snowball, est conservé. La livraison utilise maintenant le même protocole 2 que Test V3 : dossier run unique, pointeur commun running/failed/complete, validation des fichiers, durée, TC, SHA-256 et UMID avant publication. Changer de notebook suffit dans les deux sens, sans archiver/renommer le manifeste. Les anciennes générations restent intactes. La présence d'un run running bloque seulement une exécution concurrente ou une reprise non confirmée; REMPLACER_RUN_INTERROMPU sert après confirmation de l'arrêt d'un run interrompu. Les sources sont re-hashées avant publication. Un run remplacé ne peut pas écraser le pointeur du suivant. Aucun changement de pt_api. Tests de bascule des vrais workflows avec IA simulée et export FFmpeg réel.

## Test V3 — invariants et livraison vérifiée (2026-10-05)

### Révision UMID — 2026-10-06

Cause vérifiée dans les WAV : 63 UMID identiques, blocs matériel saturés à `0x7fffffffffffffff` par la conversion hexadécimale signée de FFmpeg. Les fichiers bruts comparés ont des identités distinctes. La limitation des clips au premier média de 396396 samples reproduit 75419344 samples = `00:26:09:16` à 23,976. L'audio des autres WAV cités est présent; le premier média est silencieux.

Test V3 corrigé exclut `umid` des métadonnées transférées à FFmpeg, puis `assign_render_umid` écrit directement les 64 octets de l'UMID BWF. Label basic natif conservé, nouveau material number UUID4, extension nulle. Relecture exacte et SHA-256 du chunk data avant/après écriture; géométrie/time_reference toujours vérifiés. Aucun changement du DSP. Le protocole 2 enregistre les UMID des sources/sorties; interdit les collisions entre rendus et la réutilisation d'une identité source. Contrôle d'unicité sur les 32 premiers octets, pour ne pas masquer une collision basic avec une extension différente.

Frontend : vérification sur les vrais fichiers téléchargés, y compris protocole 1/legacy; recontrôle avant l'appel API et sur les Audio Files créés avant ZIP. `pt_api` est inchangé. Un lot défectueux est refusé, pas réparé implicitement. Nouvel import en session Pro Tools vierge nécessaire à la validation manuelle. Les anciens notebooks et lots sont conservés; Test V3 et V3.5.2 contiennent cette correction. Révision manifeste `2026-10-06-test-v3-umid`.

### Architecture initiale de Test V3

Archive locale `Colab_Backend_PFX_Vtest_V3.ipynb`, ignorée par Git; référence historique, pas un backend distribué. Les anciens notebooks sont conservés. Sources maintenables `delivery_contract.py`, `backend_test/v3_processing.py` et `backend_test/v3_workflow.py` embarquées à l'identique (tests de synchronisation).

1. Préflight avant modèles : noms Windows contenant BOOM XOR LAV, collisions insensibles à la casse interdites, comptes égaux si les deux types existent, WAV RIFF mono 48 kHz PCM/float, BWF/time_reference UInt32/basic UMID. Profil conservateur 1024–0xFFFFFF samples; RF64 et fichiers hors limites refusés. Copie source locale vérifiée par SHA-256. Aucune source modifiée.
2. Chaque scène traverse séparément YAMNet brut → pré-denoise adaptatif 40 % protégé par les masques bruts → Bandit. Aucun alignement, regroupement ou remplissage de scène. Bandit garde ses fenêtres internes chevauchantes avec réflexion limitée au même fichier et restitution de N samples.
3. Finition : YAMNet SFX + analyse résiduelle amplifiée sur le même SFX non atténué. Réduction unique par maximum des profondeurs. Les masques humains du brut ne sont plus réappliqués à la sortie. Le risque de suppression de Foley simultané reste explicite.
4. Bodytalk +4 dB maximum : veto humain/ambiance/résidu et classes 48/353/354/413/454/460/461 (sentinelles vérifiées). Marge sur crêtes locales ±250 ms, lissée conservativement sans dépasser cette marge. Aucun clip normalisé; pas de garantie d'isolation des seuls vêtements.
5. BWF final produit par ffmpeg avec métadonnées source; durée, taux, time_reference et format float32 extensible/fact/UMID vérifiés. Publication sous `run_<id>` avec SHA-256. Aucun écrasement des anciens WAV. Validation du 6 octobre : normalisation du seul chunk fmt pour les versions FFmpeg qui émettent un float32 simple plutôt qu’extensible. Audio et BWF conservés; opération idempotente vérifiée. UMID dans un bext version 1/2 requis au préflight.

Contrat Drive protocole 1 : `PFX_delivery.json` racine vaut running, failed ou complete et référence une génération nommée. Le frontend rejette les états non complets; télécharge le jeu exact dans un staging local; vérifie hash + géométrie; relit le pointeur avant publication locale. Une génération changée ou un fichier parasite provoque un arrêt. L'ancien dossier local est déplacé dans `work/processed_previous_*/processed` et conservé. L'export PTX revalide le manifeste et groupe par rôle BOOM/LAV, indépendamment du préfixe de scène. Les anciens exports sans manifeste gardent le mapping historique; un nom libre avec BOOM/LAV est aussi accepté.

Pas de verrou distribué garanti sur le montage Drive : les exécutions concurrentes restent interdites; un changement de run_id est détecté avant publication. Reprise après crash dur : confirmer arrêt de la VM, activer REMPLACER_RUN_INTERROMPU et recréer les chemins/run_id. Les générations et sauvegardes locales sont conservées et occupent de l'espace. Le nettoyage historique n'efface pas les sous-dossiers de générations Drive. Le manifeste V3 doit être archivé/retiré explicitement pour revenir à un backend historique.

Validation : 83 tests locaux, dont API PTX réelle + lecture des positions/longueurs/offsets sur signaux synthétiques. Aucun changement dans pt_api, aucune validation auditive T4 ni import manuel Test V3 revendiqués. Cas MPM_06_Boom-Gain_90 : brut Drive, traité Drive et clip PTX généré ont tous 1483482 samples et time_reference 1823255434; différence de neuf images après import utilisateur non expliquée.

## Variante sans pré-nettoyage (2026-10-05)

`Colab_Backend_PFX_Vtest_sans_prenettoyage.ipynb` dérive de Vtest avec pleurs et bodytalk +4 dB. Seule l'étape pré-denoise est retirée : fonction et appel `prep_denoise_batch` absents, lecture Bandit depuis `FOLDER_MERGED` au lieu de `FOLDER_DENOISED`. Aucun appel à `nr.reduce_noise`; pas de reconstruction STFT à intensité nulle. Contrôles pré-denoise remplacés par valeurs informatives 0/False. Alignement, regroupement, YAMNet, finition et export inchangés. Dépendance noisereduce et dossier temporaire denoised laissés en place mais inutilisés pour minimiser les différences. Manifeste `pre_denoise.enabled=false`, révision `2026-10-05-sans-prenettoyage`. Vtest originale conservée à 58 %. Sortie Drive et bouton ZIP/PTX habituels, pas d'exécution concurrente des variantes.

## Vtest — pleurs et diagnostic des durées (2026-10-05)

Gain bodytalk maximal par défaut porté de +3,5 à +4 dB dans Vtest seulement (`GAIN_BODYTALK_DB=4.0`). Classes 372/470/473/481 inchangées, sans ajout de footsteps ou d'impacts. Veto humain/ambiant/pleurs et marge de crête conservés; gain appliqué une seule fois, avec ou sans passe résiduelle. Le supplément réel peut être inférieur à +0,5 dB selon ces protections.

Retour utilisateur favorable sur Bandit, avec davantage de pleurs résiduels. Ajout des classes exactes 19 Crying/sobbing, 20 Baby cry, 21 Whimper, 22 Wail/moan, vérifiées par les sentinelles YAMNet. Nouveau réglage `DUCK_DEPTH_PLEURS=95` : masque brut prioritaire, non diminué par la protection PFX, combiné par maximum aux autres retraits. Activation douce 0,06–0,20 puis racine carrée, marge ±1 frame, attaque 0,05 s / release 0,65 s. Les mêmes classes alimentent le masque résiduel existant (sa profondeur reste 90 %, release 0,45 s). Masque pleurs inclus dans le veto bodytalk. Réglage pleurs nul : désactive les deux ajouts ciblés, pas les traitements humains préexistants. Aucun modèle ni appel YAMNet supplémentaire. Seuils heuristiques non calibrés sur les clips supprimés; risque de perte du Foley simultané. Révision inscrite dans le manifeste.

Trois clips signalés trop longs, dont des clips longs; WAV supprimés. Cause non confirmée. Bandit restitue N échantillons; le découpage utilise les bornes source et l'export vérifie la longueur du segment. Un test injectant une queue de 12000 échantillons montre qu'elle ne se propage pas aux coupes. Le remplissage BWF à 1024 échantillons concerne uniquement les clips <21,3 ms et n'explique pas des longs clips prolongés. Aucun découpage arbitraire ajouté. Comparer les champs `inputs[].frames` et `outputs[].frames` du manifeste Drive pour distinguer allongement réel du média et problème de placement/import; le manifeste conserve aussi les empreintes des fichiers.

## Comparatif séparé Vtest — Bandit v2 (2026-10-03)

`Colab_Backend_PFX_Vtest.ipynb` est autonome et conserve V3.5.1 intacte. Il remplace la séparation musicale double par la sortie `sfx` du Bandit v2 multilingue officiel, entraîné sur DnR v3 (pas DnR-nonverbal, pas l'ensemble MVSEP). Initialement, la finition était identique à V3.5.1; le renfort pleurs du 5 octobre est décrit ci-dessus. TensorFlow utilise la croissance mémoire pour partager la VRAM.

- Sources : `kwatcharasupat/bandit-v2`, commit `d5563d9031e95fdaa3e5a73d5020b9a0df61adb6`; modules modèle et YAML seulement, sans infrastructure d'entraînement ni logger distant. Vérification par identifiant Git blob; licence amont conservée en cache.
- Poids : `checkpoint-multi.ckpt`, Zenodo `12701995`, 446680129 octets, MD5 publié `fea2868787551b0cff36cfcf7c3622a3`. Vérification taille/empreinte, téléchargement atomique avec trois tentatives, chargement `weights_only=True`, extraction `model.*`, `load_state_dict(strict=True)`.
- Inférence mono 48 kHz, float32, batch 1, fenêtres 8 s / pas 1 s. Reconstruction Hann avec contexte réfléchi et division par la somme effective des fenêtres, sur CPU; seulement un chunk et le modèle sur GPU. Aucune normalisation ni alignement par corrélation du SFX. Durée en échantillons conservée aux bords. La reconstruction ne prétend pas reproduire bit pour bit le benchmark amont.
- Preflight avec vrais poids et fenêtre synthétique 8 s avant tout calcul coûteux. Entrée autre que mono 48 kHz, sortie incorrecte ou NaN/Inf : arrêt explicite, jamais de bypass vers le brut. ffmpeg contrôlé, format et durée BWF vérifiés.
- Même contrat Drive que V3.5.1 : entrée `1_Bruts_vers_Colab`, sortie `2_Environnements_IA`. Cache `0_Model_Cache/Bandit_v2`; temporaires `/content/pfx_vtest/<run ID>`. Les WAV de même nom sont remplacés; un dossier de sortie non vide ne bloque pas le run. Télécharger et conserver la première livraison avant le comparatif; ne pas lancer les notebooks simultanément ni télécharger un traitement incomplet.
- Sorties frontend : uniquement les BWF `_PFX_Ready.wav`, noms/canaux/timecodes inchangés. Manifeste versions/réglages/empreintes dans `0_Model_Cache/Bandit_v2/manifests/<run ID>.json`, hors livraison. Aucun ZIP Colab séparé. Le bouton habituel du frontend télécharge les nouveaux WAV et construit la session PTX + Audio Files en ZIP, sans changement de code frontend.
- Confidentialité : GET de ressources publiques, jamais d'audio dans une requête ni clé de service. Audio dans Drive/VM Colab. Installation Internet nécessaire; ce n'est pas un environnement réseau hermétique. Aucune API de séparation externe ni logger d'entraînement.

`backend_test/bandit_runtime.py` est embarqué intégralement en cellule 4; un test impose leur égalité. Le notebook n'a pas besoin de ce fichier séparé dans Drive. La T4 et l'écoute métier restent à valider par l'utilisateur. DnR peut conserver des ambiances et des sons humains non verbaux dans SFX.

## Réglage backend V3.5.1 (2026-10-03)

Le notebook de référence pour ces réglages est `Colab_Backend_PFX_V3_5_1.ipynb`; V3.5.2 reprend les mêmes réglages avec l'export UMID corrigé. Le gain bodytalk maximal par défaut est +3,5 dB (+2 dB auparavant). Le masque utilise les classes 372 (zipper), 470 (rub), 473 (crumpling/crinkling), 481 (rustle). Footsteps, taps et impacts ne déclenchent pas ce gain. Le gain effectif reste pondéré par le masque et le veto humain/ambiant, puis limité par la marge de crête existante. Il relève le mix pendant les mouvements détectés, avec possibilité de relever d'autres sons simultanés. Le README décrit les contrôles; `changelog.md` conserve l'historique des versions. Les anciens notebooks et guides par version ont été retirés du dossier de travail.

## Analyse résiduelle et gain bodytalk

Le traitement suit cet ordre : analyse YAMNet du brut, pré-denoise protégé, séparation MDX/RoFormer et mélange aligné, premiers retraits pilotés par le brut, analyse résiduelle du mix atténué, retrait résiduel puis gain bodytalk appliqué une seule fois.

La détection résiduelle conserve son observation au niveau initial et ajoute une observation amplifiée par fenêtre (gain maximal +18 dB par défaut, crête limitée à 0,90). Les scores par classe sont fusionnés par maximum avant les enveloppes et l'unique retrait résiduel. Les copies amplifiées ne sont jamais rendues. Fenêtres effectives de 15 600 échantillons à 16 kHz, pas de 7 680; dernier segment complété par des zéros. Gain d'analyse nul : seulement l'observation initiale; profondeur résiduelle nulle : aucune analyse secondaire. Un appel court au modèle s'ajoute par fenêtre amplifiable; MDX et RoFormer ne sont pas relancés.

| Masque | Classes / activation | Enveloppe |
| --- | --- | --- |
| Respiratoire renforcé sur le brut | Whispering 12, Sigh 23, Breathing 36, Gasp 39, Pant 40, Snort 41, Sniff 45; seuil doux 0,06–0,18 puis racine carrée | Marge ±1 frame, attaque 0,05 s, relâchement 0,55 s |
| Résidus respiratoires | Les mêmes classes; seuil 0,08–0,25 puis racine carrée | Maximum des groupes résiduels, marge ±1 frame, attaque 0,05 s, relâchement 0,45 s |
| Résidus buccaux | Chewing 49, Biting 50, Gargling 51; seuil 0,10–0,30 | Même enveloppe résiduelle |
| Résidus parlés | Classes 0–4; seuil 0,10–0,35 | Même enveloppe résiduelle |
| Garde humaine résiduelle | Les 61 classes humaines; seuil 0,06–0,20 | Marge ±1 frame, attaque 0,04 s, relâchement 0,60 s |

Le premier masque buccal exploite les indices directs 49/50/51 et les transitoires 428/461/485 avec contexte humain proche. Le bodytalk utilise ses quatre classes de froissement/frottement et un veto combinant les masques humains, buccaux et ambiants initiaux, ainsi que les indices humains résiduels. Le gain est limité par la marge calculée sur la crête du mix avant les retraits, avec cible conservatrice 0,98; cette limite peut empêcher le gain sur un groupe entier.

Au maximum, les retraits respiratoire 95 % et résiduel 90 % peuvent se cumuler à environ −46 dB, en plus du denoise et de la séparation. Une détection peut manquer ou être fausse; le foley simultané peut être atténué. Les scores ne sont pas des probabilités calibrées. Le pas YAMNet est 0,48 s : une attaque de 50 ms n'implique pas une localisation à 50 ms. La finition humaine reste nécessaire.

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
- **Adaptateur de livraison Pro Tools (`protools_export.py`) :** Couche propre à PFX Extractor. Elle trie les WAV par filename, impose le format `<famille>-Gain_<numéro>_PFX_Ready.wav`, affecte la première famille à `PFX 01` et la seconde à `PFX 02`, puis appelle `build_audio_session()` de `pt_api`. `requirements.txt` installe `v1.6.2` depuis son tag GitHub (e0a7cb6ab645ee1a763ecea875f88344c496868d). Le resolver exige >=1.6.2 et journalise version/chemin chargés. Priorité : PT_API_PATH explicite, paquet installé, puis dépôt frère si absent. Une ancienne version chargée est refusée. Redémarrage frontend requis après mise à jour du paquet; contrôle d'intégration sur131clips synthétiques nommés alphabétiquement, avec ordre chronologique des événements bruts requis. Une troisième famille est refusée explicitement. Cette politique applicative demeure hors de l'API générique.
- **Template Pro Tools locale (`template.ptx`) :** Modèle natif validé, vide sur la timeline, possédant les pistes `PFX 01`/`PFX 02` et le prototype média requis par le builder. Ce fichier propriétaire est exclu par `.gitignore` et doit être installé séparément à la racine de chaque déploiement. Le flux intégré cible des sessions mono 48 kHz à 23,976 fps. L'utilisateur peut fournir ponctuellement une autre template compatible dans les paramètres avancés.
- **~~Module DSP (`dsp_local.py`)~~ — DÉPRÉCIÉ (V2.1) :** Bibliothèque de fonctions DSP initialement prévue comme couche de post-traitement local. Confirmé inutilisé (aucun import dans `app_local.py`) et retiré de la boucle de traitement — la protection PFX et le denoise sont centralisés dans le backend Colab. Le fichier reste dans le dépôt à titre de référence mais n'est plus appelé nulle part.
- **Backend Colab (`Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb`) :** Le script exécuté sur les serveurs de Google (GPU), responsable de :
  - la séparation de sources (RoFormer + MDX23C, fusion pondérée configurable) ;
  - l'alignement automatique séquentiel Lav/Boom avec garde-fou de confiance (voir ci-dessous) ;
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
- **Appariement et garde-fou de confiance sur l'alignement (V3.1.2) :** Les fichiers contenant `BOOM` et `LAV` sont triés séparément selon l'ordre naturel de leur nom, puis appariés par position; leurs suffixes numériques peuvent différer. Les deux listes doivent avoir le même nombre de fichiers avant traitement. L'alignement par corrélation croisée calcule ensuite un score de confiance normalisé; en dessous du seuil, le Lav est copié tel quel plutôt que d'être décalé sans rapport acoustique. Les sidecars macOS `._*.wav` sont ignorés.
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
