# Essai V3.2.0 — soupirs, chuchotements et respirations

Notebook autonome : `Colab_Backend_PFX_V3_2_0.ipynb`.
La référence stable reste `Colab_Backend_PFX_V3_1_2.ipynb`.

## Utilisation

Importer le notebook TEST dans Colab et exécuter ses cellules dans l'ordre lors du prochain traitement. Le nouveau contrôle « retrait prioritaire soupirs / chuchotements / respirations » est réglé à 95 %. Laisser les autres réglages habituels pour évaluer ce seul changement.

Les dossiers Drive et les noms de sortie sont les mêmes que dans la version stable : conserver une copie séparée des résultats de référence avant une comparaison et ne pas lancer les deux notebooks simultanément sur le même lot. La cellule 7 reste un lancement complet avec purge des temporaires, pas une cellule de reprise.

## Comportement expérimental

- Sous-ensemble humain : Whispering (12), Sigh (23), Breathing (36). La partition 521/521 reste inchangée.
- Seuils du masque ciblé : 0,10–0,30 au lieu des 0,18–0,45 du masque humain général. Ces scores ne sont pas des probabilités calibrées.
- Enveloppe : attaque 0,08 s, relâchement 0,60 s; résolution YAMNet et interpolation inchangées.
- Retrait ciblé maximal de 95 % en amplitude, soit environ −26 dB, sans veto de la protection PFX. Le maximum des retraits est utilisé, sans addition des deux masques humains.
- Le contrôle à 0 % désactive entièrement le renforcement; les autres traitements gardent leurs paramètres V3.1.2. Le slider humain général ne contrôle pas ce nouveau masque indépendant.
- Le masque atténue également le foley simultané. Les faux positifs et les événements non détectés restent possibles. Le pré-denoise n'est pas modifié.
- Les logs TEST affichent les pics des trois classes et le pourcentage de masque ciblé actif pour aider à interpréter les résultats à l'écoute.

## Vérification

Syntaxe du notebook contrôlée. Tests locaux sur les fonctions extraites : retour exact au gain V3.1.2 lorsque le contrôle vaut 0 %, gain 0,05 sur une détection ciblée maximale malgré une protection PFX maximale, absence de retrait supplémentaire sur du PFX seul, seuils et masques vides. Les cellules d'installation, de configuration des modèles et de lancement sont identiques à la référence. Aucun traitement GPU ni validation perceptive n'a été effectué pour cette version d'essai.
