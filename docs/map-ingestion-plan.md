# Plan — Ingestion carte (source Theomen) + grounding pour Demiurgos

> Réponse d'Aurelm au brief `Demiurgos/AURELM-BRIEF-map-ingestion.md`.
> **Statut : ✅ IMPLÉMENTÉ + MIGRÉ EN V2 + VALIDÉ SUR LE VRAI EXPORT V2 (2026-07-30).** Le plan
> ci-dessous a été construit ; la partie tools/agent est dans `map-tools-design.md`. Voir
> « État final » juste en dessous pour ce qui a divergé du plan à la mesure du réel.

---

## ⚠️ MISE À JOUR V2 — modèle à budget de points (2026-07-30, cassant)

Theomen a shippé le **format v2** (`export_version: 4`, contrat toujours `theomen.world.v1`).
Tout le corps du plan ci-dessous décrit le modèle **v1** (une `feature` + un `deposit` par
cellule) — **c'est périmé**. Ce que le code fait réellement aujourd'hui :

- Une province ne porte plus 1 feature + 1 gisement, mais un **ENSEMBLE d'éléments** de taille
  variable dont les points signés **somment à `budget_score`** (invariant vérifié sur le réel :
  `Natural Harbor +3, River Delta +2, Flood Plain −1` → budget 4).
- `features.json` + `deposits.json` → **un seul `elements.json`** (registre de 268 entrées,
  familles `deposit`/`landmark`/`constraint`). Les chunks portent `element_count` (uint8) +
  `element_0..7` (**uint16**, ids dans le registre).
- Chaque élément : `{name, display_name, category, family, formation_type, points, hidden_level}`
  — **pas de prose** (`description` supprimé). `hidden_level` (0=visible, >0=à prospecter)
  débloque la dette « feature discover » (porté en metadata, filtrage pas encore construit).
- Ingestion : `map_ingestion._resolve_elements` construit **`meta["elements"]`** (liste triée
  par points desc). **Zéro migration DB** (`map_cells.metadata` = blob JSON libre). Le grounding,
  `get_map_overview`, l'ancrage et `find_nearest` lisent tous la liste.
- Validé sur le vrai export v2 `theomen/blog/world_aurelm_seed42.world` (planète 1625×812,
  registre 268, invariant Σpoints==budget). 231 tests bot verts.

Le reste du document (modèle v1) est conservé pour l'historique de conception, mais **la source
de vérité est le code**, pas ce texte.

---

## État final (ce qui a réellement été livré)

- **Ingestion** : `bot/world_reader.py` (décodeur GMVC stdlib) + `bot/map_ingestion.py`
  (résolution des noms via sidecars, inversion log10 des ressources, record sémantique
  → `map_cells.metadata`, **crop-on-ingest**, idempotent) + migration 035 (`map_maps.metadata`).
  CLI : `python -m bot.map_ingestion`.
- **Deux corrections de FORMAT** que le contrat gelé n'avait pas cernées, attrapées par le
  **vrai export** (`theomen/blog/world_aurelm_seed42.world`, planète 1625×812) — le SPEC
  Theomen ment sur ces deux points, à corriger côté doc Theomen :
  1. Les métadonnées business (`cell_km`, `wrap_x`, `thresholds`, `max_mass` des couches) sont
     dans **`manifest["producer"]`**, PAS un `world.json` séparé. Le reader lit `producer`
     (fallback `world.json`).
  2. Les sidecars (`biomes.json`, `terrain_types.json`, `deposits.json`, `features.json`) sont
     **wrappés** sous leur clé plurielle (`{"biomes":[...]}`), pas des listes nues. Le reader
     tolère les deux ; les fixtures miroir le vrai format.
  3. Piège du décode déjà noté : le `coord.x/coord.y` d'un chunk GMVC est un **INDEX de chunk**,
     pas une origine cellule (origine = coord × chunkDims).
- **Validation complète sur le réel** (`bot/tests/test_real_world_export.py`, opt-in) : cell_km
  20, wrap_x, 30 biomes, terrain/biome/gisements nommés+gradués/features/rivières
  (bassin km²)/`resource_potential` (inversion max_mass) résolvent tous. Probe live-LLM :
  `bot/tests/live_map_probe.py`.
- **Seeding + tools + fog + transactionnalité de tour** : voir `map-tools-design.md`.

**Leçon (réaffirmée) : un fixture fidèle au spec cache un bug de forme réelle — seul le
vrai fichier tranche.** (2× : coord-index, puis biomes-wrap + producer-block.)

---

## 0. Ce qui a été constaté (base du plan)

