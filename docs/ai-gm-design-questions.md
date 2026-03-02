# CIVJDR AI Gamemaster — Questions de design

Ce document liste toutes les decisions a prendre avant de coder.
Pour chaque question : contexte, options possibles, et impact sur l'architecture.

**Comment repondre** : ecris ta reponse directement sous chaque question dans le bloc `> Reponse:`. Si t'es pas sur, ecris ce que tu penches vers et on affinera.

---

## 1. Systeme de regles

### 1.1 Narratif pur ou mecanique ?

**Contexte** : Dans le JDR actuel d'Arthur, est-ce qu'il y a des jets de des, des stats chiffrees, des barres de ressources ? Ou c'est purement narratif (le GM decide de ce qui est plausible) ?

**Options** :
- **A) Narratif pur** : Le GM AI juge subjectivement ce qui est possible. Plus creatif, mais risque de derive (le LLM qui escalade progressivement).
- **B) Semi-mecanique** : Pas de des, mais un etat structure par civ (population: "grande", militaire: "modeste", techno: liste). Le GM AI s'appuie sur cet etat pour juger la faisabilite.
- **C) Mecanique legere** : Des regles codees en dur (prerequis techno, couts en ressources, limites par tour). Plus rigide mais plus coherent sur 100+ tours.

**Impact** : Si A, on peut coder vite mais la qualite depend entierement du LLM. Si B ou C, il faut designer un state model avant de coder quoi que ce soit.

> Reponse:
Dans le JDR d'arthur il y a des jets de dés, des stats et des chiffres oui. Il y a des ressources. Il nous faut tout ça oui. 

### 1.2 Arbre technologique

**Contexte** : Est-ce qu'il y a un tech tree predefini (bronze -> fer -> acier, agriculture -> irrigation -> moulins) ou c'est emergent (le GM decide au fil du jeu ce qui est decouvrable) ?

**Options** :
- **A) Emergent** : Le GM AI decide ce qui est plausible a decouvrir, basé sur l'etat actuel. Flexible mais risque d'incoherence (decouvrir l'acier avant le fer).
- **B) Arbre souple** : Des "familles" de technologies avec un ordre logique, mais pas un arbre rigide. Le GM AI connait les prerequis generaux.
- **C) Arbre fixe** : Un tech tree predefini dans la DB. Deterministe mais moins de surprise.

> Reponse:
Il y a une système de tech prédéfini baser sur la vie réel MAIS tout est modulable. et surtout presque tout est unique à toute les civs. Et les tech peuvent être créer à la volé parfois même par les joueurs

### 1.3 Modele de ressources

**Contexte** : Est-ce que les civs ont des inventaires quantifies (bronze: 150 unites, nourriture: 80%) ou c'est qualitatif ("reserves abondantes", "stocks faibles") ?

**Options** :
- **A) Qualitatif pur** : Descriptions textuelles. "Vos reserves de bronze sont modestes."
- **B) Semi-quantitatif** : Des niveaux (abondant/suffisant/faible/critique) sans chiffres exacts.
- **C) Quantitatif** : Des chiffres (population: 5000, bronze: 150 unites). Necessite un modele economique.

> Reponse:
C'est des nombres de ce que je sais mais en impact narratif c'est jamais des nombres (d'un autre côté ma civ à pas discover les maths...)

---

## 2. Structure du jeu

### 2.1 Echelle de temps

**Contexte** : Combien de temps in-game passe entre chaque tour ? Ca determine ce qui peut se passer "passivement" (croissance, construction, recherche).

**Options** :
- **A) Variable** : Le GM decide selon le contexte (parfois 1 an, parfois 50 ans). Plus flexible mais plus dur a simuler.
- **B) Fixe** : Toujours la meme duree (ex: 1 generation = 25 ans). Plus simple a gerer.
- **C) Par phases** : Debut de partie = longs intervalles (100 ans), puis ca se resserre quand le monde se complexifie.

**Comment c'est dans le JDR d'Arthur actuellement ?**

> Reponse:
Le temps entre chaque tour varie. C'est l'IA qui doit gérer ça mais attention aux collisions entre civ et au timing ect. Mais parfois dans un tour des action/décision appartienne pas au même "moment" c'est variable et flexible. ça respecte au moins partiellement la logique de "par phase" cela dit

### 2.2 Scope d'un tour

**Contexte** : Qu'est-ce qu'un joueur peut accomplir en un seul tour ? C'est important pour empecher "je decouvre le fer, construis une armee, et conquiers 3 villes" en un tour.

**Options** :
- **A) Pas de limite formelle** : Le GM juge si c'est raisonnable.
- **B) Action principale + action secondaire** : Un focus majeur (ex: campagne militaire) + un truc mineur (ex: debut de recherche).
- **C) Points d'action** : X points par tour, chaque type d'action coute des points.
- **D) Autre ?**

**Comment Arthur gere ca actuellement ?**

> Reponse:
SImple, si y'a une decision elle à max d'impact. Si y'a 5 décision impact très faible. Le MJ donne la cadence en proposant les sujets mais un joueur peut inclure ses propres sujet si il a besoin.

