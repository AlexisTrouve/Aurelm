# Wiki Refactor Plan

## Objectif
Transformer le wiki actuel en un wiki riche exploitant TOUTES les données DB avec une structure claire séparant Question MJ / Réponse Joueur.

## Données DB disponibles (non exploitées)
- ✅ Segments typés (narrative/choice/consequence/ooc)
- ✅ Entity history (JSON structuré)
- ✅ Entity mentions avec context
- ✅ Timestamps Discord réels
- ✅ Co-occurrences d'entités calculables
- ✅ Author separation (GM vs Player)
- ✅ Technologies/resources/beliefs/geography par tour

## Structure finale

```
wiki/docs/
├── index.md                          ← Dashboard enrichi avec graphes
│
├── civilizations/
│   └── civilisation-de-la-confluence/
│       ├── overview.md               ← Stats + évolution
│       ├── turns/
│       │   ├── index.md              ← Liste avec previews
│       │   ├── turn-01.md            ← Pages individuelles (14 fichiers)
│       │   └── ...
│       ├── entities/
│       │   ├── index.md              ← Trié par mentions + graphes
│       │   └── [slug].md             ← Enrichi avec co-occurrences + timeline
│       ├── knowledge/                ← NOUVEAU
│       │   ├── technologies.md       ← Arbre tech chronologique
│       │   ├── resources.md          ← Index ressources
│       │   ├── beliefs.md            ← Évolution croyances
│       │   └── geography.md          ← Carte textuelle
│       └── analytics.md              ← NOUVEAU : Stats avancées
│
└── global/
    ├── timeline.md                   ← Timeline avec dates Discord
    ├── entity-network.md             ← NOUVEAU : Graphe co-occurrences
    └── statistics.md                 ← NOUVEAU : Dashboard stats
```

## Tâches

### 🔧 Phase 1 : Fonctions d'analyse (generate.py)
**Agent SQL/Analytics**

```python
# Nouvelles fonctions à ajouter

def get_cooccurrences(conn, civ_id=None, min_turns=2):
    """Retourne co-occurrences d'entités.
    Returns: [(entity1_name, entity1_type, entity2_name, entity2_type, nb_tours)]
    """

def get_entity_timeline(conn, entity_id):
    """Timeline des mentions d'une entité.
    Returns: {turn_number: nb_mentions}
    """

def get_tech_tree(conn, civ_id):
    """Arbre technologique chronologique.
    Returns: [(turn_number, [technologies])]
    """

def get_turn_detailed_stats(conn, turn_id):
    """Stats détaillées d'un tour.
    Returns: {
        segments_by_type: {type: count},
        entities_count: int,
        new_entities: [entity_names],
        mentions_count: int,
        has_media: bool,
        tech_count: int,
        resource_count: int
    }
    """

def get_entity_context_samples(conn, entity_id, limit=5):
    """Extraits de mentions avec contexte.
    Returns: [(turn_number, mention_text, context)]
    """

def get_activity_by_month(conn, civ_id):
    """Activité mensuelle.
    Returns: [(year_month, turn_count)]
    """

def get_turn_messages_grouped(conn, turn_id):
    """Messages Discord groupés par auteur (GM vs Player).
    Returns: [{
        author: str,
        is_gm: bool,
        timestamp: str,
        content: str
    }]
    """
```

### 📄 Phase 2 : Pages individuelles de turns
**Agent Page Generator**

