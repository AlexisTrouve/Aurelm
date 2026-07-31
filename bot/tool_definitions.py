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

# 24 tools : 22 lecture + discoverMemory / editMemory (mémoire auto-écrite par l'agent).
# Tools absorbés (leurs alias restent dispatchables mais ne sont plus annoncés) :
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
            "relations=true pour le graphe de relations (avec le pourquoi de chaque lien). "
            "relationDepth=2 ou 3 pour remonter des chaînes indirectes (remplace exploreRelations). "
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
                    "description": "Inclure le graphe de relations, avec le détail de CHAQUE lien (défaut: false)",
                },
                "relationDepth": {
                    "type": "integer",
                    "description": "Profondeur de parcours des relations (1 = voisins directs, défaut ; 2-3 = chaînes indirectes). Utilise 2 ou 3 pour 'retrace comment X est lié à Y' ou 'qui relie A et B'. Max 3.",
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
        "description": "Compare plusieurs civs sur : military, technology, politics, economy, culture, diplomacy, religion.",
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
        "name": "getMaps",
        "description": "Liste toutes les cartes avec leur hiérarchie (monde → région → local).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "getMapOverview",
        "description": "Vue d'ensemble d'une carte : tableau de cellules + 10 derniers événements. Max 200 cellules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mapName": {"type": "string", "description": "Nom de la carte (fuzzy match)."},
            },
            "required": ["mapName"],
        },
    },
    {
        "name": "getCell",
        "description": "Détail d'une cellule (terrain, civ contrôlante, entité liée) + 3 derniers événements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mapName": {"type": "string", "description": "Nom de la carte (fuzzy match)."},
                "q": {"type": "integer", "description": "Coordonnée colonne."},
                "r": {"type": "integer", "description": "Coordonnée ligne."},
            },
            "required": ["mapName", "q", "r"],
        },
    },
    {
        "name": "getCellHistory",
        "description": "Historique complet des événements d'une cellule (batailles, découvertes, colonies…).",
        "input_schema": {
            "type": "object",
            "properties": {
                "mapName": {"type": "string"},
                "q": {"type": "integer"},
                "r": {"type": "integer"},
                "limit": {"type": "integer", "description": "Nb max d'événements (défaut: 20)."},
            },
            "required": ["mapName", "q", "r"],
        },
    },
    {
        "name": "getTerritory",
        "description": "Toutes les cellules contrôlées par une civ, groupées par carte.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civ (fuzzy match)."},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "findEntityOnMap",
        "description": "Cherche sur quelle carte/cellule se trouve une entité (fuzzy match + aliases).",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string", "description": "Nom de l'entité (fuzzy match)."},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "groundCivTerrain",
        "description": (
            "Terrain local structuré autour d'une civ (grounding géographique) : sa province "
            "d'origine + l'anneau de provinces voisines, avec biome, relief, régime d'eau "
            "(fleuve/bassin versant, lac, océan), l'ensemble d'éléments à budget de points "
            "(gisements, landmarks, contraintes — avec leurs points signés) et le potentiel "
            "minéral. 1 cellule = 1 province de 20 km (échelle empire/région, pas locale)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civ (fuzzy match)."},
                "radius": {"type": "integer", "description": "Rayon en provinces (défaut: 2)."},
                "fog": {"type": "boolean", "description": "Défaut true : ne révèle que les provinces DÉCOUVERTES par la civ (fog of war) ET gate le contenu par prospection. false = omniscience MJ (toutes provinces, tout contenu)."},
                "maxHiddenLevel": {"type": "integer", "description": "Profondeur de prospection de la civ (défaut 0 = surface). Les éléments de hidden_level supérieur sont comptés « à prospecter », jamais nommés. Passe le niveau que débloque la techno de la civ. Ignoré si fog=false."},
                "eventsPerCell": {"type": "integer", "description": "Nb de derniers événements de chronique (fondations, batailles, notes…) à remonter par province (défaut 2 ; 0 = aucun). Referme la boucle : ce qui a été écrit ressort dans le grounding."},
                "sinceGameTime": {"type": "integer", "description": "Cutoff d'âge (année de jeu, calculée par l'appelant depuis son horloge) : ne remonte que les événements dont game_time >= ce seuil. Les événements sans estampille (game_time NULL) passent toujours. Compose avec eventsPerCell. Aurelm n'a aucune politique d'âge — le seuil vient de toi."},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "discoverAround",
        "description": (
            "Une civ explore : marque comme DÉCOUVERTES les provinces autour d'un lieu (fog of war). "
            "'around' = lieu sémantique (feature/entité/« spawn N ») ou vide = son siège. C'est ainsi "
            "que le fog se lève au fil des tours. Écriture (atomique au tour). Rend les provinces "
            "nouvellement vues."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Civ qui explore (fuzzy match)."},
                "around": {"type": "string", "description": "Lieu exploré (défaut : le siège)."},
                "radius": {"type": "integer", "description": "Rayon exploré en provinces (défaut: 1)."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "proposeSpawnPositions",
        "description": (
            "Propose des provinces de spawn (positions de départ) classées par habitabilité "
            "sur une carte. Read-only. Chaque proposition est numérotée : pour fonder ensuite, "
            "appelle foundSettlement(civName, at='spawn N'). Ne donne JAMAIS de coordonnée à fournir."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
                "n": {"type": "integer", "description": "Nb de propositions (défaut: 5)."},
                "minSpacing": {"type": "integer", "description": "Écart min entre propositions (provinces)."},
            },
            "required": [],
        },
    },
    {
        "name": "foundSettlement",
        "description": (
            "Fonde la cité/capitale d'une civ sur une province (ÉCRITURE : pose le contrôle + "
            "un événement 'settlement' dans l'historique). La cible 'at' est SÉMANTIQUE — "
            "jamais de (q,r) : soit une proposition de spawn (« spawn 1 »), soit une feature/"
            "entité nommée (« Glacial Cirque »). Valide (pas de cité en mer) et renvoie le "
            "terrain local résultant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Civ qui fonde (fuzzy match)."},
                "at": {"type": "string", "description": "Cible sémantique : « spawn N » ou nom de feature/entité."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
                "name": {"type": "string", "description": "Nom de la cité (optionnel)."},
            },
            "required": ["civName", "at"],
        },
    },
    {
        "name": "findNearest",
        "description": (
            "Trouve la/les province(s) la/les plus proche(s) correspondant à « what » "
            "(ressource, biome, terrain, ou eau : river/lake/ocean) depuis un point de départ "
            "sémantique « from » (une civ placée ou une feature nommée). Rend direction + distance "
            "en provinces, jamais de (q,r). Ex : « les Confluents ont-ils du fer proche ? »"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from": {"type": "string", "description": "Départ : nom de civ placée ou de feature/entité."},
                "what": {"type": "string", "description": "Ce qu'on cherche : ressource (iron/coal…), biome, terrain, ou river/lake/ocean."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
                "n": {"type": "integer", "description": "Nb de résultats (défaut: 3)."},
                "fog": {"type": "boolean", "description": "Défaut true : si le départ est une civ, ne cherche que dans ses provinces DÉCOUVERTES. false = omniscience MJ."},
            },
            "required": ["from", "what"],
        },
    },
    {
        "name": "whatIsBetween",
        "description": (
            "Décrit le terrain et les barrières (montagnes, océan) entre les sièges de deux civs : "
            "distance en provinces + la séquence de provinces sur le chemin. Ex : « y a-t-il une "
            "chaîne de montagnes entre les Confluents et les Cheveux de Sang ? »"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civA": {"type": "string", "description": "Première civ (fuzzy match)."},
                "civB": {"type": "string", "description": "Seconde civ (fuzzy match)."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
                "fog": {"type": "boolean", "description": "Défaut true : ne décrit que les provinces découvertes par l'une OU l'autre civ (les autres = inexplorées). false = omniscience MJ."},
            },
            "required": ["civA", "civB"],
        },
    },
    {
        "name": "recordEvent",
        "description": (
            "Inscrit un événement narratif sur une province (ÉCRITURE dans la chronique de la "
            "carte) : kind = settlement|battle|discovery|diplomatic|migration|disaster|note. "
            "La cible 'at' est SÉMANTIQUE (feature/entité nommée ou « spawn N »), jamais de (q,r)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "description": "settlement|battle|discovery|diplomatic|migration|disaster|note"},
                "at": {"type": "string", "description": "Cible sémantique : feature/entité nommée, ou « spawn N »."},
                "description": {"type": "string", "description": "Ce qui s'est passé."},
                "civName": {"type": "string", "description": "Civ concernée (optionnel)."},
                "gameTime": {"type": "integer", "description": "Année de jeu écoulée (ton horloge) à laquelle l'événement a lieu — stockée telle quelle pour le vieillissement. Optionnel (NULL si absent)."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
            },
            "required": ["kind", "at", "description"],
        },
    },
    {
        "name": "annotate",
        "description": (
            "Pose un label MJ et/ou une note sur une province (ÉCRITURE). Cible 'at' SÉMANTIQUE "
            "(feature/entité nommée ou « spawn N »), jamais de (q,r)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "at": {"type": "string", "description": "Cible sémantique."},
                "label": {"type": "string", "description": "Nom/label de la province (optionnel)."},
                "note": {"type": "string", "description": "Note MJ (optionnel)."},
                "gameTime": {"type": "integer", "description": "Année de jeu écoulée (ton horloge) de la note — stockée telle quelle pour le vieillissement. Optionnel (NULL si absent)."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
            },
            "required": ["at"],
        },
    },
    {
        "name": "expandTerritory",
        "description": (
            "Étend le territoire d'une civ en annexant des provinces terrestres libres sur sa "
            "frontière, biaisé « toward » (une direction cardinale N/S/E/O/NE…, ou une civ/feature "
            "nommée). Ne prend jamais l'océan ni le territoire d'une autre civ. Écriture : logge "
            "des événements 'migration'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Civ qui s'étend (fuzzy match)."},
                "toward": {"type": "string", "description": "Direction (N/S/E/O/NE…) ou civ/feature nommée."},
                "amount": {"type": "integer", "description": "Nb de provinces à annexer (défaut: 1)."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "moveEntity",
        "description": (
            "Déplace le pion d'une entité vers une province (ÉCRITURE, un pion par entité par carte). "
            "Cible 'to' SÉMANTIQUE (civ/feature/entité nommée, ou « spawn N »), jamais de (q,r)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string", "description": "Entité à déplacer (fuzzy + alias)."},
                "to": {"type": "string", "description": "Cible sémantique : civ/feature/entité, ou « spawn N »."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
            },
            "required": ["entityName", "to"],
        },
    },
    {
        "name": "cedeTerritory",
        "description": (
            "Une civ CÈDE des provinces à une autre (diplomatie/conquête) — ÉCRITURE : transfère "
            "le contrôle + logge des événements 'diplomatic'. La cible 'at' est SÉMANTIQUE : une "
            "province que la civ cédante contrôle (feature/label/entité nommée), jamais de (q,r). "
            "amount>1 étend la cession aux provinces contiguës de la civ cédante. Le bénéficiaire "
            "découvre le territoire gagné."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fromCiv": {"type": "string", "description": "Civ qui cède (fuzzy match)."},
                "toCiv": {"type": "string", "description": "Civ bénéficiaire (fuzzy match)."},
                "at": {"type": "string", "description": "Province cédée : feature/label/entité nommée que la civ cédante contrôle."},
                "amount": {"type": "integer", "description": "Nb de provinces contiguës à céder (défaut: 1)."},
                "mapName": {"type": "string", "description": "Carte (optionnel si une seule)."},
            },
            "required": ["fromCiv", "toCiv", "at"],
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
    {
        "name": "discoverMemory",
        "description": (
            "Explore TA propre mémoire (le pendant lecture d'editMemory). "
            "SANS 'keys' → inventaire compact de tout ce que tu as retenu (key + description + "
            "portée + ancre, SANS le contenu — peu coûteux). "
            "AVEC 'keys' → le contenu complet des mémoires demandées. "
            "Utilise-le quand le MJ demande ce que tu sais/retiens, quand tu cherches la key "
            "d'une mémoire à corriger ou oublier, ou pour vérifier si tu as déjà un ruling sur "
            "un sujet. Le rappel automatique ne te montre que les mémoires jugées pertinentes — "
            "celui-ci te montre les autres."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Les keys dont tu veux le contenu complet. Vide/absent = inventaire de tout.",
                },
                "civName": {"type": "string", "description": "Ne montrer que les mémoires de cette civ."},
                "type": {
                    "type": "string",
                    "enum": ["fact", "preference"],
                    "description": "Filtrer par type.",
                },
                "includeInactive": {
                    "type": "boolean",
                    "description": "Inclure aussi les mémoires oubliées (défaut: false).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "editMemory",
        "description": (
            "Gère TA propre mémoire durable à partir d'un retour du MJ (correction, ruling sur "
            "le monde, préférence de réponse). Un seul outil qui fait tout : "
            "CRÉER / METTRE À JOUR (défaut) ou OUBLIER (forget=true). "
            "Upsert par 'key' — réappeler avec la MÊME key met à jour (pas de doublon) ; les keys "
            "de tes mémoires actives te sont montrées entre crochets dans '## Mémoire de l'agent', "
            "réutilise-les pour corriger ou oublier. "
            "Appelle-le quand le MJ te corrige, énonce une règle, ou dit comment il veut ses réponses. "
            "Ne PAS l'utiliser pour du contenu déjà en base (entités, tours) — seulement les retours du MJ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Slug court et stable identifiant la mémoire (ex: 'confluence-bronze', 'style-citation'). Réutilise la même key pour corriger ou oublier.",
                },
                "content": {
                    "type": "string",
                    "description": "Le fait, la règle ou la préférence à retenir, en une phrase. Requis sauf si forget=true.",
                },
                "description": {
                    "type": "string",
                    "description": "Résumé d'une ligne pour le rappel (optionnel).",
                },
                "type": {
                    "type": "string",
                    "enum": ["fact", "preference"],
                    "description": "'fact' = ruling/correction sur le monde (défaut, rappelé quand pertinent). 'preference' = comment répondre (toujours injecté).",
                },
                "civName": {
                    "type": "string",
                    "description": "Civ concernée (optionnel). Vide = mémoire globale.",
                },
                "turnNumber": {
                    "type": "integer",
                    "description": "Ancre le fait à un tour ('à partir de T12'). Optionnel, avec civName. Pour un fait daté qui pourrait évoluer.",
                },
                "links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Articles de la base que cette mémoire concerne, pour pouvoir y revenir : "
                        "'entity:Argile Vivante', 'turn:12', 'subject:18'. Les entités se résolvent "
                        "par nom (ou alias), les tours par numéro pour la civ donnée. "
                        "Remplace les liens existants à chaque appel. Max 8."
                    ),
                },
                "forget": {
                    "type": "boolean",
                    "description": "true = OUBLIER (désactiver) la mémoire de cette key, quand le MJ dit qu'elle est fausse/périmée. Ignore les autres champs.",
                },
            },
            "required": ["key"],
        },
    },
]
