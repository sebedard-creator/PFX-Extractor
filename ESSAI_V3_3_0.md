# Essai V3.3.0 — bruits de bouche et gain bodytalk

Notebook complet : `Colab_Backend_PFX_V3_3_0.ipynb`. La V3.2.0, jugée meilleure à l'écoute par l'utilisateur, reste intacte pour comparaison.

## Réglages de départ

- `DUCK_DEPTH_BOUCHE = 95` : retrait prioritaire buccal, jusqu'à environ −26 dB au masque maximal. Le retrait maximal est retenu parmi les masques, sans addition; la protection PFX ne diminue pas le masque buccal.
- `GAIN_BODYTALK_DB = 2.0` : jusqu'à +2 dB sur les passages identifiés comme froissements/frottements. Plage 0–4 dB. Ce n'est ni un gain global ni une normalisation.
- Souffles/chuchotements : réglages V3.2.0 conservés, notamment `DUCK_DEPTH_SOUFFLES = 95`.
- Bouche à 0 % ET bodytalk à 0 dB : retour exact au traitement audio V3.2.0, à autres réglages identiques.

## Retrait buccal

YAMNet n'a pas de classe spécifique « bec / lip smack ». Les proxys explicites sont `Chewing, mastication` (49), `Biting` (50), `Gargling` (51), avec seuil doux 0,08–0,25. Ce choix ne garantit pas la détection des becs.

Les classes ambiguës `Burst, pop` (428), `Slap, smack` (461), `Clicking` (485) ne déclenchent ce retrait supplémentaire qu'avec un indice humain proche : parole (0–4), chuchotement (12), soupir (23), respiration (36) ou indices buccaux (49–51). Les clics seuls restent soumis au traitement habituel, sans nouveau retrait buccal. Les seuils sont 0,10–0,35 pour le transitoire et 0,06–0,20 pour le contexte humain; les deux activations sont multipliées.

Le contexte est recherché à ±1 frame (hop 0,48 s). Le masque buccal obtenu est ensuite étendu de ±1 frame, avec enveloppe attaque 0,04 s / relâchement 0,25 s. Cette marge vise les débuts de phrase, mais peut retirer des objets ou mouvements voisins du dialogue. Ces temps d'enveloppe ne constituent pas une précision de détection de 40 ms : YAMNet travaille avec des fenêtres de 0,96 s espacées de 0,48 s. Le traitement reste temporel, jamais une décision sur le clip entier.

## Gain bodytalk

Proxys choisis : `Zipper (clothing)` (372), `Rub` (470), `Crumpling, crinkling` (473), `Rustle` (481); seuil 0,15–0,40, attaque 0,12 s / relâchement 0,40 s. La classe `Walk, footsteps` (48) n'est pas incluse. Ces classes peuvent aussi désigner du papier ou d'autres objets : elles ne permettent pas d'isoler les vêtements avec certitude.

Le gain agit sur le mix des stems déjà nettoyés, sans récupérer du signal brut. Son intensité est multipliée par `(1 − veto)²`, où le veto est le maximum des masques humain, souffles, bouche, ambiance, hors-PFX et d'une garde humaine plus sensible (61 classes humaines, seuil 0,06–0,20, marge ±1 frame, attaque 0,04 s / relâchement 0,60 s). Une détection indésirable maximale annule le boost, même si le slider de retrait correspondant est désactivé. Un indice faible le freine seulement; une erreur de classification peut donc encore remonter un résidu indésirable.

Le gain maximal disponible est limité par le pic du mix avant les retraits, avec une cible de crête échantillon de 0,98. Il n'y a ni normalisation globale, ni hard clipping, ni limiteur. Un pic élevé peut réduire/annuler le boost pour tout le groupe Snowball; un dépassement déjà présent n'est pas corrigé. Ce garde-fou n'est pas un limiteur true-peak. Les logs indiquent le gain disponible, les passages effectivement relevés et les pics des classes utilisées.

## Utilisation et comparaison

1. Importer le nouveau `.ipynb` dans Colab et lancer les cellules dans l'ordre, sur un nouveau traitement complet.
2. Conserver séparément les résultats V3.2.0 avant l'essai. Les dossiers Drive et noms de sortie sont identiques : ne pas lancer deux versions simultanément sur le même lot. La cellule 7 purge les temporaires, ce n'est pas une cellule de reprise.
3. Comparer notamment un bec isolé, une amorce de phrase, des vêtements sans voix, puis vêtements avec voix. Écouter aussi les clics d'objets autour des dialogues pour repérer les faux positifs.
4. Pour isoler l'effet buccal, commencer avec bodytalk à 0 dB; pour évaluer le gain seul par rapport à V3.2.0, mettre bouche à 0 %.

Les seuils sont expérimentaux, pas des probabilités calibrées. Le gain ne recrée pas le foley déjà supprimé par les séparateurs. Le retrait buccal atténue aussi le foley simultané. Aucun détecteur spécialisé ni dépendance supplémentaire n'a été ajouté.

## Validation

Tests synthétiques sur les fonctions réelles extraites des notebooks : syntaxe, partition 521 classes, désactivation bit-identique à V3.2.0, gain +2 dB, priorité buccale, veto indépendant des sliders, marge avant saturation, formes mono/stéréo, silence/masques vides, contexte local des clics, exclusion explicite des footsteps, continuité entre blocs. Les cellules d'installation, modèles, Drive et orchestration sont inchangées, ainsi que les fonctions d'alignement, de séparation, de redécoupage et de timecode. Pas de modification du frontend ni de pt_api.

Commande locale : `.venv\Scripts\python.exe -m unittest tests.test_backend_v330 -v`.

Ces vérifications ne remplacent pas un traitement Colab ni une validation auditive : aucun résultat perceptif V3.3.0 n'est encore confirmé.

Bilan local du 22 septembre : les 11 tests V3.3.0 passent. La suite complète donne 19/20 : un test frontend préexistant attend `download_processed_files()` sans argument alors que le code lui transmet `progress=...`. Les deux fichiers concernés sont inchangés par rapport au commit HEAD; ce décalage de test, sans rapport avec le DSP, n'a pas été modifié dans cet essai.

Sources de référence : [grille officielle YAMNet](https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv), [fonctionnement temporel YAMNet](https://www.tensorflow.org/hub/tutorials/yamnet).