Structure de `turns/turn-XX.md` :
```markdown
# Tour {N} — {title if exists}

📅 **{discord_date}** | 📊 **{nb_segments} segments** | 🎯 **{nb_new_entities} nouvelles entités**

> {summary}

## 📊 Statistiques du tour
- **Entités découvertes** : {new_entities_list}
- **Mentions totales** : {mentions_count}
- **Technologies** : {tech_count}
- **Ressources** : {resource_count}
- **Densité narrative** : {narratives} narratifs, {choices} choix, {consequences} conséquences

{if media_links}
## 🎵 Ambiance
{youtube_embed}
{endif}

## 🎭 Question du Maître du Jeu

### 📖 Récit
{narrative_segments_concat}

### ⚖️ Choix proposés
{choices_proposed_list}

## 💬 Réponse de {player_name}
{player_response}

{if consequences}
## 🎯 Conséquences
{consequence_segments}
{endif}

## 🔍 Découvertes

{if geography}
### 🗺️ Géographie
{geography_list}
{endif}

{if technologies}
### 🔧 Technologies
{technologies_list}
{endif}

{if resources}
### 🌾 Ressources
{resources_list}
{endif}

{if beliefs}
### ✨ Croyances
{beliefs_list}
{endif}

## 🏷️ Entités mentionnées
{for entity in entities}
**{entity.name}** ({entity.type}) — {entity.mentions_this_turn} mentions {if entity.is_new}⭐ *Première apparition*{endif}
{endfor}

---

## 📜 Messages Discord originaux

{for message in messages_grouped}
### {if message.is_gm}Maître du Jeu{else}{message.author}{endif}
*{message.timestamp}*

{message.content}
{endfor}
```

### 🏠 Phase 3 : Dashboard enrichi (index.md)
**Agent Dashboard**

```markdown
# 🏛️ Wiki Aurelm

Bienvenue sur le wiki automatisé du monde d'Aurelm. Ce wiki est généré à partir des tours de jeu Discord.

## 📊 Statistiques globales

| Tours | Entités | Mentions | Technologies | Ressources |
|-------|---------|----------|--------------|------------|
| **{turn_count}** | **{entity_count}** | **{mention_count}** | **{tech_count}** | **{resource_count}** |

## 📈 Activité par mois

```
{for month, count in activity_by_month}
{month} {"█" * count}  {count} tours
{endfor}
```

## 🏆 Top 10 Entités (par mentions)

{for i, entity in top_entities[:10]}
{i}. **{entity.name}** ({entity.type}) {"█" * (entity.mentions // 2)} {entity.mentions} mentions
{endfor}

## 📰 Derniers tours

{for turn in recent_turns[:5]}
- **[Tour {turn.number}]({turn.link})** — *{turn.date}* — {turn.summary[:100]}...
{endfor}

## 🗂️ Navigation rapide

- **[📚 Civilisations](civilizations/index.md)** — Vue d'ensemble des civilisations
- **[⏱️ Timeline globale](global/timeline.md)** — Chronologie complète
- **[🕸️ Réseau d'entités](global/entity-network.md)** — Graphe des co-occurrences
- **[📊 Analytics](civilizations/civilisation-de-la-confluence/analytics.md)** — Stats avancées
- **[📖 Base de connaissances](civilizations/civilisation-de-la-confluence/knowledge/technologies.md)** — Technologies, ressources, croyances

---

*Dernière mise à jour : {timestamp}*
```

### 🏷️ Phase 4 : Pages d'entités enrichies
**Agent Entity Enricher**

Ajouter à chaque page d'entité :
```markdown
## 📊 Vue d'ensemble
| | |
|---|---|
| **Mentions totales** | {total_mentions} |
| **Tours actifs** | {first_turn}-{last_turn} ({duration} tours) |
| **Pic d'activité** | Tour {peak_turn} ({peak_mentions} mentions) |
| **Moyenne** | {avg_mentions} mentions/tour |

## 🔗 Réseau relationnel
**Entités souvent mentionnées ensemble :**
{for entity, turns_together in cooccurrences[:5]}
- 🔵 **{entity.name}** ({entity.type}) — {turns_together} tours — [lien]({entity.link})
{endfor}

## 📈 Graphe d'activité
```
{for turn in turn_range}
Tour {turn} {"█" * mentions[turn] if mentions[turn] else "░"}
{endfor}
```

## 💬 Mentions avec contexte

{for turn, mention, context in context_samples}
**Tour {turn}**
> "{mention}"
>
> Contexte : {context}
{endfor}
```

### 📚 Phase 5 : Knowledge base
**Agent Knowledge**

4 nouvelles pages à créer :

**1. knowledge/technologies.md**
```markdown
# Arbre Technologique

## Timeline chronologique
{for turn, techs in tech_tree}
**Tour {turn}** → {", ".join(techs)}
{endfor}

## Par catégorie

### 🛠️ Outils de chasse
{tech_by_category['hunting']}

### 🎣 Outils de pêche
{tech_by_category['fishing']}

[...]

## Graphe de dépendances
```
Tour 2: gourdins, pieux
         ↓