**Côté Aurelm (cible)** — migrations 031-034, `bot/tools.py`, `bot/tests/conftest.py` :
- `map_maps(id, name UNIQUE, grid_type∈{hex,square}, grid_cols, grid_rows, parent_map_id, parent_cell_q/r)`.
- `map_cells` : **PK composite `(map_id, q, r)`**, pas d'`id`. Colonnes utiles : `terrain_type` (TEXT libre, défaut `plain`), `controlling_civ_id`, `entity_id`, `label`, `child_map_id`, **`metadata` (TEXT = blob JSON, "resources, notes…")**.
- **Aucun writer prod n'existe** (Python) : seuls les fixtures de test écrivent des cartes. La GUI (`map_dao.dart`) écrit les cartes de l'éditeur interactif, mais **ne peuple jamais `metadata`**. → l'ingestion est **greenfield** côté Python.
- `metadata` : défini mais **jamais écrit**, **aucun contrat de clés** existant, et **seul `get_cell` l'affiche** (brut, tronqué 200). `get_map_overview` (le tool naturel pour le grounding) ne montre que `q,r,terrain,label,civ,entité` (LIMIT 200).
- Vocab `terrain_type` de facto (fixtures) : `plain, forest, mountain, river, ruins` (non contraint).

**Côté Theomen (source)** — `core/World.h`, `core/mapexport/` :
- Grille **carrée** row-major W×H (pas hex). `Tile` porte : `elevation_m`, `temperature_c`, `humidity`, `soil_type/soil_depth`, **biome** (index → `gameData/Biomes/*.json`, chaque biome a un `map_color`), **hydrologie** (`flow_dir`, `flow_accum`, `water`=débit rivière/profondeur lac), **`resource_deposit_id`** (gisement nommé gradué), `feature_id` (landmark), `budget_score`.
- **Un exporteur existe déjà** : `writeWorldDocument` → dossier `.world` (manifest + chunks binaires) pour un viewer, avec **une frontière qui traduit le vocabulaire Theomen en noms NEUTRES** (`elevation`, `res_<type>`, `biome`). Sidecars JSON à contrat neutre déjà en usage (`core.json`, `CoreSidecarWriter`). Downsample LOD supporté ; **crop région : non** (à confirmer).

**Conséquence clé** : la grille carrée de Theomen mappe **1:1** sur `map_cells` avec `grid_type='square'`, `q=x`, `r=y`. Aucune conversion hex, aucun resampling.

---

## 1. LE CONTRAT D'INGESTION *(priorité — pilote Theomen)*

