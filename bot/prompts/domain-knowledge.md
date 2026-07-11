# Domain Knowledge — Aurelm

Contexte pré-chargé pour l'agent. Ce fichier est injecté au démarrage de session.

---

## Structure du jeu

- **Format** : JDR de civilisation multijoueur, asynchrone, sur Discord.
- **MJ** : Arthur ("Mug") — gère 3+ civilisations simultanément.
- **Joueurs** : Chaque joueur contrôle une civilisation, poste ses décisions, Arthur répond avec les conséquences narratives.
- **Flux d'un tour** : joueur poste ses choix → Arthur écrit le résultat narratif → le pipeline extrait les entités, classe les segments, détecte les sujets.
- **Échelle temporelle** : un tour peut représenter des années ou des décennies de temps in-game.

---

## Civilisations connues

### Civilisation de la Confluence
- **Joueur** : Rubanc
- **Géographie** : Vallée fluviale, à la confluence de deux rivières
- **Technologie-clé** : Argile Vivante (durcit instantanément au contact de l'air)
- **Structure sociale** : Oligarchie à cinq castes — Air, Feu, Eau, Terre, Éther
- **Événements majeurs** : Découverte de ruines anciennes, premier contact avec les Cheveux de Sang
- **Alias** : "Confluence", "Confluents", "la Confluence"

### Cheveux de Sang
- **Type** : Civilisation maritime étrangère, premier contact avec la Confluence
- **Alias** : "CdS"

### Nanzagouets / Tlazhuaneca
- **Type** : Civilisation étrangère
- **Alias** : "Nanzagouets", "Tlazhuaneca"

---

## Types d'entités

| Type | Description | Exemples |
|------|-------------|----------|
| `person` | Personnage nommé | Chef de caste, émissaire, explorateur |
| `place` | Lieu géographique ou structure | Confluence, ruines anciennes, embouchure |
| `technology` | Savoir-faire ou invention | Argile Vivante, poterie, irrigation |
| `institution` | Organisation politique/sociale | Castes, conseil |
| `resource` | Ressource naturelle ou produite | Argile, poisson, obsidienne |
| `creature` | Être vivant non-humain | Créatures des ruines, faune locale |
| `event` | Événement historique notable | Premier contact, découverte des ruines |
| `caste` | Groupe social hiérarchique | Caste de l'Air, Caste du Feu |
| `belief` | Croyance ou système religieux | Culte des ancêtres, mythologie fluviale |
| `civilization` | Entité civilisationnelle | Confluents, Cheveux de Sang |

## Tags de domaine

Les entités et les sujets peuvent être taggés avec ces domaines :

| Tag | Utilisation |
|-----|-------------|
| `militaire` | Armées, conflits, fortifications, guerriers |
| `politique` | Gouvernement, castes, lois, pouvoir |
| `religieux` | Cultes, divinités, rituels, croyances |
| `economique` | Commerce, ressources, production, agriculture |
| `culturel` | Art, traditions, monuments, festivals |
| `diplomatique` | Alliances, traités, contacts étrangers |
| `technologique` | Inventions, techniques, constructions |
| `mythologique` | Mythes, légendes, origines, créatures |

---

## Types de segments

| Type | Quand chercher |
|------|----------------|
| `narrative` | Faits, événements, descriptions du monde |
| `choice` | Décisions en attente, options stratégiques |
| `consequence` | Impact des décisions, changements d'état |
| `ooc` | Commentaires hors-jeu, règles, clarifications |
| `description` | Géographie, culture, environnement |

---

## Sujets — fils ouverts MJ↔Joueur

Un **sujet** est un fil de décision entre le MJ et un joueur, tracé par le pipeline.

**Directions** :
- `mj_to_pj` : Le MJ pose un choix ou une question au joueur (ex : "Choisissez votre stratégie d'expansion")
- `pj_to_mj` : Le joueur prend une initiative en attente de traitement par le MJ (ex : "Je fonde un temple")

**Catégories** :
- `choice` : Choix explicite (plusieurs options proposées)
- `question` : Question du MJ au joueur
- `initiative` : Initiative du joueur (action déclarée)
- `request` : Demande formelle

**Statuts** :
- `open` : En attente de réponse/résolution
- `resolved` : Traité, avec texte de résolution et confidence
- `superseded` : Remplacé par un autre sujet
- `abandoned` : Abandonné

**Quand utiliser les outils sujets** :
- Arthur demande "quelles décisions sont en attente" → `listSubjects(status="open")`
- "Qu'est-ce que le joueur a décidé concernant X" → `listSubjects(status="resolved")` + `getSubjectDetail`
- "Initiatives non traitées" → `listSubjects(direction="pj_to_mj", status="open")`
- "Décisions militaires ouvertes" → `listSubjects(tag="militaire", status="open")`

---

## Patterns de requêtes courants

| Question Arthur | Outils |
|----------------|--------|
| "Recap de la Confluence" | `getCivState` + `timeline` |
| "Qu'est-ce qu'on sait sur X ?" | `searchLore` → `getEntityDetail` |
| "Toutes les croyances des Confluents" | `getEntitiesByTag(tag="religieux", civName="Confluence")` |
| "Compare les civs sur le militaire" | `compareCivs(civNames, aspects=["military"])` |
| "Où parle-t-on de bronze ?" | `searchTurnContent(query="bronze")` |
| "Est-ce cohérent que X ait du bronze ?" | `sanityCheck(statement)` |
| "Tour 5 en détail" | `getTurnDetail(civName, turnNumber=5)` |
| "Quelles technos a la Confluence ?" | `getStructuredFacts(civName, factType="technologies")` |
| "Quels choix sont encore ouverts ?" | `listSubjects(status="open")` |
| "Initiatives du joueur en attente" | `listSubjects(direction="pj_to_mj", status="open")` |
| "Quand l'Argile est-elle apparue ?" | `entityActivity(entityName="Argile Vivante")` |
| "Relations entre X et Y" | `exploreRelations(entityName, depth=2)` |
| "Timeline des tours 5-10" | `filterTimeline(fromTurn=5, toTurn=10)` |
| "Arbre technologique" | `getTechTree(civName)` |

---

## Fraîcheur des données

Les données sont aussi à jour que le dernier run du pipeline ML. Si Arthur mentionne des événements récents absents des résultats, le pipeline n'a probablement pas encore traité ces messages. Suggérer de relancer le pipeline.
