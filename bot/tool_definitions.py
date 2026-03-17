"""Tool schemas for the Aurelm agent.

Standard filter parameters — présents sur tous les tools qui retournent des listes.
Le LLM apprend le vocabulaire une fois, l'applique partout.

    civName    : nom de la civ (fuzzy match)
    fromTurn   : tour de début (inclus)
    toTurn     : tour de fin (inclus)
    lastNTurns : raccourci "N derniers tours" (ex: 5)
    tag        : domaine — militaire|politique|religieux|economique|
                           culturel|diplomatique|technologique|mythologique
    limit      : max résultats (défaut selon l'outil)
"""

# Bloc standard réutilisé dans chaque schema — évite la répétition de tokens.
_STD = {
    "civName": {"type": "string"},
    "fromTurn": {"type": "integer"},
    "toTurn": {"type": "integer"},
    "lastNTurns": {"type": "integer", "description": "ex: 5 = 5 derniers tours"},
    "tag": {
        "type": "string",
        "description": "militaire|politique|religieux|economique|culturel|diplomatique|technologique|mythologique",
    },
    "limit": {"type": "integer"},
}

# 12 tools (réduit depuis 18).
# Tools supprimés (absorbés) :
#   filterTimeline  → timeline (params standard)
#   exploreRelations → getEntityDetail(relations=true)
#   entityActivity   → getEntityDetail(activity=true)
#   getChoiceHistory → getStructuredFacts(factType="choices")
#   getTechTree      → getStructuredFacts(factType="techtree")
#   getEntitiesByTag → searchLore(tag=..., query="")
TOOL_DEFINITIONS = [
    {
        "name": "listCivs",
        "description": "Liste toutes les civs avec nb tours et nb entités.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "getCivState",
        "description": "Vue d'ensemble d'une civ : tours récents, entités-clés, breakdown par type.",
        "input_schema": {
            "type": "object",
            "properties": {"civName": {"type": "string"}},
            "required": ["civName"],
        },
    },
    {
        "name": "getTurnDetail",
        "description": "Contenu complet d'un tour : segments, choix, conséquences, entités. Sections opt-in pour contrôler la verbosité.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string"},
                "turnNumber": {"type": "integer"},
                "showSegments": {
                    "type": "boolean",
                    "description": "Inclure les segments narratifs (défaut: false)",
                },
                "showEntities": {
                    "type": "boolean",
                    "description": "Inclure la table des entités mentionnées (défaut: false)",
                },
                "showNotes": {
                    "type": "boolean",
                    "description": "Inclure les notes GM (défaut: false). Les notes pinned sont toujours incluses.",
                },
            },
            "required": ["civName", "turnNumber"],
        },
    },
    {
        "name": "searchLore",
        "description": (
            "Recherche entités par nom/description/alias. "
            "tag= pour filtrer par domaine (remplace getEntitiesByTag — query vide OK). "
            "Params standard supportés."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Laissez vide avec tag= pour lister toutes les entités d'un domaine",
                },
                "entityType": {
                    "type": "string",
                    "description": "person|place|technology|institution|resource|creature|event|civilization|caste|belief",
                },
                **_STD,
            },
            "required": [],
        },
    },
    {
        "name": "getEntityDetail",
        "description": (
            "Fiche complète d'une entité : description, aliases, mentions. "
            "relations=true pour le graphe de relations (remplace exploreRelations). "
            "activity=true pour la timeline d'activité par tour (remplace entityActivity). "
            "Sections opt-in pour contrôler la verbosité."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string"},
                "civName": {"type": "string"},
                "relations": {
                    "type": "boolean",
                    "description": "Inclure le graphe de relations (défaut: false)",
                },
                "activity": {
                    "type": "boolean",
                    "description": "Inclure la timeline d'activité par tour (défaut: false)",
                },
                "showMentions": {
                    "type": "boolean",
                    "description": "Inclure les 20 dernières mentions (défaut: false)",
                },
                "showFacts": {
                    "type": "boolean",
                    "description": "Inclure la chronologie/history (défaut: false)",
                },
                "showTimeline": {
                    "type": "boolean",
                    "description": "Alias pour activity (défaut: false)",
                },
                "showNotes": {
                    "type": "boolean",
                    "description": "Inclure les notes GM (défaut: false). Les notes pinned sont toujours incluses.",
                },
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "sanityCheck",
        "description": "Vérifie une affirmation contre le lore : croise mots-clés, entités connues, tours récents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "statement": {"type": "string"},
                "civName": {"type": "string"},
            },
            "required": ["statement"],
        },
    },
    {
        "name": "timeline",
        "description": (
            "Chronologie des tours. "
            "turnType=standard|event|first_contact|crisis pour filtrer par type. "
            "entityName= pour les tours où une entité est mentionnée. "
            "Params standard supportés (fromTurn, toTurn, lastNTurns, civName, limit). "
            "Remplace filterTimeline."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "turnType": {
                    "type": "string",
                    "description": "standard|event|first_contact|crisis",
                },
                "entityName": {
                    "type": "string",
                    "description": "Filtre tours mentionnant cette entité",
                },
                **_STD,
            },
            "required": [],
        },
    },
    {
        "name": "compareCivs",
        "description": "Compare plusieurs civs sur : military, technology, politics, economy, culture.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civNames": {"type": "array", "items": {"type": "string"}},
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optionnel, défaut: tous",
                },
            },
            "required": ["civNames"],
        },
    },
    {
        "name": "searchTurnContent",
        "description": "Recherche full-text dans les récits narratifs (pas les entités). Params standard supportés.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "segmentType": {
                    "type": "string",
                    "description": "narrative|choice|consequence|ooc|description",
                },
                **_STD,
            },
            "required": ["query"],
        },
    },
    {
        "name": "getStructuredFacts",
        "description": (
            "Faits structurés d'une civ par tour. "
            "factType=technologies|resources|beliefs|geography|choices|techtree|all. "
            "choices = historique des bifurcations narratives (remplace getChoiceHistory). "
            "techtree = arbre technologique organisé par catégorie (remplace getTechTree). "
            "Params standard supportés."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "factType": {
                    "type": "string",
                    "description": "technologies|resources|beliefs|geography|choices|techtree|all (défaut: all)",
                },
                **_STD,
            },
            "required": ["civName"],
        },
    },
    {
        "name": "listSubjects",
        "description": (
            "Sujets MJ↔PJ (décisions ouvertes, initiatives). "
            "status=open|resolved|all. direction=mj_to_pj|pj_to_mj. "
            "Params standard supportés (tag, lastNTurns, civName...)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "open|resolved|all (défaut: open)",
                },
                "direction": {
                    "type": "string",
                    "description": "mj_to_pj (GM→joueur) | pj_to_mj (initiative joueur)",
                },
                **_STD,
            },
            "required": [],
        },
    },
    {
        "name": "getNotes",
        "description": "Notes GM attachées à une entité, un sujet, ou un tour. Appeler pour enrichir le contexte d'un élément.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string", "description": "Nom d'une entité"},
                "subjectId":  {"type": "integer", "description": "ID d'un sujet"},
                "turnNumber": {"type": "integer", "description": "Numéro de tour"},
                "civName":    {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "getSubjectDetail",
        "description": "Détail complet d'un sujet : description, options proposées, résolutions. Sections opt-in. Utiliser après listSubjects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subjectId": {"type": "integer"},
                "showOptions": {
                    "type": "boolean",
                    "description": "Inclure les options proposées (défaut: false)",
                },
                "showResolutions": {
                    "type": "boolean",
                    "description": "Inclure les résolutions (défaut: false)",
                },
                "showNotes": {
                    "type": "boolean",
                    "description": "Inclure les notes GM (défaut: false). Les notes pinned sont toujours incluses.",
                },
            },
            "required": ["subjectId"],
        },
    },
    {
        "name": "getFavorites",
        "description": (
            "Liste les éléments marqués favoris par le MJ (entités, sujets, tours). "
            "Point d'entrée prioritaire pour les sujets importants — utiliser en premier "
            "quand le MJ demande 'mes favoris' ou 'les éléments importants'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["entity", "subject", "turn"],
                    "description": "Type d'élément à lister. Omis = tous les types.",
                },
                "civName": {
                    "type": "string",
                    "description": "Filtrer par civilisation (fuzzy match).",
                },
                "tag": {
                    "type": "string",
                    "description": "Filtrer par domaine : militaire|politique|religieux|economique|culturel|diplomatique|technologique|mythologique",
                },
                "status": {
                    "type": "string",
                    "description": "Sujets seulement — open|resolved|abandoned|superseded",
                },
                "limit": {"type": "integer", "description": "Nombre max de résultats (défaut: 20)."},
            },
        },
    },
    {
        "name": "getCivRelations",
        "description": (
            "Relations diplomatiques inter-civilisations. Retourne l'opinion unilatérale "
            "d'une civ envers les autres (allied/friendly/neutral/suspicious/hostile/unknown), "
            "la description narrative de chaque relation, et les traités/accords détectés. "
            "Utiliser pour : 'quelles sont les relations de la Confluence ?', 'est-ce que X est alliée avec Y ?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {
                    "type": "string",
                    "description": "Nom de la civ (fuzzy match). Retourne toutes ses relations connues.",
                },
            },
            "required": ["civName"],
        },
    },
    {
        "name": "deepExplore",
        "description": (
            "Analyse approfondie : lance un sous-agent qui enchaîne automatiquement searchLore, "
            "getEntityDetail, getSubjectDetail, timeline, getTurnDetail pour répondre à une question complexe. "
            "Utiliser quand une seule recherche ne suffit pas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "La question de recherche approfondie",
                },
                "context": {
                    "type": "string",
                    "description": "Contexte additionnel pour guider la recherche",
                },
            },
            "required": ["question"],
        },
    },
]
