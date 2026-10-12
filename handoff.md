# Handoff - PFX Extractor

## Date de session : 2026-10-12 — deux backends utilisables, nomenclature

- Sur demande utilisateur, Test V3 reste locale mais n'est plus versionnée : git rm --cached uniquement et règle .gitignore dédiée. Aucun fichier local supprimé.
- Backends renommés `Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb` et `Colab_Backend_PFX_Bandit_V4.ipynb`; tous deux utilisables au choix, pas des essais. Bandit titres/messages/label manifeste deviennent Bandit V4/Bandit_V4, protocole2 inchangé, anciennes générations compatibles. DSP et paramètres inchangés.
- Liens/docs et tests adaptés. La référence Test V3 peut être reconstituée uniquement dans les tests depuis les sources embarquées/sources v3 conservées quand le notebook local ignoré est absent; aucun backport DSP ni changement frontend/API.

## Date de session : 2026-10-12 — minimum absolu pt_api 1.6.2

- L'utilisateur confirme que l'API est corrigée et demande >=1.6.2 obligatoire. Tag distant v1.6.2 vérifié, commit e0a7cb6ab645ee1a763ecea875f88344c496868d. requirements épinglé v1.6.2 et paquet mis à jour dans .venv.
- MIN_PT_API_VERSION=(1,6,2), messages générés depuis cette constante; versions plus anciennes ou inconnues refusées, y compris tous les chemins locaux. Versions stables supérieures acceptées. Tests de bornes et vraie génération/relecture d'un lot synthétique131 avec ordre natif des événements contrôlé.
- Aucun changement du dépôt API ou des notebooks. Frontend à redémarrer avant nouvelle livraison pour quitter les anciens modules en mémoire.

## Date de session : 2026-10-12 — timeline arrêtée au clip 99, cause confirmée

- Malgré pt_api 1.6.1 réellement chargée, la sortie BOOM_PFX_001 s'arrête dans Pro Tools à 10:33:13:16. PTX/ZIP/manifeste contiennent pourtant les 131 clips exacts jusqu'à 10:43:03:10; UMID uniques, géométries/empreintes cohérentes.
- Ordre alphabétique strict des noms : 09,100..109,10,110..119,11,120..129,12,130,131,13..99. Quatre retours temporels en arrière; dernier événement physique =99, fin exactement10:33:13:16. API builder conserve cet ordre; reader trie par timestamp et validation par dictionnaire masque l'anomalie.
- Diagnostic sous work/diagnostics/pt_api_1_6_1_timeline_20261012 : contrôle byte-identique, candidat avec seuls les événements 0x1050 réordonnés, médias copiés/hashés, 131 placements/IDs/durées/TC intacts. Seul root0x1054 diffère; no-op API byte-identique. Aucun chevauchement ni trou dans ce lot.
- L'utilisateur confirme « ca fonctionne! » après test du candidat chronologique. Cause confirmée pour ce lot; save natif/réouverture encore non fournis. DIAGNOSTIC_POUR_AGENT_API.md et evidence.json actualisés pour l'agent API. Aucun changement de code pendant l'enquête; l'utilisateur veut confier le correctif à l'agent de l'API. Respecter le contrat générique et valider séparément la priorité des chevauchements.

## Date de session : 2026-10-12 — dépendance pt_api 1.6.1

- L'utilisateur rapporte parfois une timeline PTX incomplète et demande d'utiliser pt_api 1.6.1 pour son test. Tag distant confirmé, SHA 8c91eb9e82d03bbaf629c901cc68a730fd96b046. requirements auparavant v1.3.8, paquet absent de .venv; un nouveau processus chargeait déjà Y:\pt_api\pt_api.py version 1.6.1 par fallback. Ne pas affirmer que le bug venait nécessairement de la version.
- requirements mis à v1.6.1, installation du seul paquet pt_api dans .venv. Resolver exige >=1.6.1 quelle que soit la source et log version/chemin. Ordre PT_API_PATH > installé > frère si absent conservé. Frontend à redémarrer pour éviter tout module conservé en mémoire. Pas de modification du dépôt API ni des notebooks.
- Tests de résolution/version et test existant de vraie génération/relecture PTX synthétique. Validation manuelle du lot incomplet laissée au test utilisateur.

## Date de session : 2026-10-06 — Test V4 demandée pour le cumul humain

