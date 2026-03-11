"""Tool schemas for the Aurelm agent. Edit here to tune descriptions/params.
Implementations in tools.py. Imported by agent.py.
"""

TOOL_DEFINITIONS = [
    {
        "name": "listCivs",
        "description": "Liste toutes les civs (nom, nb tours, nb entités). Appeler en début de réponse cross-civ.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "getCivState",
        "description": "Vue d'ensemble d'une civ : tours récents, entités-clés, breakdown par type. Paralléliser pour plusieurs civs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civilisation"},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "getTurnDetail",
        "description": "Contenu complet d'un tour : segments narratifs, choix, conséquences, entités. Paralléliser pour plusieurs tours.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string"},
                "turnNumber": {"type": "integer"},
            },
            "required": ["civName", "turnNumber"],
        },
    },
    {
        "name": "searchLore",
        "description": "Recherche dans les entités (noms, descriptions, aliases). Pour chercher dans les récits narratifs : utiliser searchTurnContent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "civName": {"type": "string", "description": "Optionnel"},
                "entityType": {"type": "string", "description": "person|place|technology|institution|resource|creature|event|civilization|caste|belief (optionnel)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "getEntityDetail",
        "description": "Fiche complète d'une entité : description, chronologie, relations, tous les tours. Paralléliser pour plusieurs entités.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string"},
                "civName": {"type": "string", "description": "Optionnel, aide si ambiguïté"},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "sanityCheck",
        "description": "Vérifie une affirmation contre le lore : croise mots-clés avec entités connues et tours récents. Pour valider une décision narrative ou détecter une incohérence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "statement": {"type": "string"},
                "civName": {"type": "string", "description": "Optionnel"},
            },
            "required": ["statement"],
        },
    },
    {
        "name": "timeline",
        "description": "Chronologie des tours avec type et nb entités. Pour filtres précis (type, intervalle, entité) : utiliser filterTimeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Optionnel"},
                "limit": {"type": "integer", "description": "Défaut 50"},
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
                "aspects": {"type": "array", "items": {"type": "string"}, "description": "Optionnel, défaut: tous"},
            },
            "required": ["civNames"],
        },
    },
    {
        "name": "searchTurnContent",
        "description": "Recherche full-text dans les segments narratifs (récits, pas entités). Complémentaire à searchLore.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "civName": {"type": "string", "description": "Optionnel"},
                "segmentType": {"type": "string", "description": "narrative|choice|consequence|ooc|description (optionnel)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "getStructuredFacts",
        "description": "Faits structurés par tour : technologies, ressources, croyances, géographie. Pour 'ont-ils X ?'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string"},
                "factType": {"type": "string", "description": "technologies|resources|beliefs|geography|all (défaut: all)"},
                "turnNumber": {"type": "integer", "description": "Optionnel"},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "getChoiceHistory",
        "description": "Historique des choix proposés et décisions prises par une civ. Pour comprendre les bifurcations narratives.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string"},
                "turnNumber": {"type": "integer", "description": "Optionnel"},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "exploreRelations",
        "description": "Graphe de relations d'une entité : contrôle, appartenance, alliances. Depth 1-3.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string"},
                "civName": {"type": "string", "description": "Optionnel"},
                "depth": {"type": "integer", "description": "1-3, défaut 1"},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "filterTimeline",
        "description": "Timeline avec filtres : type de tour, intervalle T, ou tours mentionnant une entité.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Optionnel"},
                "turnType": {"type": "string", "description": "standard|event|first_contact|crisis (optionnel)"},
                "fromTurn": {"type": "integer", "description": "Optionnel"},
                "toTurn": {"type": "integer", "description": "Optionnel"},
                "entityName": {"type": "string", "description": "Optionnel"},
            },
            "required": [],
        },
    },
    {
        "name": "entityActivity",
        "description": "Activité temporelle d'une entité : mentions par tour, pic, contexte récent. Pour 'X est-il toujours actif ?'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string"},
                "civName": {"type": "string", "description": "Optionnel"},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "getTechTree",
        "description": "Arbre technologique d'une civ organisé par catégorie avec timeline d'acquisition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string"},
                "category": {"type": "string", "description": "Optionnel"},
            },
            "required": ["civName"],
        },
    },
]
