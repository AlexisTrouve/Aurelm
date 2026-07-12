# Aurelm — Moteur générique : cahier des charges (WANT + NICE-TO-HAVE)

> **But du doc :** transformer Aurelm (aujourd'hui un toolkit MJ pour JDR de civ sur Discord) en un
> **moteur générique entité-relation + exports headless**, réutilisable par n'importe quel « customer »
> (n'importe quel corpus). Ce fichier est autoportant : il contient l'état actuel d'Aurelm nécessaire
> pour attaquer sans re-investiguer. Rédigé depuis une autre session ; à exécuter dans une session ancrée sur Aurelm.

---

## 0. Vision en une phrase
Un **customer** = un corpus → sa propre DB Aurelm. Depuis ce corpus, Aurelm **extrait** entités/relations/mentions/historique,
puis **exporte en headless** : une **mindmap image**, un **glossaire**, un **historique par entité**. Générique, baked-in, pas de module par customer.

## 1. Règle DURE, non négociable (garde-fou du plan agressif)
- **La pipeline civ existante reste VERTE à chaque étape.** Aurelm est un produit VIVANT (bot Discord, Demiurgos, veracite tournent dessus).
  Avant/après chaque changement : test de non-régression sur une DB civ réelle (ex. une `*.aurelm.db` de Demiurgos) →
  les entités/relations/wiki s'extraient toujours. Le chemin Discord/MJ-PJ n'est jamais retiré, seulement rendu optionnel.
- **Surgical + flag merdier** : `pipeline/runner.py` est un monolithe ~700 lignes avec un `TODO REFACTOR`. On ne le démonte pas au passage ; on branche proprement, on flag ce qui pue.

## 2. État actuel d'Aurelm (les seams à exploiter / les blocages à défaire)

**Seams déjà là (à réutiliser, ne pas réinventer) :**
- **Extraction déjà VERSIONNÉE** : `pipeline/pipeline/extraction_versions/v1..v22.py`, dataclass `ExtractionVersion` (prompts + schémas + vocab par version). → point d'ancrage naturel pour un profil d'extraction non-civ.
- **Exporteur headless déjà prouvé** : `wiki/generate.py` (`generate_wiki`) lit la DB en direct via `sqlite3`, a un `main()`/CLI, **pas couplé au Flutter**. Produit déjà : fiches entité (description, aliases, relations, **timeline**), listes-glossaire (`generate_civ_entities`/`generate_global_entities`), timeline (`get_entity_timeline`, `generate_global_timeline`), contexte (`get_entity_context_samples`). → **template des exporteurs.**
- **Couche LLM agnostique** : `pipeline/pipeline/llm_provider.py` (`OllamaProvider`, `OpenRouterProvider`, `claude_proxy` = etheryale). Modèle/prompt par stage via `load_llm_config`.
- **Schéma core neutre** : `database/schema.sql` → `entity_entities` (id, canonical_name, entity_type, description, **history** = JSON events, first/last_seen_turn, is_active), `entity_aliases`, `entity_mentions` (entity↔turn + context), `entity_relations` (source, target, relation_type, description, turn_id). Ces 4 tables sont **domain-neutres**.

**Blocages à défaire pour « générique » :**
- **Ontologie HARDCODÉE + recopiée dans les prompts** : `VALID_ENTITY_TYPES` (`entity_filter.py`), `VALID_RELATION_TYPES` (`entity_profiler.py`), et les mêmes listes en dur DANS les strings de prompts (`extraction_versions/v*.py`, `entity_profiler.PROFILE_PROMPT`). → la rendre config = **templater les prompts aussi**.
- **Prompts = constantes FR/JDR** ; vocab de domaine `THEMATIC_TAGS`/`TECH_ERAS`/`FANTASY_LEVELS` (`summarizer.py`) ; `_GENERIC_FRENCH_NOUNS`/noise regex FR (`entity_filter.py`).
- **Ingestion couplée Discord + tours MJ/PJ + `civ_id`** : `loader.py`, `chunker.py`, `ingestion.py`, `runner.GM_AUTHORS`, schéma (`turn_raw_messages.discord_*`, `turn_turns`, `subject_subjects.direction` CHECK `mj_to_pj`/`pj_to_mj`). Pas de notion « customer » au-dessus de la civ.
- **Aucun rendu d'image** nulle part. Aucune lib graphe dans `pipeline/requirements.txt` (juste spacy/ollama/pydantic). Le graphe est 100% Flutter écran (`gui/lib/screens/graph/*`), **non réutilisable en headless**.

## 3. CE QU'ON VEUT (les 3 phases)

### P1 — Exporteurs headless baked-in  *(indépendant, faible risque, valeur immédiate)*
Modules **neufs**, standalone, read-only sur les tables neutres, CLI type `aurelm export <kind> --db X ...`. Marchent sur N'IMPORTE quelle DB Aurelm (donc servent aussi les DBs civ existantes).
- **graph** → image (PNG **et** SVG). Layout **radial ego-graph** centré sur une entité (`--center`), anneaux par profondeur (`--depth`), **filtre par type** (`--filter entity_type=person`), nœuds colorés par `entity_type`, arêtes colorées/labellées par `relation_type`. Rendu **self-contained** (voir §5).
- **glossary** → md + json : par entité `canonical_name` + `description` + `aliases` (+ statut actif/inactif). Généralise `generate_civ_entities`.
- **history** → md + json : `entity_entities.history` (events chrono) + `entity_mentions` par tour + first/last_seen. Réutilise `get_entity_timeline`/`get_entity_context_samples`.
- Sorties en **double format** : machine (json) + humain (md/png) pour qu'elles composent (embed PDF, wiki, etc.).
- **Zéro texte FR hardcodé** dans ces modules (titres/couleurs/labels → config).

### P2 — Ontologie configurable  *(chemin critique : sans ça, pas d'extraction non-civ)*
- Sortir `entity_type` + `relation_type` + les prompts des constantes Python vers des **profils de domaine** (fichier/config par customer).
- Profil **`civ`** = comportement actuel, inchangé. Profil **`novel`** = ontologie du roman (§6).
- **Templater les prompts** pour que le vocab ne soit plus dupliqué (une seule source de vérité par profil, injectée dans le prompt).
- Rendre le vocab summarizer (`THEMATIC_TAGS`/`TECH_ERAS`/`FANTASY_LEVELS`) **par profil ou optionnel**.
- Utiliser le seam `ExtractionVersion` (ne pas repartir de zéro).

### P3 — Ingestion générique  *(la lourde, derrière le garde-fou)*
- **Loader de corpus générique** (documents/chapitres → turns/segments) **à côté** du loader Discord (pas à la place).
- Assouplir le schéma : `discord_*` **nullable/optionnels**, modèle de « turn » généralisé, relâcher le CHECK `subject_subjects.direction`.
- **`civ_id` réutilisé comme scope = customer** (le moins de churn), ou un concept tenant si nécessaire. Le chemin Discord reste fonctionnel.

## 4. Modèle « customer / tenant »
- **Un customer = une DB** (`civjdr_roman.aurelm.db`, comme Demiurgos a la sienne). Les exporteurs prennent `--db` → agnostiques du customer, **zéro changement de schéma requis pour P1**.
- Dans une DB, `civ_id` sert de scope interne si besoin de multi-scope.

## 5. CE QU'ON PENSE BIEN (opinions / nice-to-have)
- **Rendu image self-contained** : `networkx` + `matplotlib` (pur Python, embarque une police, gère le **CJK**), PAS de navigateur headless (Edge headless est **non fiable** sur la machine cible ; on a déjà basculé nos PDF sur reportlab/PyMuPDF pour ça). Alternative : Graphviz/DOT si rendu hiérarchique généalogique voulu (binaire système).
- **Mimer le look de l'ego-graph Flutter d'Aurelm** (radial, centré, anneaux par depth, couleur nœud=type, couleur arête=relation) — s'inspirer de `gui/lib/models/graph_data.dart` (modèle) et `ego_painter.dart` (layout radial) pour le style, sans réutiliser le code Flutter.
- **`entity_aliases` = couche multilingue de noms** : `canonical_name` + aliases par langue → peut servir de **registre de noms cross-langue** (pertinent pour le roman FR/EN/ZH, qui a déjà ce besoin).
- **Réutiliser le proxy etheryale** (`claude_proxy` dans `llm_provider`) pour l'extraction si on ne veut pas d'Ollama local.
- **Tout piloté par config/profil** (ontologie, prompts templatés, styles d'export) → un fichier profil par customer.
- **CJK first-class dans l'export image** (police embarquée) — le roman est en chinois.
- **P1 et P2 parallélisables** (fichiers quasi disjoints : P1 = nouveaux modules ; P2 = entity_filter/entity_profiler/extraction_versions). P3 derrière, seule à toucher schéma/loader/chunker.

## 6. Customer #1 concret : le roman (cas de test réel)
- **Repo source du corpus** : `../civjdr_roman` (chapitres FR canoniques `chapitres/CHAP_T*.md`) ; état structuré dans `etat/personnages/*` + `etat/noms.md` (noms FR/EN/ZH) + `etat/fils/`, `etat/lignees/`.
- **Ontologie « novel » :**
  - `entity_type` visé pour la mindmap : **`person`** (le filtre « persos, pas le reste »).
  - `relation_type` : **`parent-de`, `marié-à`, `mentor-de`** (ex. Shaman↔apprenti), **`héritier-du-geste`** (lignée *thématique*, non génétique — cœur du roman), **`même-peuple`**, **`immortel/observe`** (l'Oracle vs les mortels).
- **Personnages actuels** (T5-T7) : Oracle (immortel), Pluie-Menue, Front-Levé, Doigts-de-Craie, Grain-de-Suie, Bec-Calme, Cendre (grue), Mère-des-Braises, Suie-d'Aval, Aube-Grise.
- **Attention low-trust** : les liens intimes (qui est mère de qui, qui refuse qui) sont le cœur du roman → l'extraction ne doit pas les halluciner. Prévoir soit une extraction vérifiable, soit une amorce depuis `etat/` (déterministe) puis enrichissement LLM.

## 7. Décisions à trancher au moment du build
- **Comment remplir la DB du roman** : extraction LLM d'Aurelm sur les chapitres (le choix d'Alexi : « Aurelm doit faire le taff ») **avec le profil `novel`** — vs amorce déterministe depuis `etat/`. (Défaut retenu : Aurelm extrait, profil `novel`, mais garder l'option d'amorce vu le low-trust sur l'intime.)
- **Où vivent les exporteurs** : dans `pipeline/` ou un package `exporters/` neuf ? (préférence : package autonome, testable seul, comme `wiki/`).
- **Lib image** : `networkx+matplotlib` (reco) vs Graphviz.
- **Format de config des profils de domaine** : un JSON/YAML par profil vs étendre `ExtractionVersion`.

---

*Ordre d'attaque conseillé : P1 (exporteurs, livre vite + sert les DBs civ) ∥ P2 (ontologie, débloque le non-civ) en parallèle ; P3 (ingestion) ensuite, derrière le garde-fou civ-vert. Roman = customer #1 end-to-end une fois P1+P2 (+ ingestion légère) en place.*
