# Plan d'Implémentation : Pipeline Incrémental + Progress Tracking

## Objectif

Transformer le système en architecture incrémentale permettant :
- Traiter seulement les nouveaux tours (workflow normal)
- Régénérer tout si besoin (maintenance/topping)
- Suivre la progression en temps réel pour l'UI Flutter

## Architecture Globale

### 1. Pipeline (toujours incrémental)
- **Mode normal** : Traite uniquement les tours non-traités
- **Mode `--reprocess-all`** : Marque tous les tours comme non-traités → force tout refaire
- **Granularité** : 1 tour par civ

### 2. Profiler
- **Mode incrémental (défaut)** : Met à jour seulement les entités des nouveaux tours
- **Mode `--full`** : Régénère toutes les descriptions (après amélioration prompt)
- **Granularité** : 1 entité

### 3. Wiki Generator
- **Toujours complet** : Lit l'état actuel de la DB, génère toutes les pages
- **Granularité** : 1 page

## Étapes d'Implémentation

### Phase 1 : Database Schema (15 min)

#### 1.1 Table de tracking des tours traités
```sql
CREATE TABLE IF NOT EXISTS pipeline_turn_status (
    turn_id INTEGER PRIMARY KEY REFERENCES turn_turns(id),
    processed_at TEXT,
    pipeline_run_id INTEGER REFERENCES pipeline_runs(id)
);
```

#### 1.2 Table de progression (pour Flutter)
```sql
CREATE TABLE IF NOT EXISTS pipeline_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER REFERENCES pipeline_runs(id),
    phase TEXT NOT NULL,  -- 'pipeline', 'profiler', 'wiki'
    civ_id INTEGER REFERENCES civ_civilizations(id),
    civ_name TEXT,
    total_units INTEGER NOT NULL,
    current_unit INTEGER NOT NULL,
    unit_type TEXT NOT NULL,  -- 'turn', 'entity', 'page'
    status TEXT NOT NULL,  -- 'running', 'completed', 'failed'
    started_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pipeline_run_id, phase, civ_id)
);
```

#### 1.3 Migration script
- Créer `database/migrations/003_incremental_tracking.sql`
- Ajouter helper dans `db.py` pour gérer les tables

### Phase 2 : Pipeline Incrémental (30 min)

#### 2.1 Modifier `runner.py`

**Ajouts** :
```python
def get_unprocessed_turns(conn, civ_id=None):
    """Retourne les tours qui n'ont pas été traités."""
    # Requête SQL pour trouver les turns sans entry dans pipeline_turn_status

def mark_turn_processed(conn, turn_id, run_id):
    """Marque un tour comme traité."""
    # INSERT INTO pipeline_turn_status

def mark_all_turns_unprocessed(conn):
    """Efface le tracking → force tout refaire."""
    # DELETE FROM pipeline_turn_status

def update_progress(conn, run_id, phase, civ_id, civ_name, current, total, unit_type):
    """Met à jour la progression pour Flutter."""
    # INSERT OR REPLACE INTO pipeline_progress
```

**Logique principale** :
```python
def run_pipeline(db_path, reprocess_all=False, use_llm=True):
    if reprocess_all:
        mark_all_turns_unprocessed(conn)

    civs = get_civilizations(conn)
    run_id = create_pipeline_run(conn)

    for civ in civs:
        unprocessed_turns = get_unprocessed_turns(conn, civ['id'])
        total_turns = len(unprocessed_turns)

        for i, turn in enumerate(unprocessed_turns):
            # Traiter le tour (existing logic)
            process_turn(turn)

            # Marquer comme traité
            mark_turn_processed(conn, turn['id'], run_id)

            # Update progress
            update_progress(
                conn, run_id, 'pipeline', civ['id'], civ['name'],
                i + 1, total_turns, 'turn'
            )
```

#### 2.2 Ajouter flag CLI
```python
parser.add_argument('--reprocess-all', action='store_true',
                    help='Mark all turns as unprocessed and reprocess everything')
```

### Phase 3 : Profiler Incrémental (30 min)

#### 3.1 Modifier `entity_profiler.py`

**Nouvelles fonctions** :
```python
def get_entities_from_new_turns(conn, last_profiler_run=None):
    """Retourne les entités qui apparaissent dans les tours traités depuis last_profiler_run."""
    # Si last_profiler_run is None → toutes les entités
    # Sinon → requête sur entity_mentions JOIN turn_turns WHERE processed_at > last_profiler_run

def append_turn_summaries(conn, entity_id, new_summaries):
    """Ajoute de nouveaux résumés de tours à l'historique existant."""
    # Lit history JSON actuel
    # Append les nouveaux (évite doublons)
    # UPDATE entity_entities SET history = new_json

def build_entity_profiles_incremental(db_path, model, full_reprocess=False):
    """Version incrémentale du profiler."""
    if full_reprocess:
        # Mode actuel : tout régénérer
        return build_entity_profiles(db_path, model, use_llm=True)
    else:
        # Mode incrémental
        last_run = get_last_profiler_run(conn)
        entities_to_update = get_entities_from_new_turns(conn, last_run)

        for entity in entities_to_update:
            # Récupère seulement les mentions des nouveaux tours
            new_mentions = get_new_mentions(conn, entity['id'], last_run)

            # Génère résumés pour ces tours
            new_summaries = generate_turn_summaries(new_mentions)

            # Append à l'existant
            append_turn_summaries(conn, entity['id'], new_summaries)
```