### 2.3 Conditions de fin

**Contexte** : Le jeu a-t-il une fin ? Si oui, quand ?

**Options** :
- **A) Open-ended** : Pas de fin, on joue tant que c'est fun.
- **B) Objectif** : Premiere civ a atteindre X (age industriel, domination mondiale, etc.)
- **C) Nombre de tours** : On decide d'avance "on joue 50 tours".

> Reponse:
Je sais pas. Pas de fin je dirais. On peut même imaginer des restart dans le jeu (pahse spacial quand c'est "gagné" et avec des nouvelles civ eventuellement)

---

## 3. Multi-civilisation

### 3.1 Ordre des tours

**Contexte** : Si 3 civs jouent (1 humain, 2 AI), dans quel ordre on traite les tours ?

**Options** :
- **A) Sequentiel fixe** : Toujours Civ A, puis B, puis C. Simple. Civ A a un leger avantage (voit rien), Civ C un leger avantage (voit tout).
- **B) Sequentiel aleatoire** : L'ordre change chaque tour.
- **C) Simultane** : Toutes les civs soumettent leur choix, puis le GM resout tout d'un coup. Plus realiste mais complexe (conflits).
- **D) Asynchrone** : Chaque civ joue quand elle veut. Le monde avance en temps reel. Le plus immersif mais le plus dur.

**Impact** : Si C ou D, il faut un systeme de resolution de conflits ("Civ A attaque Civ B pendant que Civ B propose la paix a Civ A").

> Reponse:
Je propose un système d'initiative. Mais "l'avantage" dont tu parle est gérer par la contextualisation MJ. Un joueur n'a accès que au infos dans les messages. Pas d'accès wiki au autre. Juste le message MJ

### 3.2 Interactions entre civilisations

**Contexte** : Comment les civs communiquent/interagissent ?

**Options** :
- **A) Via le GM uniquement** : Le GM decrit ce que les autres civs font. Les joueurs ne communiquent pas directement.
- **B) Diplomatie directe** : Les joueurs (humains ou AI) peuvent s'envoyer des messages diplomatiques. Le GM modere.
- **C) Mixte** : Certaines interactions sont directes (commerce, diplomatie), d'autres passent par le GM (guerre, espionnage).

> Reponse:
Via le GM uniquement.

### 3.3 Information asymetrique

**Contexte** : En vrai JDR, un joueur ne connait pas l'etat exact des autres civs. Il sait seulement ce que le GM lui revele ou ce qu'il decouvre (exploration, espionnage).

**Options** :
- **A) Omniscient** : Les AI players voient toute la DB. Plus simple a coder.
- **B) Brouillard de guerre** : Chaque AI player ne voit que sa civ + ce qui a ete revele. Plus immersif, plus complexe.

**Impact** : Si B, il faut un systeme de "visibility" par civ (quelles entites sont connues, quelles infos sur les autres civs).

> Reponse:
B, Brouillard de guerre. Le brouillard de guerre existe de part le fait que le GM choisit ce qu'il révèle.

---

## 4. AI Players

### 4.1 Personnalite des AI civs

**Contexte** : Pour que le jeu soit interessant, chaque AI civ doit jouer differemment.

**Comment tu imagines les personnalites ?**
- Les Cheveux de Sang (civ maritime) : plutot agressifs ? commercants ? explorateurs ?
- Les Nanzagouets / Tlazhuaneca : religieux ? isolationnistes ? expansionnistes ?
- Autres civs futures ?

**Est-ce que chaque civ a un "character" defini dans le lore d'Arthur, ou c'est a nous de le definir ?**

> Reponse:
On fait des pools et on pick random ? On peut même changer en jeu je dirais

### 4.2 Actions libres des AI

**Contexte** : Quand le GM propose 4 choix, est-ce que l'AI player peut aussi proposer une action libre (comme un humain) ?

**Options** :
- **A) Non, choix parmi les options seulement** : Plus previsible, moins de risque d'hallucination.
- **B) Oui, avec validation Veracite** : Plus dynamique, mais l'AI peut proposer des trucs bizarres.
- **C) Rarement** : L'AI choisit surtout parmi les options, mais parfois (10% ?) propose une action libre pour la surprise.

> Reponse:
Oui oui. Je dirais même on ne propose pas de choix à l'IA

### 4.3 Strategie a long terme

**Contexte** : Est-ce que les AI players doivent avoir un "plan strategique" sur plusieurs tours, ou juste reagir turn-by-turn ?

**Options** :
- **A) Reactif** : L'AI choisit le meilleur coup a chaque tour. Simple.
- **B) Strategique** : L'AI maintient un plan ("devenir puissance maritime en 10 tours") et oriente ses choix vers ce plan. Plus interessant mais faut gerer la memoire inter-tours.

> Reponse:
Les AI players doivent faire des plans, documenter des strats, etablir une vision etcetc. 

---

## 5. Qualite narrative

