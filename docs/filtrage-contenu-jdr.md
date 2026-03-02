# Filtrage du contenu JDR avant analyse

Comment transformer un fichier markdown brut de JDR (posts GM + réponses joueur) en phrases narratives exploitables par un LLM de vérification factuelle.

Implémenté dans `civjdr/veracite/preprocessing.py`. Applicable à tout projet qui ingère du contenu JDR markdown.

## Le problème

Un fichier de session JDR typique contient un mélange de :

```markdown
## Message du MJ
Récit narratif avec du lore canonique...          ← ON VEUT ÇA

**Choix 1 - Guerre:**
Il faut les repousser à la mer...                 ← HYPOTHÉTIQUE, PAS DU LORE

**Choix 2 - Diplomatie:**
Ne pas risquer de provoquer...                    ← HYPOTHÉTIQUE, PAS DU LORE

---

## Réponse du joueur
Narration du joueur avec assertions à vérifier... ← ON VEUT ÇA

### RÉSUMÉ DES DÉCISIONS
**Posture militaire:**                            ← TITRE DE SECTION
- Faucons au village fortifié                     ← BULLET POINT DE PLAN
- Feux allumés sur les tours                      ← BULLET POINT DE PLAN
```

Sans filtrage, un LLM fact-checker reçoit ~100 "phrases" dont ~15 sont des bullet points de résumé, des titres de section, ou des options hypothétiques du GM. C'est du bruit qui génère des faux positifs (ORANGE/ROUGE sur du contenu non-factuel).

## Pipeline de filtrage

Deux étapes : **clean_markdown** (nettoyage syntaxe) puis **extract_sentences** (filtrage sémantique).

### Étape 1 : clean_markdown — Nettoyage ligne par ligne

Parcourt le fichier ligne par ligne avec des machines à état pour les blocs multi-lignes.

| Élément | Action | Raison |
|---|---|---|
| Code blocks ` ``` ` | Skip bloc entier | Pas du contenu narratif |
| Headers `# ##` | Skip | Titres, pas des assertions |
| Séparateurs `---` | Remplacer par ligne vide | Ponctuation structurelle |
| **Blocs de choix GM** | Skip jusqu'au prochain `---` ou `#` | Options hypothétiques, pas du lore (voir détail ci-dessous) |
| Bullet points `- item` | Skip | Items de plan/résumé, pas des phrases complètes |
| Listes numérotées `1. item` | Skip | Idem |
| Blockquotes `> texte` | Garder le texte, retirer `>` | Peut contenir du dialogue |
| Bold/italic `**text**` | Retirer marqueurs, garder texte | Syntaxe pure |
| Links `[text](url)` | Garder le texte | Syntaxe pure |
| Em-dashes `--` | Normaliser en ` -- ` | Ponctuation narrative, spaCy gère |

#### Détail : filtrage des blocs de choix GM

Pattern spécifique au format JDR. Le GM propose des choix numérotés suivis de paragraphes explicatifs :

```markdown
**Choix 1 - Une grande forêt:**          ← Détection: regex ^\*{0,2}Choix\s+\d
Paragraphe d'option hypothétique...       ← Skippé (in_choice_block = True)
Autre paragraphe d'option...              ← Skippé

---                                       ← Fin du bloc (séparateur détecté)
Texte narratif qui suit...                ← Reprise normale
```

Machine à état avec **seuil de longueur** pour distinguer options et lore :

```
in_choice_block = False

# Détection du titre de choix
if regex "Choix N" → in_choice_block = True, skip la ligne

# Dans le bloc de choix :
if séparateur (---) ou header (#) → in_choice_block = False, skip
if len(ligne) > 300 chars        → in_choice_block = False, GARDER la ligne
sinon                             → skip (option courte)
```

**Pourquoi le seuil 300 chars :** le GM mélange options et narration dans le même bloc. Les options hypothétiques font 30-240 chars (1-2 phrases prescriptives). Le lore narratif intercalé fait 400-700 chars (paragraphes descriptifs avec entités, événements, géographie). Le seuil 300 sépare les deux sans ambiguïté sur le corpus actuel.

**Exemple concret du problème :**
```markdown
**Choix 1 - Évaluation du Sans-ciel:**
- de l'audace, encore de l'audace          ← option (55 chars) → SKIP
- c'est la preuve que les sans ciels...     ← option (152 chars) → SKIP

Le voyage n'est pas terminé pour les        ← lore narratif (655 chars) → GARDER
captifs. Ils entreprennent une grande
marche... On découvre qu'ils se font
appeler "Nanzagouet"...

**Choix 2 - Identité collective:**
C'est vrai ça, qui êtes vous ?              ← option (30 chars) → SKIP
```

Sans le seuil, une machine à état naïve (skip tout entre `Choix N` et `---`) perd le paragraphe lore Nanzagouet. Avec le seuil, seules les options courtes sont filtrées.

**Pourquoi c'est important pour Aurelm :** ces options sont des scénarios hypothétiques proposés par le GM ("Il faut les repousser à la mer..."). Ce n'est pas du lore canonique — c'est ce qui *pourrait* arriver selon un choix. Les indexer comme faits dans la DB d'entités ou les embedder dans un RAG produit du bruit et des résultats absurdes.

### Étape 2 : extract_sentences — Filtrage sémantique

Opère sur le texte déjà nettoyé. Split par paragraphes puis par lignes, et filtre :

| Filtre | Seuil | Raison |
|---|---|---|
| Longueur minimale | < 25 caractères | Fragments inutiles |
| Ratio alphabétique | < 40% alpha | Lignes de ponctuation/chiffres |
| Titres de section | Finit par `:` ET < 8 mots | `Posture militaire:` n'est pas une assertion |

### Résultat

Sur un fichier typique de ~230 lignes markdown :

```
Avant filtrage :  101 phrases extraites → 98 analysées par le LLM
Après filtrage :   85 phrases extraites → 84 analysées par le LLM
```

- 15 bullet points de résumé éliminés
- 1 titre de section éliminé
- Les blocs de choix GM (si présents) éliminés
- ~15% de tokens et d'appels API économisés
- Faux positifs ORANGE divisés par 2 (12 → 6 sur le benchmark mars-attack)

## Format des fichiers attendus

Le filtrage gère trois formats de fichiers JDR :

1. **Fichier réponse pure** (`reponses/*.md`) — que du joueur, pas de choix GM
2. **Fichier Background** (`Background/*.md`) — GM + choix + réponse joueur dans le même fichier
3. **nextUpdate.md** — brouillon de réponse en cours

Les blocs de choix GM n'apparaissent que dans le format 2. Les bullet points et titres de section apparaissent dans les trois.

## Réutilisation dans Aurelm

Ce pipeline de filtrage est pertinent pour tout module Aurelm qui ingère du markdown JDR :

- **Extraction d'entités** : les bullet points contiennent des noms d'entités mais sans contexte narratif → bruit pour le NER
- **Résumé de tours** : les options non-choisies polluent le résumé si elles ne sont pas filtrées
- **Embedding/RAG** : indexer des bullet points de plan donne des chunks pauvres en sémantique

La logique est dans `civjdr/veracite/preprocessing.py` — portable en ~50 lignes de Python pur (regex, pas de dépendance externe).
