# Design — les tools carte pour un LLM (read + write)

> **Statut : IMPLÉMENTÉ (branche `feat/map-tools`, TDD).** Les 10 tools + le CLI sont
> livrés et testés (bot suite 221 passed / 4 skipped) ; build order §6 tout coché.
> Compagnon de
> [`map-ingestion-plan.md`](map-ingestion-plan.md) : celui-là décrit comment un monde
> Theomen entre dans la base ; **celui-ci décrit l'interface agent/LLM** au-dessus —
> comment le MJ (et le Context Agent de Demiurgos) *perçoit* et *modifie* la carte.

---

## 1. La question

> Comment donner à un LLM un tool de carte **utile**, en **lecture ET en écriture** ?

Ce n'est pas une question de plomberie (MCP vs HTTP). C'est une question de **design
d'interface**. Et Aurelm n'est **pas du SIG** : c'est un **jeu**. Le MJ ne fait pas du
CRUD sur des cellules, il fait des **actes narratifs** — *une cité est fondée, une
guerre ravage une province, un peuple migre*.

## 2. Le principe (confirmé par le prior art)

**Loi universelle : un LLM est nul en géométrie brute. Ne la lui fais jamais faire.**
Tous les systèmes agent-spatiaux convergent : **séparer la couche SÉMANTIQUE (le LLM)
de la couche GÉOMÉTRIQUE (le code déterministe).** Le LLM raisonne en mots et en
intentions ; le code résout les coordonnées, le voisinage, les distances, le
wrap-cylindre.

- **MapAgent**, **Spatial-Agent** : « spatial grounding » = traduire les descriptions
  sémantiques en représentations calculées ; le planner LLM est **découplé** de
  l'exécution géométrique.
- **Grid-world (« From Text to Space »)** : l'agent ne sort **jamais** de coordonnée —
  il choisit une action dans un **vocabulaire fixe**, et le monde **valide** (une
  action illégale ne change rien, ce n'est pas le LLM qui décide de la légalité).
- **Voyager / Generative Agents** : intentions **haut-niveau** exécutées par une couche
  déterministe + **mémoire** des lieux nommés (chez Voyager la skill-library = ~15× la
  perf). Le LLM ne manipule jamais la grille.

### Les trois règles qui en découlent, pour TOUS les tools carte

1. **Jamais de `(q,r)` du LLM.** Cible toujours par **nom** (« le siège fluvial des
   Confluents »), **relatif** (« vers la frontière des Cheveux », « au nord-est »), ou
   **id de proposition** (le tool propose des candidats, le LLM en *choisit* un).
2. **Read = tranches sémantiques**, pas de grille brute. On rend de la prose/du
   structuré (lieux nommés, directions relatives, distances, features notables), jamais
   un dump de cellules.
3. **Write = acte validé, tracé, avec feedback.** valider → appliquer → **logguer
   l'événement** (`map_cell_events`) → **renvoyer le nouvel état local** (le LLM ne voit
   rien, il a besoin du retour pour vérifier et se corriger).

> **La carte n'est pas une base de données, c'est une chronique.** Aurelm l'a déjà
> modélisé : `map_cell_events.event_type` = `settlement | battle | discovery |
> diplomatic | migration | disaster | note`. Le vocabulaire des writes existe déjà.

### Ce que ça règle côté archi

Le débat « read vs write », et « bot Python vs mcp-server TS », **se dissout** : la
**géométrie reste 100 % en Python** (une seule source de vérité, zéro duplication), les
tools sont **sémantique-in / sémantique-out**, et on expose cette *même* logique via la
surface que Demiurgos utilise (à câbler séparément).

---

## 3. READ — perception

| Tool | Statut | Entrée sémantique | Rend |
|---|---|---|---|
| `groundCivTerrain` | ✅ existe | civName, radius | province d'origine + anneau de provinces (**le grounding cœur**). 🔧 à enrichir : **directions relatives + noms** (« fer 2 provinces NE ») au lieu de `(q,r)` |
| `getTerritory` | ✅ existe | civName | toutes les provinces contrôlées par une civ |
| `findEntityOnMap` | ✅ existe | entityName | où se trouve une entité (fuzzy + alias) |
| `findNearest` | ✨ new | from (civ/feature), what (ressource/biome/eau/relief) | « le fer le plus proche des Confluents » — **le** tool MJ (« ont-ils accès au bronze ? ») |
| `whatIsBetween` | ✨ new | civA, civB | terrain / barrières / provinces entre deux civs (frontières, chaînes de montagnes) |
| `describeRegion` | ✨ new *(ou un mode de ground)* | around (civ/feature), radius | résumé de région (biomes dominants, features, qui contrôle) — le « dézoom » |
| `proposeSpawnPositions` | 🔧 fonction → **tool** | mapName, n, spacing | candidats de spawn classés (habitabilité), read-only — alimente `foundSettlement` |
| `getMaps` | ✅ existe | — | liste des cartes |
| `getMapOverview` | 🔧 **refactor** | mapName | **résumé sémantique** (régions/biomes/features/sièges) — le dump de 200 cellules est inutile à un LLM sur un vrai monde |
| `getCell` / `getCellHistory` | ✅ existent | q,r | **bas-niveau** (suivi après un tool sémantique / GUI / debug) — secondaires, pas primaires pour le LLM |

## 4. WRITE — actes narratifs de MJ