### 5.1 Style d'ecriture

**Contexte** : Le GM AI doit ecrire des posts narratifs. A quoi doivent-ils ressembler ?

**Questions** :
- Longueur typique d'un post d'Arthur ? (mots approximatifs)
- Registre : epique ? factuel ? poetique ? un mix ?
- Perspective : 2eme personne ("Votre civilisation...") ? 3eme personne ("Les Confluents...") ?
- Est-ce qu'Arthur utilise des dialogues entre personnages ? Des descriptions de scenes ?

> Reponse:
ça doit être cool à lire mais clair dans les implications. l'IA doit être lucide sur la signification mais ça doit être cool à lire. On peut avoir des posts de la taille des réponses d'arthur x2 je dirais

### 5.2 Choix proposes

**Contexte** : Les choix sont le coeur du gameplay. A quoi ressemble un bon choix dans le JDR d'Arthur ?

**Questions** :
- Combien de choix par tour typiquement ?
- Y a-t-il toujours une "option libre" ?
- Les choix sont-ils plutot strategiques ("investir dans X ou Y") ou narratifs ("comment reagir a cette situation") ?
- Est-ce qu'un choix a toujours des consequences visibles, ou certains sont des slow burns ?

> Reponse:
2-3 choix généralement et quand c'est un "problème" y'a pas d'option libre généralement. souvent visible, parfois slow burns. On a du startégique et du narratif.

---

## 6. Technique

### 6.1 Budget compute

**Contexte** : Chaque tour necessite plusieurs appels LLM. Faut savoir le budget.

**Questions** :
- Le systeme tourne sur ta machine (RTX 4060 8GB) ou celle d'Arthur (RTX 5070 Ti 16GB) ?
- Ollama uniquement, ou Claude API aussi ? (cout $)
- Combien de tours par jour tu veux pouvoir jouer ? (1 ? 10 ? 50 ?)
- Latence acceptable par tour ? (1 min ? 5 min ? 15 min ?)

> Reponse:
Ollama pour l'analyse mais c'est claude le master. 1 tour par jour je dirais mais pas de limite. Latence de 2-3 heures parfaitement acceptable. Même 6heures is fine. 

### 6.2 Interface

**Contexte** : Par ou tu joues ?

**Options** :
- **A) Discord uniquement** : Le bot poste les turns, tu reponds dans le channel.
- **B) GUI Flutter** : Interface dediee avec historique, carte, stats.
- **C) Discord + GUI** : Discord pour jouer, GUI pour consulter l'etat du monde.
- **D) CLI** : Terminal, simple et rapide pour le dev.

> Reponse:
DIscord ? mais osef tant que pas CLI. On peut bien sûr CLI pour le dev. NP

### 6.3 Persistance des AI players

**Contexte** : Les AI players doivent-ils "se souvenir" de leurs decisions passees entre les sessions ? Ou ils repartent de zero en relisant la DB a chaque tour ?

**Options** :
- **A) Stateless** : L'AI relit la DB a chaque tour. Simple, mais perd la "personnalite emergente".
- **B) Stateful** : L'AI a un fichier de memoire/strategie qui persiste. Plus riche mais plus complexe.

> Reponse:
Les AI players doivent faire des docs pour savoir ce qu'il font dans le futurs et utilise Aurelm pour savoir ce qu'il ont fait dans le passé. Bien sûr, il ont aussi un prompt des actions récentes.

---

## 7. Scope du POC

### 7.1 Version minimale

**Contexte** : On peut pas tout faire d'un coup. Qu'est-ce qui est essentiel pour un premier test jouable ?

**Ma proposition de scope minimal** :
- 1 humain (toi, Confluence)
- 1 AI civ (Cheveux de Sang)
- GM AI (Claude API ou Ollama)
- Tours sequentiels
- Pas de diplomatie directe (tout via GM)
- Pas de carte
- Interface Discord
- 10 tours de test

**Est-ce que ca te va comme premier jalon, ou tu veux plus/moins ?**

> Reponse:
On fait tout. Même si ça prend des mois. Je veux une carte inclut.

### 7.2 Nom du projet ?

> Reponse:
Choisis un truc cool genre greco romain. Avec une pointe de fantasy.

---

## Resume des decisions critiques

| # | Question | Impact |
|---|----------|--------|
| 1.1 | Narratif vs mecanique | Determine toute l'architecture |
| 1.3 | Ressources qualitatives vs quantitatives | Determine le state model |
| 2.1 | Echelle de temps | Determine la simulation passive |
| 3.1 | Ordre des tours | Determine le game loop |
| 3.3 | Brouillard de guerre | Determine l'acces DB des AI |
| 5.1 | Style d'ecriture | Determine les prompts |
| 6.1 | Budget compute | Determine les modeles utilisables |

**Prochaine etape** : Une fois tes reponses, je fais l'architecture technique detaillee.


Commentaires autre.
Il faut pourvoir avoir de la fantasy hein. Ou des trucs vraiment originaux. On se contente pas de faire du classique CIV 5 game. On fait du open game