- L'utilisateur veut une nouvelle copie de Test V3 avec la séquence de retrait cumulatif de V3.5.2, pour comparer les soupirs/respirations/chuchotements. Nouveau `Colab_Backend_PFX_Bandit_V4.ipynb`; V3/V3.5.2 préservées.
- Bandit et paramètres conservés : pré-denoise 40 %, bodytalk +4 dB, gain d'écoute résiduel +18 dB. Finition : masques YAMNet du snapshot brut → premier retrait sur SFX → analyse résiduelle du rendu déjà atténué → deuxième retrait multiplicatif → bodytalk local une seule fois. Pas de réintroduction de Snowball/alignement. Masques du brut réanalysés scène par scène en remplacement de la passe SFX V3, sans accumulation mémoire.
- Implémentation embarquée depuis backend_test/v4_processing.py et v4_workflow.py, contrat protocole 2 commun et identifiants Vtest_V4/2026-10-06-test-v4-cumulative. Même bouton ZIP/PTX, aucun manifeste à renommer, anciens résultats conservés. API intacte.
- Tests dédiés tests/test_backend_vtest_v4.py : 8 réussis, dont workflow avec modèles simulés mais vraie finition/FFmpeg et contrôles N/TC/UMID. Le cumul 95 % × 90 % peut atteindre environ −46 dB, pas une garantie d'amélioration; Foley simultané possiblement davantage atténué. Validation auditive à réaliser par l'utilisateur sur Colab.

## Date de session : 2026-10-06 — V3.5.2 demandée

- Nouveau `Colab_Backend_PFX_MDX23C_BS_RoFormer_V3_5_2.ipynb` : V3.5.1 avec correction UMID uniquement côté traitement/export; pré-nettoyage ensuite ajusté à 40 % sur demande (contre 58 %), autres réglages inchangés, bodytalk +3,5 dB. V3.5.1 conservée (SHA256 FAF3695FBB4621ACF2852037992F6888C436CA8E962A5CC4C6B655E419973A7A). API intacte.
- Export temporaire FFmpeg avec UMID supprimé des métadonnées, écriture UUID4 binaire et contrôles audio/identités avant publication. Helpers UMID identiques à `delivery_contract.py`. Tests dédiés : `tests/test_backend_v352.py`.
- L'utilisateur refuse toute manipulation du manifeste en changeant de notebook. V3.5.2 publie désormais comme Test V3 via protocole 2 et run_<id>, pointeur commun et contrôles d'intégrité. Choisir l'un ou l'autre ipynb suffit. Anciens lots conservés. Helpers backend_test/v352_delivery.py + contrat complet embarqués. Tests des vrais workflows dans les deux sens avec modèles simulés. Pas de traitement concurrent; reprise exceptionnelle après confirmation de l'arrêt d'un run running interrompu. Aucun renommage manuel du manifeste entre ces deux notebooks.
- L'utilisateur confirme que le téléchargement Test V3 est réglé après relance du frontend, préfère vitesse/body foley mais note encore des souffles; amplification détecteur +18 dB toujours active. Cette demande ne modifie pas les réglages de Test V3. Pas de nouvelle validation auditive Colab locale.

## Date de session : 2026-10-06 — correction UMID autorisée, API hors périmètre

- L'utilisateur demande de corriger le programme sans toucher pt_api; il refera un test complet. Ne pas réparer ses lots à sa place : ils sont conservés comme preuves.
- Diagnostic : 131 WAV = 2591.005083 s, mais 63 UMID identiques. Le 01, silencieux, a 396396 samples (8 s 6 images). Limiter chaque collision à ce premier média donne exactement 75419344 samples = 00:26:09:16 à 23,976. WAV 06/09/17/32/42 et 04/12/13 contiennent bien de l'audio. L'ancien lot MPM_06_PFX a la même collision. FFmpeg n6.1 wavenc utilise strtoll sur des segments UMID hex unsigned, donnant 7fffffffffffffff.
- Correction uniquement du notebook courant Test V3 et du programme local : transfert FFmpeg `umid=` vide, puis écriture binaire d'un UMID neuf (label native basic + UUID4 matériel + extension nulle). Relecture UMID et hash data inchangé. Source/raw jamais modifiée. Protocole 2 identités sources/sorties, vérification anti-collision et anti-réutilisation source. Révision 2026-10-06-test-v3-umid.
- Frontend : contrôle des identités réelles sur téléchargement, avant API et sur les Audio Files sortis avant ZIP, même anciens lots sans protocole 2. Refus explicite des collisions. Redémarrer le frontend et recharger le fichier ipynb corrigé (même nom). Import manuel dans session Pro Tools neuve à vérifier. Ne pas présenter tous les problèmes d'import, notamment +9 images, comme formellement validés corrigés.
- 88 tests locaux réussis après correction (dont export/relecture PTX réelle sur audio synthétique); empreinte API avant/après identique. Validation manuelle Pro Tools toujours attendue.
- pt_api.py doit rester inchangé : SHA256 avant intervention F77E7B873D5620405A289C01DE5F19DF3296149EA759D8A9627BADDEA901F6A9. Aucun DSP modifié; pré-denoise 40 %, bodytalk max +4 dB conservés.