Chaque write suit **le même moule** (règle 3) : valider (pas de cité dans l'océan) →
appliquer l'état → logguer l'événement → renvoyer le nouvel état local.

| Tool | Statut | Entrée sémantique | Effet + événement |
|---|---|---|---|
| `foundSettlement` | 🔧 refonte de `place_civ` | civName, at (**id de proposition** / ancrage nommé) | pose une cité, `controlling_civ_id` → `settlement`. **Le socle** — template de tous les writes |
| `expandTerritory` | ✨ new | civName, toward (direction / civ / feature), amount? | le code choisit les provinces (le long du fleuve/relief) → `migration` |
| `recordEvent` | ✨ new | kind, at (nommé / civ / relatif), description, civName? | bataille / découverte / diplomatie / catastrophe → historique (`kind`). Le **write narratif générique** |
| `moveEntity` | ✨ new | entityName, to (civ / feature / nommé) | déplace un pion (`map_entity_pawns`) → `migration` |
| `annotate` | ✨ new | at (nommé / relatif), label? / note? | label / note MJ sur une province → `note` |
| `cedeTerritory` | ✨ optionnel | fromCiv, toCiv, at | transfert de contrôle → `diplomatic` |

> **Départ assumé du design read-only.** L'agent Aurelm était read-only (22 lectures +
> `editMemory`). Ces writes lui donnent le pouvoir de **muter le canon** — c'est voulu
> (c'est le point), mais ça impose la discipline validation/feedback/event **et**
> probablement un mode *dry-run* ou une confirmation MJ pour les mutations lourdes.

## 5. SETUP — pas des tools agent (CLI / GUI / batch)

| Truc | Statut | Forme |
|---|---|---|
| `ingest_world` | ✅ existe (fonction) | **CLI** `python -m bot.map_ingestion` — chargement d'un monde Theomen, batch, **jamais** un tool LLM |

---

## 6. Ordre de construction — ✅ TOUT LIVRÉ

1. ✅ **Socle write** : `foundSettlement` — valider / appliquer / logguer / feedback →
   le **template** de tous les writes.
2. ✅ `proposeSpawnPositions` en read-tool (il alimente `foundSettlement`).
3. ✅ `groundCivTerrain` enrichi (directions relatives, plus de `(q,r)`).
4. ✅ `findNearest` + `whatIsBetween` (les reads MJ à forte valeur).
5. ✅ `recordEvent` + `annotate` (writes narratifs génériques).
6. ✅ `expandTerritory` + `moveEntity` (writes riches).
7. ✅ `getMapOverview` refait en résumé sémantique (pour les vrais mondes).
8. ✅ CLI d'ingestion (`python -m bot.map_ingestion`).

**~10 tools** (4 existants dont 2 à retoucher, ~6 neufs) + le CLI. Tout en Python (une
source), exposable ensuite via la surface Demiurgos.

## 6bis. Fog of war (V2) + intégration Demiurgos

Les 5 points remontés par Demiurgos, résolus :
- **Source unique** : Aurelm est LA source du territoire/cités (Demiurgos déprécie ses
  `map_zones`/`map_structures`). ✅
- **Transactionnalité shadow-DB** (option A) : `beginTurn`/`commitTurn`/`abortTurn`
  encadrent un tour ; les writes carte s'accumulent sans commit, `abortTurn` les jette
  → zéro canon orphelin si le tour rollback. Orchestration-only (absent de
  tool_definitions). ✅
- **Prose** : le grounding rend **faits + labels** (nom + catégorie de feature), jamais
  la prose finie de Theomen — la plume reste au GM. ✅
- **Fog of war (V2, SPATIAL)** : `map_cell_discovery` par-civ ; la fondation/expansion
  sème la découverte du siège + voisinage, `discoverAround(civName, around, radius)`
  fait explorer, `groundCivTerrain(..., fog=true)` ne révèle que le découvert (les
  provinces voisines non explorées sont comptées, pas décrites ; `fog=false` =
  omniscience MJ). ✅

> **DETTE — « feature discover » (connaissance tech-gatée du CONTENU).** Le fog ci-dessus
> est **spatial** (voir une province). Savoir ce qu'une province **contient** — p. ex.
> qu'il y a du charbon — dépend du **tech-level** : une civ néolithique ne « découvre »
> pas le charbon. Il faut une mécanique plus fine (révéler les ressources/features d'une
> province selon la techno de la civ) — **non résolue, parkée**. Aujourd'hui, une province
> découverte montre tout son contenu.

## 7. Décisions ouvertes
- **Résolution des ancres relatives** (« vers la frontière », « au nord-est ») : jusqu'où
  on va dans la richesse au premier jet ? (défaut : directions cardinales + « vers civ X »
  + « vers feature Y »).
- **Confirmation des writes** : dry-run systématique, ou write direct + event annulable ?
- **Surface Demiurgos** : bot HTTP vs mcp-server TS (tranché plus tard, n'affecte pas la
  logique Python).
- **`getMapOverview`** sur un monde de plusieurs milliers de provinces : quel niveau
  d'agrégation (régions ? clusters de biomes ?).

## 8. Références (prior art)
- [MapAgent — Hierarchical Agent for Geospatial Reasoning](https://arxiv.org/abs/2509.05933)
- [Spatial-Agent — Agentic Geo-spatial Reasoning](https://arxiv.org/html/2601.16965)
- [From Text to Space — grid-world navigation](https://arxiv.org/pdf/2502.16690)
- [LLM commander agent, spatial reasoning in combat simulation](https://www.nature.com/articles/s41598-026-43365-3)
- [Modular harness for LLM agents in gaming environments](https://arxiv.org/html/2507.11633v1)
