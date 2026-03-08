# Dashboard Enrichi — Implémentation Phase 3

## Objectif
Créer un dashboard riche pour `index.md` qui exploite les données DB avec statistiques, graphes ASCII, top entités et derniers tours.

## Fonction Implémentée

### `generate_enriched_index(conn: sqlite3.Connection) -> str`

Génère le dashboard enrichi avec :
1. **Table de statistiques globales** (tours, entités, mentions, technologies, ressources)
2. **Graphe ASCII d'activité par mois** (utilise `get_activity_by_month()`)
3. **Top 10 entités avec barres ASCII** (mentions proportionnelles)
4. **Derniers 5 tours** avec preview du summary et date Discord
5. **Navigation rapide** vers les sections principales

## Exemple de Rendu

```markdown
# Wiki Aurelm

Bienvenue sur le wiki automatise du monde d'Aurelm. Ce wiki est genere a partir des tours de jeu Discord.

## Statistiques globales

| Tours | Entites | Mentions | Technologies | Ressources |
|-------|---------|----------|--------------|------------|
| **14** | **55** | **162** | **36** | **49** |

## Activite par mois

```
Sept 2024    ████████████████████ 4 tours
Oct 2024     ███████████████      3 tours
Nov 2024     █████                1 tours
Dec 2024     █████                1 tours
Jan 2025     █████                1 tours
Fev 2025     █████                1 tours
Mars 2025    █████                1 tours
Avr 2025     █████                1 tours
Mai 2025     █████                1 tours
Juin 2025    ██████████           2 tours
Juil 2025    █████                1 tours
Aout 2025    ██████████           2 tours
Sept 2025    █████                1 tours
Oct 2025     █████                1 tours
Nov 2025     █████                1 tours
Jan 2026     █████                1 tours
```

## Top 10 Entites (par mentions)

1. **La confluence** (place) ████████████████████ 19 mentions
2. **Ailes-Grises** (caste) ██████████████       14 mentions
3. **Sans ciel** (caste) █████████            9 mentions
4. **Regards-Libres** (caste) ████████             8 mentions
5. **Enfants du Courant** (caste) ███████              7 mentions
6. **Enfants des échos** (caste) ███████              7 mentions
7. **Voix de l'Aurore** (caste) ██████               6 mentions
8. **Passes-bien** (caste) ██████               6 mentions
9. **Faucons Chasseurs** (caste) ██████               6 mentions
10. **Cercle des sages** (institution) █████                5 mentions

## Derniers tours

- **[Tour 14](civilizations/civilisation-de-la-confluence/turns.md#tour-14)** — *08/09/2025* — La narration concerne l'univers de Gouffre Humide et les Ailes-Grises, où un peuple adore les premie...
- **[Tour 13](civilizations/civilisation-de-la-confluence/turns.md#tour-13)** — *19/08/2025* — La civilisation de la Confluence traverse une période difficile après la disparition d'un groupe dan...
- **[Tour 12](civilizations/civilisation-de-la-confluence/turns.md#tour-12)** — *10/06/2025* — Un cadavre a été découvert dans le village de la Confluence, et une dispute éclate entre les habitan...
- **[Tour 11](civilizations/civilisation-de-la-confluence/turns.md#tour-11)** — *22/05/2025* — La civilisation de la Confluence poursuit son développement avec la construction de nouveaux bâtimen...
- **[Tour 10](civilizations/civilisation-de-la-confluence/turns.md#tour-10)** — *20/03/2025* — Le Maitre du Jeu décrit sa visite dans les villages de la vallée et ses observations sur les changem...

## Navigation rapide

- **[Civilisations](civilizations/index.md)** — Vue d'ensemble des civilisations
- **[Timeline globale](global/timeline.md)** — Chronologie complete
- **[Index des entites](global/entities.md)** — Toutes les entites par type
- **[Pipeline](meta/pipeline.md)** — Statistiques du pipeline ML

---

*Derniere mise a jour : 13/02/2026 17:31*
```

## Détails Techniques

### Graphe d'activité par mois
- Utilise `get_activity_by_month(conn, civ_id=None)` pour récupérer les données
- Bars ASCII proportionnels (max 20 caractères)
- Format : `Sept 2024    ████████████████████ 4 tours`
- Gère les mois sans date (fallback: `(non date)`)