#### 3.2 Ajouter flag CLI
```python
parser.add_argument('--full', action='store_true',
                    help='Regenerate all entity descriptions from scratch')
```

#### 3.3 Progress tracking
Même logique que pipeline : `update_progress()` tous les 10 entités

### Phase 4 : Wiki Generator Progress (15 min)

#### 4.1 Modifier `generate.py`

**Ajouter callback de progression** :
```python
def generate_wiki(db_path, output_dir, progress_callback=None):
    """
    progress_callback(current, total, unit_type) si fourni
    """
    total_pages = estimate_total_pages(conn)
    current = 0

    # Pour chaque page générée
    _write_page(...)
    current += 1
    if progress_callback:
        progress_callback(current, total_pages, 'page')
```

**CLI wrapper** :
```python
def main():
    # ...existing...

    def progress(current, total, unit_type):
        # Si DB path fournie, update pipeline_progress
        if args.track_progress:
            update_progress_in_db(args.db, 'wiki', None, None, current, total, unit_type)

    generate_wiki(args.db, args.out, progress_callback=progress if args.track_progress else None)
```

### Phase 5 : API de Progression pour Flutter (20 min)

#### 5.1 Ajouter endpoint au bot HTTP server (`bot/server.py`)

```python
@routes.get('/progress')
async def get_progress(request):
    """Retourne l'état de progression actuel."""
    db_path = request.app['config'].db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Récupère le dernier run en cours
    run = conn.execute("""
        SELECT * FROM pipeline_runs
        WHERE status = 'running'
        ORDER BY id DESC LIMIT 1
    """).fetchone()

    if not run:
        return web.json_response({'status': 'idle'})

    # Récupère la progression
    progress = conn.execute("""
        SELECT * FROM pipeline_progress
        WHERE pipeline_run_id = ?
        ORDER BY updated_at DESC
    """, (run['id'],)).fetchall()

    # Format pour Flutter
    return web.json_response({
        'status': 'running',
        'run_id': run['id'],
        'started_at': run['started_at'],
        'phases': [dict(p) for p in progress]
    })
```

#### 5.2 Flutter polling (déjà existant dans BotService)
Juste adapter pour lire `/progress` au lieu de `/status`

### Phase 6 : Tests & Validation (30 min)

#### 6.1 Scénarios de test

1. **Pipeline incrémental normal**
   - État initial : 14 tours traités
   - Ajoute tour 15 dans DB
   - Lance pipeline → doit traiter seulement tour 15
   - Vérifie `pipeline_turn_status` et `pipeline_progress`

2. **Pipeline --reprocess-all**
   - Lance avec flag → doit tout refaire
   - Vérifie que tous les tours sont re-traités

3. **Profiler incrémental**
   - État initial : entités profilées pour tours 1-14
   - Lance profiler après ajout tour 15
   - Vérifie que seulement les entités du tour 15 sont mises à jour

4. **Profiler --full**
   - Lance avec flag → doit tout régénérer
   - Vérifie qualité des descriptions

5. **Progress tracking**
   - Lance pipeline → poll `/progress` pendant exécution
   - Vérifie que les barres de progression ont du sens

#### 6.2 Tests unitaires
```bash
# Ajouter dans pipeline/tests/
test_incremental_tracking.py
test_progress_api.py
```

## Résumé des Changements

### Fichiers à créer
- `database/migrations/003_incremental_tracking.sql`
- `pipeline/tests/test_incremental_tracking.py`
- `bot/tests/test_progress_api.py`

### Fichiers à modifier
- `database/schema.sql` (ajouter nouvelles tables)
- `pipeline/pipeline/db.py` (helpers pour tracking)
- `pipeline/pipeline/runner.py` (logique incrémentale + progress)
- `pipeline/pipeline/entity_profiler.py` (mode incremental + progress)
- `wiki/generate.py` (progress callback)
- `bot/server.py` (endpoint `/progress`)
- `gui/lib/services/bot_service.dart` (adapter pour `/progress`)

### Temps estimé total
~2h30 (sans compter les tests complets avec Ollama)

## Workflow Final

### Workflow Normal (Nouveau Tour)
```bash
# 1. Bot fetch nouveau tour → DB (automatique)
# 2. Pipeline incrémental
python -m pipeline.runner --db aurelm.db

# 3. Profiler incrémental (automatique après pipeline)
# Déjà intégré dans runner.py step 7

# 4. Wiki generator
python wiki/generate.py --db pipeline/aurelm.db --out wiki/docs --wiki-dir wiki
```

### Workflow Topping (Maintenance)
```bash
# Prompt amélioré → régénérer toutes les descriptions
cd pipeline
python -c "from pipeline.entity_profiler import build_entity_profiles; build_entity_profiles('aurelm.db', use_llm=True)" --full

# Pipeline bogué → tout refaire
python -m pipeline.runner --db aurelm.db --reprocess-all

# Wiki seul
python wiki/generate.py --db pipeline/aurelm.db --out wiki/docs --wiki-dir wiki
```

### Flutter UI
```
╔════════════════════════════════════════╗
║  Pipeline Progress                     ║
║  ─────────────────────────────────    ║
║  Global: 2/3 civs ███████░░░░ 66%     ║
║                                        ║
║  Civ de la Confluence:                 ║
║  Tours: 14/14 ██████████████ 100%     ║
║  Profiling: 45/187 ████░░░░░░░ 24%    ║
║  Wiki: 0/74 ░░░░░░░░░░░░░░░░ 0%       ║
╚════════════════════════════════════════╝
```