Tour 3: fumage, pièges
         ↓
Tour 5: pointes de flèches
```
```

**2. knowledge/resources.md**
```markdown
# Index des Ressources

## Par tour
{for turn, resources in resources_by_turn}
**Tour {turn}** : {", ".join(resources)}
{endfor}

## Par catégorie
### 🍖 Nourriture
{resource_by_category['food']}

### 🪨 Matériaux
{resource_by_category['materials']}
```

**3. knowledge/beliefs.md**
```markdown
# Système de Croyances

## Évolution
{for turn, beliefs in beliefs_by_turn}
**Tour {turn}**
{for belief in beliefs}
- {belief}
{endfor}
{endfor}

## Rituels développés
{rituals_list}

## Concepts spirituels
{spiritual_concepts}
```

**4. knowledge/geography.md**
```markdown
# Géographie

## Lieux par ordre de découverte
{for turn, places in geography_by_turn}
**Tour {turn}** : {", ".join(places)}
{endfor}

## Carte textuelle
```
Vallée de la Confluence
├─ Rivière bleue azur (nord)
├─ Rivière vert émeraude (sud)
├─ Villages temporaires
│  ├─ Village principal (confluence)
│  └─ Campements saisonniers
└─ Crêtes adjacentes (lieux funéraires)
```
```

### 📊 Phase 6 : Analytics & Network
**Agent Analytics**

**analytics.md**
```markdown
# Analytics — Civilisation de la Confluence

## 📈 Évolution des entités découvertes
```
Tour  1: █
Tour  2: █
Tour  3: ██
Tour  6: ██████  ← Pic
Tour  7: █████
...
Tour 11: ████████  ← Pic maximal
```

## 📊 Densité narrative par tour
{density_chart}

## 🏆 Top 20 entités
{top_20_entities_with_bars}

## 🎯 Tours clés
- **Tour 6** : Explosion de 6 nouvelles entités
- **Tour 11** : Record de 8 nouvelles entités
```

**global/entity-network.md**
```markdown
# Réseau d'Entités

## Hub central : La confluence (19 mentions)
```
La confluence (place)
├─ Ailes-Grises (caste) — 7 tours ensemble
├─ Regards-Libres (caste) — 6 tours ensemble
├─ Enfants du Courant (caste) — 6 tours ensemble
└─ sans ciel (caste) — 5 tours ensemble
```

## Clusters par type

### Castes
- Ailes-Grises ↔ Enfants du Courant (6 tours)
- Regards-Libres ↔ sans ciel (4 tours)

{network_ascii_graph}
```

### 🧭 Phase 7 : Navigation (mkdocs.yml)
Mettre à jour la navigation pour refléter la nouvelle structure.

## Ordre d'exécution

1. ✅ **Phase 1** : Écrire fonctions d'analyse (Agent SQL)
2. ✅ **Phase 2** : Générateur pages de turns (Agent Page Generator)
3. ✅ **Phase 3** : Dashboard enrichi (Agent Dashboard)
4. ✅ **Phase 4** : Enrichir pages d'entités (Agent Entity Enricher)
5. ✅ **Phase 5** : Knowledge base (Agent Knowledge)
6. ✅ **Phase 6** : Analytics & Network (Agent Analytics)
7. ✅ **Phase 7** : Mise à jour navigation (Moi)
8. ✅ **Test** : Regénérer et vérifier (Moi)

## Agents à utiliser

- **Agent 1 (SQL/Analytics)** : Phase 1 - Fonctions d'analyse DB
- **Agent 2 (Page Generator)** : Phase 2 - Pages de turns individuelles
- **Agent 3 (Dashboard)** : Phase 3 - Dashboard enrichi
- **Agent 4 (Entity)** : Phase 4 - Enrichissement entités
- **Agent 5 (Knowledge)** : Phase 5 - Knowledge base
- **Agent 6 (Analytics)** : Phase 6 - Analytics & Network

Coordination centrale par Claude principal pour intégration et tests.