### Top 10 entités
- Requête SQL : `COUNT(m.id) as mention_count` groupé par entité
- Filtre les entités noise avec `is_noise_entity()`
- Bars ASCII proportionnels (max 20 chars)
- Format : `1. **Nom** (type) ████████████████████ N mentions`

### Derniers tours
- Joint avec `turn_raw_messages` pour récupérer les timestamps Discord
- Format de date : `dd/mm/yyyy`
- Preview du summary (max 100 chars)
- Liens vers `civilizations/{civ_slug}/turns.md#tour-{N}`

### Statistiques globales
- Technologies/Ressources : Compte les éléments dans les JSON fields
- Parse avec `_parse_json_list()` pour sécurité

## Utilisation

### Dans le générateur principal
```python
from generate import generate_enriched_index

# Remplacer l'appel à generate_index() par :
_write_page(out / "index.md", generate_enriched_index(conn))
```

### Test standalone
```python
from generate import generate_enriched_index, get_connection

conn = get_connection('aurelm.db')
output = generate_enriched_index(conn)
print(output)
conn.close()
```

## Dépendances

### Fonctions utilisées
- `get_activity_by_month(conn, civ_id)` — Ligne 329
- `_parse_json_list(json_str)` — Helpers existants
- `_clean_summary(summary)` — Helpers existants
- `is_noise_entity(name)` — Filtre entités bruit
- `_capitalize_entity(name)` — Capitalisation display
- `slugify(name)` — Conversion en slug URL

### Schema DB requis
- `turn_turns` : `id`, `turn_number`, `summary`, `technologies`, `resources`, `civ_id`, `raw_message_ids`
- `entity_entities` : `id`, `canonical_name`, `entity_type`
- `entity_mentions` : `id`, `entity_id`, `turn_id`
- `turn_raw_messages` : `id`, `timestamp`
- `civ_civilizations` : `id`, `name`

## Migration vers Dashboard Enrichi

### Option 1 : Remplacement total
Modifier `generate_wiki()` ligne 1449 :
```python
# Avant :
_write_page(out / "index.md", generate_index(conn))

# Après :
_write_page(out / "index.md", generate_enriched_index(conn))
```

### Option 2 : Deux versions
Garder `generate_index()` pour compatibilité, ajouter option CLI :
```python
parser.add_argument("--enriched-index", action="store_true",
                    help="Use enriched dashboard (Phase 3)")

# Dans generate_wiki() :
if enriched_index:
    _write_page(out / "index.md", generate_enriched_index(conn))
else:
    _write_page(out / "index.md", generate_index(conn))
```

## Tests

### Test avec DB réelle
```bash
cd /c/Users/alexi/Documents/projects/Aurelm
python -c "
import sys
sys.path.insert(0, 'wiki')
from generate import generate_enriched_index, get_connection

conn = get_connection('aurelm.db')
output = generate_enriched_index(conn)

with open('wiki_index_preview.md', 'w', encoding='utf-8') as f:
    f.write(output)
print('Generated: wiki_index_preview.md')
conn.close()
"
```

### Vérifications
- ✅ Stats globales correctes (14 tours, 55 entités, 162 mentions)
- ✅ Graphe d'activité avec dates réelles (Sept 2024 - Jan 2026)
- ✅ Top 10 entités filtrées (pas de noise)
- ✅ Barres ASCII proportionnelles
- ✅ Derniers tours avec dates Discord et preview
- ✅ Liens fonctionnels vers pages de tours

## Améliorations Futures

### Phase 3.1 : Graphes avancés
- Ajouter graphe d'évolution du nombre d'entités par tour
- Timeline des technologies découvertes
- Distribution des types d'entités (pie chart ASCII)

### Phase 3.2 : Stats par civilisation
- Section "Civilisations actives" avec mini-stats
- Derniers tours **par civ** (pas seulement global)

### Phase 3.3 : Recherche rapide
- Top 10 entités **cliquables** (liens directs vers pages entités)
- Afficher les aliases dans le top 10

## Status
- ✅ **Phase 3 : Dashboard enrichi** — TERMINÉ
- Fonction : `generate_enriched_index()` — Ligne 466
- Tests : Validés avec `aurelm.db` (14 tours, 55 entités)
- Preview : `wiki_index_preview.md` généré avec succès

---

*Implémentation par Agent Dashboard — 13/02/2026*