## Date de session : 2026-10-05 — Test V3 demandé après audit

- L'utilisateur retient un pré-denoise à 40 % après écoute du bypass et demande de corriger les cinq points d'audit. Nouveau `Colab_Backend_PFX_Vtest_V3.ipynb`; anciens notebooks inchangés.
- Suppression de l'alignement BOOM/LAV et du regroupement Snowball. Scènes indépendantes, N et TC vérifiés; aucune coupe ou ajout de silence. Pré-denoise adaptatif 40 %, protégé par YAMNet brut. Finition YAMNet + résidus sur SFX non atténué, une seule atténuation par maximum. Bodytalk +4 dB local, veto indices de pas/impacts, pas d'isolation parfaite des tissus.
- Nouveau contrat `delivery_contract.py`, sources V3 embarquées sous `backend_test/`. Publications `2_Environnements_IA/run_<id>` et `PFX_delivery.json` racine. Frontend mis à jour/redémarré indispensable; même bouton ZIP/PTX. Vérification des générations complètes, fichiers exacts, hash, durée et TC, puis contrôle du pointeur. Anciennes copies locales déplacées dans `work/processed_previous_*`, non effacées. pt_api non modifié.
- Préflight avant modèles : noms BOOM XOR LAV valides sous Windows, comptes égaux si deux micros, mono48k RIFF BWF/UMID/time_reference UInt32, 1024–0xFFFFFF samples. Sources snapshot local vérifié. Export par microphone même avec préfixes de scènes variés. Les limites du profil sont documentées; aucune prolongation arbitraire des petits clips.
- Validation finalisée le 6 octobre : certains FFmpeg locaux émettent fmt IEEE float simple (18 bytes), alors que pt_api requiert WAVE_EXTENSIBLE (40 bytes). `ensure_export_extensible` adapte uniquement le fmt des fichiers de staging nouvellement créés; préserve données/BWF, vérifie géométrie et idempotence. Bext version 1/2 avec UMID requis au préflight; tests réels FFmpeg et data identiques réussis.
- 83 tests locaux passent, y compris une génération/relecture PTX réelle avec template local et audio synthétique. Aucune validation auditive T4 ni ouverture/import manuel de Test V3 effectuée. Interdiction de runs concurrents; après crash dur, confirmer arrêt, option REMPLACER_RUN_INTERROMPU puis nouveaux chemins/run_id. Retour à backend historique : archiver/retirer le manifeste V3; sous-dossiers de génération et sauvegardes locales à gérer explicitement, pas purgés automatiquement.
- Enquête MPM_06_Boom-Gain_90 : accès Drive lecture seule. Brut et traité = 1483482 samples (30.905875 s), TC 1823255434; copie locale/export et manifeste SHA256 cohérents. PTX généré : même longueur, même début, offset source 0. Deux runs (58 % et bypass) gardent N. Utilisateur constate +9 images une fois dans sa timeline; méthode de transfert et session après import non fournies. Ne pas prétendre le bug résolu par Test V3.

## Date de session : 2026-10-05 — comparatif sans pré-nettoyage

- Nouvelle variante `Colab_Backend_PFX_Vtest_sans_prenettoyage.ipynb` demandée par l'utilisateur pour évaluer la perte éventuelle de body foley au pré-denoise. Vtest actuelle (+4 dB, pleurs, pré-denoise 58 %) et V3.5.1 conservées.
- Bypass réel : fonction et appel pré-denoise retirés, Bandit lit les WAV alignés/regroupés directement. Tous les autres traitements identiques, même frontend et ZIP/PTX. Aucun traitement audio externalisé.
- 69 tests locaux passent : parité des traitements restants, échantillons exacts à l'entrée Bandit, livraison répétée et BWF. Pas de test auditif/T4 de cette variante. Préserver le premier ZIP avant l'autre run qui remplace les WAV de même nom sur Drive.