**Décision de forme proposée** : le `.world` binaire est fait pour un *viewer* (rasters elevation/densité). Aurelm est le **magasin canon structuré** et doit servir du **grounding sémantique** au GM (« cette cellule : biome *gallery_forest*, rivière débit 900, *rich_iron_ore* tier 3 »). Donc **on ne parse pas le `.world` binaire** (ça forcerait Aurelm à embarquer les catalogues d'index Theomen = couplage). On demande à Theomen un **export structuré par-cellule avec les noms déjà résolus**, exactement dans l'esprit de sa frontière `core.json` existante.

### Format (2 fichiers, un dossier `region.world-export/`)

**`header.json`** — métadonnées carte :
```jsonc
{
  "contract_version": "1.0",
  "world_seed": 42,
  "region": { "x0": 800, "y0": 300, "w": 96, "h": 64 },   // bbox dans le monde Theomen
  "cell_km": 20,                                            // taille d'une cellule
  "grid_type": "square", "cols": 96, "rows": 64,
  "terrain_legend": ["ocean","lake","plain","forest","hills","mountain","desert","wetland","tundra","ice"],
  "biome_palette": { "gallery_forest": "#3f7d3f", "alpine": "#c9d6e0", "...": "#..." }  // depuis biome_index map_color
}
```

**`cells.ndjson`** — un objet JSON par ligne, une ligne par cellule (streamable) :
```jsonc
{ "x": 0, "y": 0,
  "terrain_type": "forest",          // catégorie GROSSIÈRE (peinture + tools de lecture) — dérivée par Theomen de biome+élévation+eau
  "biome": "gallery_forest",         // biome_id fin (nom résolu)
  "elevation_m": 340.0,
  "temperature_c": 18.5,
  "is_water": false,                 // océan/lac
  "river": { "is_river": true, "flow": 912.0 } ,  // depuis water/flow_accum ; null si pas de rivière
  "resources": [ { "name": "rich_iron_ore", "tier": 3 } ],   // resource_deposit_id résolu + gradé
  "feature": "canyon"                // feature_id résolu, ou null
}
```

**Règles du contrat** :
- **Noms résolus côté Theomen** (biome_id, resource name, feature name) — Aurelm ne connaît aucun index. C'est la frontière (comme `res_<type>` / `core.json`).
- **`terrain_type`** = petit vocabulaire contrôlé (`terrain_legend`), dérivé par Theomen — c'est ce que peignent la GUI et les tools de lecture actuels. Le **biome fin** vit à part.
- **Région, pas planète** (cf. [À TRANCHER] #1).
- **Versionné** (`contract_version`) — un champ ajouté n'est jamais cassant (Aurelm ignore l'inconnu).

### Mapping Aurelm (ingestion)
- `header.json` → 1 ligne `map_maps` (`name`=nom de partie/région, `grid_type='square'`, `grid_cols=cols`, `grid_rows=rows`).
- chaque `cells.ndjson` → 1 upsert `map_cells (map_id, q=x, r=y, terrain_type)` + **`metadata` = JSON** `{biome, elevation_m, temperature_c, is_water, river, resources, feature}`.
- `biome_palette`, `region`, `cell_km`, `world_seed` → stockés au niveau carte (dans un `map_cells` pseudo ? non — dans `metadata` de la carte : **[À TRANCHER mineur]** `map_maps` n'a pas de colonne `metadata` ; option : une table `map_meta` 1-ligne, ou réutiliser une convention. Recommandation : petite extension `map_maps.metadata TEXT` (migration 035, additive, non cassante) pour porter seed/région/palette).

---

## 2. Réponses aux 3 [À TRANCHER] *(je propose, tu tranches — #1 avec Theomen, #3 avec Demiurgos)*

**#1 — Échelle / région.** → **Theomen crope une région (bbox) à l'export**, à la résolution de jeu (son downsample LOD donne déjà le levier résolution). Aurelm ingère une région, **jamais** un globe.
- *Pourquoi* : Aurelm est le canon **par-partie** ; une planète (~1.3M cellules) n'est ni utile ni voulue ; Theomen possède le monde et a déjà le LOD.
- *Décision à remonter à Theomen* : ajouter un **param de crop bbox** à `writeWorldDocument` (aujourd'hui seulement `downsample`), + fixer la **taille cible de région** (reco : ≤ ~128×128 ≈ 16k cellules, à confirmer selon ce qu'une partie Demiurgos couvre).

**#2 — Richesse par-cellule vs schéma.** → **`metadata` JSON** (jeu de clés versionné), **pas** de colonnes typées sur `map_cells`.
- *Pourquoi* : ne casse aucun tool de lecture (contrainte dure), DB-par-partie, `metadata` **est** l'escape hatch prévu, et le grounding ne lit qu'une poignée de cellules voisines (parse JSON négligeable). `terrain_type` reste la catégorie de peinture. On **étend** `get_map_overview`/`get_cell` pour faire remonter biome/rivière/ressources (additif).
- *Ma reco ferme* ; override possible si tu veux des colonnes typées (coût : migration + risque sur les lectures).

**#3 — Granularité du grounding.** → cellule d'origine de la civ **+ anneau de rayon N (défaut 2)** : par-cellule terrain/biome/rivière/ressources + features notables à portée, format structuré consommable par le GM.
- *À caler avec Demiurgos* : rayon exact, quels champs, format (Markdown structuré vs JSON) que son Context Agent préfère.

---

## 3. Découpage en étapes (TDD, après validation)

| # | Étape | Livrable | Test qui verrouille |
|---|---|---|---|
| **S1** | **Publier le contrat** (§1) | Contrat figé, partagé à l'agent Theomen | — (bloque Theomen) |
| **S2** | Stub fixture | Un petit export région (~8×8) écrit à la main sous `bot/tests/fixtures/`, conforme au contrat | sert de source de test |
| **S3** | `map_ingestion` | fonction `ingest_world(conn, export_dir, map_name)` : upsert `map_maps` + `map_cells`(+metadata), **idempotent** (ré-ingest = remplace les cellules de la carte) ; CLI `python -m bot.map_ingestion` | rouge→vert : ingère le stub → N `map_cells`, clés `metadata` présentes, `get_map_overview` montre terrains/biomes ; **non-régression** : les tests des 6 tools restent verts |
| **S4** | Placement civ | assigner `controlling_civ_id` à la/les cellule(s) d'origine d'une civ (param du contrat OU appel séparé) | rouge→vert : civ placée → `get_territory` la voit |
| **S5** | Tool de grounding | nouveau tool `groundCivTerrain(civName, radius)` + schéma ; rend le terrain local structuré ; réutilise/étend le rendu de `get_map_overview` (surface biome/rivière/ressources depuis metadata) | rouge→vert : grounding rend cellule+anneau avec ressources ; **les 6 tools existants inchangés** |

Extension transverse : faire remonter les nouvelles clés `metadata` dans `get_map_overview`/`get_cell` (additif, testé).

---

## 4. Contraintes tenues (rappel du brief)
- ✅ Ne casse aucun tool de lecture → S3/S5 gardent la suite map verte + tests neufs.
- ✅ DB par-partie uniquement → l'ingestion prend un chemin de DB explicite ; ne touche aucune DB canon partagée.
- ✅ Ne code pas l'export Theomen → on propose le contrat ; **stub fixture** pour tester sans Theomen.
- ✅ Pas de génération de terrain dans Aurelm → on ingère et sert, point.

---

## 5. Ce que j'attends de toi (validation)
1. **Valide le CONTRAT (§1)** — surtout la forme (export structuré NDJSON+header vs parser le `.world`). C'est ce qui débloque Theomen.
2. **Tranche #1** (Theomen crope la région ? taille cible ?) et **#2** (metadata JSON — je recommande oui).
3. **#3** : je m'aligne avec l'agent Demiurgos sur le format de grounding, ou tu fixes le rayon/champs.
4. Emplacement du module (`bot/map_ingestion.py` + CLI) et la petite migration 035 (`map_maps.metadata`) — OK ?
