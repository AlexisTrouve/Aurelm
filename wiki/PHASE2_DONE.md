# Phase 2 : Pages individuelles de turns — Implémentation terminée

## Fonctions créées

### `generate_turn_page(conn, turn_id, civ_name, player_name)`
Génère une page détaillée pour un tour individuel.

**Structure de la page générée :**
1. **Header** : Titre avec numéro de tour, date Discord, nombre de segments et nouvelles entités
2. **Statistiques du tour** : Entités découvertes, mentions totales, technologies, ressources, densité narrative
3. **Ambiance** : Liens YouTube (si présents)
4. **Question du Maître du Jeu** :
   - Récit (segments narrative + description)
   - Choix proposés (de structured facts ou segments choice)
5. **Réponse de [Joueur]** : Messages du joueur séparés du MJ
6. **Conséquences** : Segments consequence (si présents)
7. **Découvertes** : Géographie, Technologies, Ressources, Croyances
8. **Entités mentionnées** : Liste avec nombre de mentions et marqueur ⭐ pour première apparition
9. **Messages Discord originaux** : Séparés par auteur (MJ vs Joueur)

**Fonctionnalités :**
- Séparation claire GM vs Player
- Gestion robuste des colonnes optionnelles (try/except pour KeyError)
- Nettoyage du contenu avec `_clean_segment_content()`
- Détection automatique du GM via `_detect_gm_authors()`
- Downgrade des headers dans le contenu (### → ####) pour éviter les collisions

### `generate_turn_index(conn, civ_id, civ_name)`
Génère la page index des tours (`turns/index.md`).

**Structure :**
- En-tête avec nombre total de tours
- Pour chaque tour :
  - Lien vers `turn-{N:02d}.md`
  - Date Discord
  - Nombre d'entités mentionnées
  - Preview du résumé (150 chars)

## Fichiers créés

1. **`wiki/turn_page_generator.py`** : Module contenant les deux fonctions
2. **`wiki/test_turn_pages.py`** : Script de test

## Intégration

Les fonctions sont importées dans `generate.py` :
```python
from turn_page_generator import generate_turn_index, generate_turn_page
```

## Tests

✅ Test réussi avec la base `aurelm.db` :
- `generate_turn_index()` : 953 caractères générés
- `generate_turn_page()` : 5856 caractères générés
- Séparation GM/Player fonctionnelle
- Structured facts affichés correctement
- Gestion robuste des colonnes manquantes

## Utilisation

```python
from generate import get_connection
from turn_page_generator import generate_turn_page, generate_turn_index

conn = get_connection("path/to/aurelm.db")

# Générer l'index
index_md = generate_turn_index(conn, civ_id=1, civ_name="Civilisation de la Confluence")

# Générer une page de tour
turn_md = generate_turn_page(conn, turn_id=5, civ_name="Civilisation de la Confluence", player_name="Rubanc")

# Écrire les fichiers
Path("docs/civilizations/civilisation-de-la-confluence/turns/index.md").write_text(index_md)
Path("docs/civilizations/civilisation-de-la-confluence/turns/turn-01.md").write_text(turn_md)
```

## Notes importantes

- La fonction `generate_civ_turns()` existante **n'a PAS été modifiée** pour maintenir la compatibilité.
- Les nouvelles fonctions utilisent les helper functions existantes via import relatif.
- Gestion d'erreur robuste pour les colonnes qui peuvent manquer dans les anciennes migrations.
- Format de fichier : `turn-{N:02d}.md` (ex: `turn-01.md`, `turn-14.md`).

## Prochaines étapes (Phase 3+)

Pour intégrer complètement ces fonctions dans le générateur principal :
1. Modifier `generate_wiki()` pour créer le dossier `turns/` et appeler ces fonctions
2. Mettre à jour la navigation dans `mkdocs.yml` pour inclure les pages de turns
3. Optionnellement : déprécier `generate_civ_turns()` après migration complète