## Date de session : 2026-10-05 — Vtest pleurs, longueurs à diagnostiquer

- L'utilisateur est impressionné par le comparatif, mais constate plus de pleurs et trois clips avec quelques frames de trop. Il a supprimé les WAV et confirme que le problème concernait aussi des clips longs.
- Vtest modifiée pour les pleurs : classes 19–22, `DUCK_DEPTH_PLEURS=95`, masque brut prioritaire + ajout aux résidus, veto bodytalk; 0 désactive ces ajouts. Puis gain bodytalk maximal porté à +4 dB (+0,5 dB) à la demande de l'utilisateur, protections inchangées. Pas de nouveau modèle ou d'appel YAMNet. V3.5.1, frontend et API intacts; workflow identique.
- Audit durées : N préservé par Bandit, bornes Snowball strictes et longueur export vérifiée. Seule extension volontaire : clips <1024 samples portés à 1024 (max 21,3 ms), exclue comme explication des longs clips. Test de queue artificielle +12000 samples éliminée du redécoupage réussi. Ne pas annoncer un bug de longueur corrigé : cause non établie. Le manifeste Drive peut survivre aux WAV supprimés (`0_Model_Cache/Bandit_v2/manifests`) et contient les longueurs comparables.
- Ajustement pleurs heuristique à écouter : aucun exemple disponible pour calibration, ne pas garantir la suppression effective. Révision `2026-10-05-pleurs-bodytalk4db` dans manifeste, changements décrits en en-tête notebook.

## Date de session : 2026-10-03 — Vtest Bandit v2, confidentialité

- L'utilisateur demande un notebook séparé pour comparer le même projet, puis impose le traitement dans Colab (audio confidentiel, aucune API externe). Création de `Colab_Backend_PFX_Vtest.ipynb`, autonome; V3.5.1 inchangée (SHA256 `faf3695fbb4621acf2852037992f6888c436ca8e962a5cc4c6b655e419973a7a`).
- Bandit v2 officiel multilingue / DnR v3, sortie SFX à la place du mélange MDX/RoFormer. Ce n'est PAS DnR-nonverbal ni MVSEP. Même finition, mêmes paramètres; le modèle n'est pas garanti meilleur pour les sons humains non verbaux. Aucun upload de WAV vers un service tiers.
- Correction demandée par l'utilisateur : workflow strictement habituel, seul le notebook chargé change. Entrée `1_Bruts_vers_Colab`, sortie BWF `2_Environnements_IA`, puis bouton ZIP/PTX du frontend. Plus de dossier de comparaison ni ZIP Colab séparé. Télécharger et conserver la première livraison avant le second run (remplacement des WAV de même nom); ne pas vider les bruts entre comparatifs ni télécharger pendant le traitement. Manifeste technique dans `0_Model_Cache/Bandit_v2/manifests`, hors livraison.
- Runtime maintenable `backend_test/bandit_runtime.py` embarqué en cellule 4, sources et poids publics épinglés/vérifiés, chargement strict, preflight réel de 8 s, pas de bypass. Voir architecture pour paramètres et chemins.
- Validation après correction du workflow : 57 tests réussis (39 existants + 18 nouveaux), dont deux publications successives dans un dossier frontend déjà rempli (ML simulé, WAV réels, aucun manifeste/ZIP parasite), reconstruction aux bords, absence de décalage/normalisation, égalité YAMNet/DSP avec V3.5.1 et export BWF ffmpeg réel mono 48 kHz avec time_reference conservée. `git diff --check` sans erreur.
- Smoke réel local CPU : poids officiels 446680129 octets et empreinte vérifiés, 37022688 paramètres chargés strictement; signal synthétique de 384000 échantillons -> SFX de même longueur, valeurs finies (pic 0.00011571197). Aucune scène confidentielle utilisée pour ce contrôle; cela ne valide pas la qualité auditive. T4 et Colab complet non exécutés ici.
- Environnement de validation isolé et poids publics sous `work/bandit_test_env` et `work/bandit_validation` (ignorés par Git). Aucune modification du frontend, de pt_api, des requirements applicatifs ni de colab_link.txt. Les tests frontend simulent des erreurs dans les logs; ce ne sont pas des incidents utilisateur.

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
