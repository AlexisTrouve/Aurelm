# Domain Knowledge — Aurelm

Pre-seeded context for the OpenClaw agent. This file is loaded at session start to avoid cold-start problems.

## Game Structure

- **Format** : JDR de civilisation multijoueur, asynchrone, joue sur Discord.
- **MJ** : Arthur ("Mug") — gere 3+ civilisations simultanement.
- **Joueurs** : Chaque joueur controle une civilisation. Il poste ses decisions, Arthur repond avec les consequences narratives.
- **Flux d'un tour** : Le joueur poste ses choix -> Arthur ecrit le resultat narratif (1 ou plusieurs segments) -> Le pipeline extrait les entites et classe les segments.
- **Echelle temporelle** : Le jeu couvre des millenaires de temps in-game. Un tour peut representer des annees ou des decennies.

## Civilisations connues

### Civilisation de la Confluence
- **Joueur** : Rubanc
- **Geographie** : Vallee fluviale, a la confluence de deux rivieres
- **Technologie-cle** : Argile Vivante (durcit instantanement au contact de l'air)
- **Structure sociale** : Oligarchie a cinq castes — Air, Feu, Eau, Terre, Ether
- **Evenements majeurs** : Decouverte de ruines anciennes, premier contact avec les Cheveux de Sang
- **Alias courants** : "Confluence", "Confluents", "la Confluence"

### Cheveux de Sang
- **Type** : Civilisation maritime etrangere
- **Premier contact** : Avec la Confluence (approche par la mer)
- **Alias courants** : "Cheveux de Sang", "CdS"

### Nanzagouets / Tlazhuaneca
- **Type** : Civilisation etrangere
- **Alias courants** : "Nanzagouets", "Tlazhuaneca"

### Autres
- D'autres civilisations seront ajoutees au fur et a mesure qu'Arthur elargit le jeu.

## Glossaire

| Terme | Definition |
|-------|-----------|
| **Tour** | Un post du MJ sur Discord contenant narration, choix et/ou consequences. Unite de base du jeu. |
| **Segment** | Partie d'un tour, classee par type (narrative, choice, consequence, ooc, description). |
| **Entite** | Element nomme extrait par NER : personne, lieu, technologie, institution, ressource, creature, evenement. |
| **Lore** | L'ensemble des faits canoniques accumules sur le monde du jeu. |
| **Sanity check** | Verification de coherence d'une affirmation contre le lore etabli. |
| **OOC** | Out of character — commentaires hors-jeu du MJ ou du joueur. |
| **MJ** | Maitre du Jeu — Arthur. |
| **Pipeline** | Le systeme ML qui traite les messages Discord et les structure en base. |

## Types d'entites

| Type | Description | Exemples |
|------|-------------|----------|
| `person` | Personnage nomme | Chef de caste, emissaire, explorateur |
| `place` | Lieu geographique ou structure | Confluence, ruines anciennes, embouchure |
| `technology` | Savoir-faire ou invention | Argile Vivante, poterie, irrigation |
| `institution` | Organisation politique/sociale | Castes (Air, Feu, Eau, Terre, Ether), conseil |
| `resource` | Ressource naturelle ou produite | Argile, poisson, obsidienne |
| `creature` | Etre vivant non-humain | Creatures des ruines, faune locale |
| `event` | Evenement historique notable | Premier contact, decouverte des ruines |

## Types de segments

| Type | Description | Quand chercher |
|------|-------------|----------------|
| `narrative` | Texte narratif decrivant ce qui se passe | Faits, evenements, descriptions du monde |
| `choice` | Choix proposes au joueur par le MJ | Decisions en attente, options strategiques |
| `consequence` | Resultats des choix du joueur | Impact des decisions, changements d'etat |
| `ooc` | Commentaire hors-jeu | Regles, clarifications, meta-discussion |
| `description` | Description pure du monde (pas d'action) | Geographie, culture, environnement |

## Patterns de requetes courantes du MJ

1. **Verification** : "Est-ce que X est coherent ?" -> `sanityCheck`
2. **Recherche d'entite** : "Qu'est-ce qu'on sait sur X ?" -> `searchLore` puis `getEntityDetail`
3. **Recap de civilisation** : "Fais-moi un recap de la Confluence" -> `getCivState` puis `timeline`
4. **Comparaison** : "Compare les civs sur le militaire" -> `compareCivs`
5. **Chronologie** : "Timeline des 10 derniers tours" -> `timeline`
6. **Detail de tour** : "Que s'est-il passe au tour 5 ?" -> `getTurnDetail`
7. **Recherche textuelle** : "Ou parle-t-on de bronze ?" -> `searchTurnContent`
8. **Inventaire** : "Liste toutes les civs" -> `listCivs`
9. **Exploration** : "Quelles entites militaires existent ?" -> `searchLore` avec `entityType`
10. **Acquis technologiques** : "Quelles technos a la Confluence ?" -> `getStructuredFacts(civName, factType="technologies")`
11. **Historique des choix** : "Quels choix au tour 8 ?" -> `getChoiceHistory(civName, turnNumber=8)`
12. **Relations** : "Qui controle quoi ?" / "Relations de l'Argile Vivante ?" -> `exploreRelations(entityName, depth=2)`
13. **Timeline filtree** : "Tous les premiers contacts" / "Tours 5-10" -> `filterTimeline(turnType, fromTurn, toTurn)`
14. **Activite d'entite** : "Quand l'Argile est-elle devenue importante ?" -> `entityActivity(entityName)`

## Mots-cles d'aspects (pour compareCivs)

| Aspect | Mots-cles associes |
|--------|-------------------|
| `military` | armee, soldats, guerre, combat, defense, fortification, armes |
| `technology` | technologie, invention, outil, savoir-faire, decouverte, construction |
| `politics` | politique, gouvernement, caste, conseil, loi, alliance, diplomatie |
| `economy` | economie, commerce, ressource, production, echange, agriculture |
| `culture` | culture, religion, art, rituel, tradition, croyance, ceremonie |

## Fraicheur des donnees

Les donnees sont aussi a jour que le dernier run du pipeline ML. Si Arthur mentionne des evenements recents non presents dans les resultats des outils, c'est probablement que le pipeline n'a pas encore traite les derniers messages Discord. Suggere a Arthur de relancer le pipeline.
