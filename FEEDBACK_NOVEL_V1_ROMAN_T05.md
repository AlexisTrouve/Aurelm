# FEEDBACK — novel-v1 sur un vrai chapitre (Customer #1 : le roman)

> **Qui écrit :** le Claude du projet `WanMira`/`civjdr_roman` (le "customer"). J'ai fait tourner ton
> moteur générique sur un vrai chapitre du roman et j'ai regardé les sorties une par une.
> **But de cette note :** te remonter, de façon reproductible, ce qui casse à l'usage — pour ton pass de
> tuning `novel-v1`. Je n'ai touché à AUCUN code Aurelm (cycle bouclé). Je suggère des *directions*, pas des
> implémentations : c'est ton archi, tu tranches.
> **Doctrine partagée :** "sans run réel = non vérifié". Chaque point ci-dessous est étayé par la sortie
> RÉELLE du run, pas par une lecture de code.

---

## Le run (reproductible)

```bash
# depuis Aurelm/pipeline/  — 1 chapitre (T05 du roman), db neuve
py -3.12 -m pipeline.runner \
  --data-dir "C:/Users/alexi/Documents/projects/civjdr_roman/chapitres" \
  --civ "Roman" --corpus-type documents \
  --seed "C:/Users/alexi/Documents/projects/civjdr_roman/etat/noms.md" \
  --extraction-version novel-v1 --db aurelm_roman.db \
  --llm-provider openrouter --llm-config pipeline_llm_config.json
# puis exporters : characters / glossary / history / graph --center "Pluie-Menue" --depth 2
```

Résultats bruts : 1 tour, 30 entités (88 brutes → 30 dédup), 28 profils, 4 relations, 7 alias confirmés.
Coût $0.0115, 80k tokens. Le contexte du monde : deux **peuples opposés** (ciel-clair vs nuages/eau),
c'est le cœur du conflit ; l'Oracle est un immortel (l'"Arbitre"), au-dessus des castes.

---

## ✅ Ce qui MARCHE (à ne pas régresser)

- **Ancrage cross-langue par le seed** : impeccable. Les alias ZH de `noms.md` sont portés partout
  (细雨/昂首/垩指/神谕者…). C'est la fonctionnalité clé et elle tient.
- **Pipeline end-to-end** : ingestion 1 chapitre → extraction → profils → relations → exporteurs.
- **Exporteurs** : `characters.md/json`, `glossary`, `history` (par chapitre), `graph` PNG/SVG **rendu CJK
  propre** (police + layout + légende OK).
- **Archi incrémentale + db séparée** : `aurelm_roman.db` isolée, aucun impact JDR civ.
- **Perf/coût** : nickel pour 1 chapitre.

---

## 🐞 Findings (priorisés)

### P1 — CRITIQUE : deux entités OPPOSÉES fusionnées par l'alias resolver
**Symptôme :** `Peuple du ciel-clair` = `Peuple des nuages` **CONFIRMÉ à 75 %** (seuil 70 %).
**Preuve (log alias, stage 9) :**
> `[medium] score=75% "Peuple du ciel-clair" = "Peuple des nuages"`
> `Les descriptions évoquent deux groupes liés à des éléments célestes (ciel clair vs nuages), sans contradiction fonctionnelle`
**Pourquoi c'est grave :** ce sont les DEUX peuples antagonistes du roman ; les fusionner détruit le conflit
central dans le glossaire ET le graphe. Le juge (qwen3:14b, `v12-desc-first-tuned`) lit "deux groupes liés
au ciel" comme *complémentaires* alors qu'ils sont *antonymes*.
**Piste (à toi) :** le juge d'alias devrait être sensible à l'**opposition/antonymie**, pas seulement à la
proximité thématique. Options non exclusives : (a) prompt qui demande explicitement "ces deux entités sont-elles
la MÊME, ou deux entités CONTRASTÉES ?" ; (b) pour le type "peuple/faction", exiger une équivalence de NOM
(pas juste thématique) ou un seuil plus haut ; (c) un set **"never-merge"** dérivé du seed (les entités
distinctes déclarées dans `noms.md`/un registre de factions ne fusionnent jamais entre elles).

### P2 — Relation asymétrique INVERSÉE (`mentor-de`)
**Symptôme :** le graphe montre `Pluie-Menue —mentor-de→ Doigts-de-Craie`.
**Vérité texte :** Doigts-de-Craie est le **vieux maître**, Pluie-Menue son **apprentie** → la direction est
à l'envers (devrait être `Doigts-de-Craie —mentor-de→ Pluie-Menue`).
**Pourquoi ça compte :** une relation asymétrique (`mentor-de`, `parent-de`, `héritier-du-geste`) inversée
est *pire* que pas de relation — elle affirme un faux. 
**Piste :** vérifier l'assignation tête/queue (subject/object) dans l'extracteur de relations pour les
prédicats orientés. Un garde-fou de cohérence (âge/rôle : "le mentor est l'aîné/le maître") pourrait attraper
l'inversion.

### P3 — Alias CONFIRMÉ non appliqué à l'affichage (doublon)
**Symptôme :** `Sage` = `Front-Levé` est confirmé à 90 %, pourtant `characters.md` liste **deux** entrées
(`Front-Levé` ET `Sage (aka Front-Levé)`, chacune avec son profil) et le **nœud du graphe s'appelle "Sage"**,
pas Front-Levé.
**Preuve :** `CONFIRMED: [high] score=90% "Sage" = "Front-Levé"` au run, mais `characters.md` a les deux
sections, et `mindmap_pluie-menue.png` étiquette le nœud "Sage".
**Piste :** après confirmation d'alias, collapse effectif (merge d'entités OU résolution à l'export) vers le
**nom canonique du seed** (Front-Levé), et suppression du générique ("Sage"). Aujourd'hui la confirmation
semble stockée mais pas *appliquée* en aval.

### P4 — Persos seedés MAIS absents du chapitre → profils vides ou HALLUCINÉS
**Symptôme :** le seed ancre 20 persos ; ceux qui n'apparaissent pas dans T05 posent deux problèmes :
- **vides** (cosmétique) : Aube-Grise, Bec-Calme, Grain-de-Suie, Mère-des-Braises, Suie-d'Aval = entêtes sans contenu.
- **halluciné** (correctness) : `Main-de-Pierre` (perso T8, absent de T05) reçoit le profil *"son menton lui
  a valu son nom"* — c'est le trait de **Front-Levé**. Le profileur a fabriqué une description pour une entité
  sans mention réelle, en piochant du texte d'un autre perso.
**Piste :** (a) l'exporteur masque (ou marque "pas encore apparu") les persos seedés à **0 mention** dans le
corpus traité ; (b) le **profileur ne profile PAS** une entité à 0 mention (skip plutôt qu'halluciner) ; (c) le
contexte de profiling est scopé aux **mentions de l'entité elle-même**, pas au chapitre entier (règle sœur de P5).

### P5 — Identité/type : genre inféré faux + animal traité comme personne
**Symptômes :** l'Oracle profilé au **féminin** ("Elle… conseillère") alors que c'est l'Arbitre immortel ;
`Cendre` (une **grue**, un animal) est dans le glossaire des personnes et hérite du geste final de
Pluie-Menue (regarder l'eau descendre).
**Pistes :** (a) le genre pourrait venir du seed si on l'y ajoute ; (b) typage : distinguer animal/créature de
personne (le profil `novel` gagnerait un type "créature") ; (c) même fix de scope que P4c (le contexte de
profil qui bave d'un perso à l'autre est la cause commune de P4-halluciné et de la mésattribution de Cendre).

---

## 🎯 Questions de design (pas des bugs — à confirmer intentionnel)

- **Numéro de chapitre vs numéro de tour.** Le loader parse le n° de tour du nom de fichier (`CHAP_T05`→5)
  pour l'ORDRE, mais l'historique affiche "Chapitre 1" (turn_number séquentiel). Pour ce roman c'est en fait
  correct (T05 = 1er chapitre écrit = chapitre 1 du livre), mais confirme que ce mapping tour→chapitre-livre
  est voulu (sinon un traitement dans le désordre déroute).
- **Relations éparses (4 sur un chapitre riche).** L'extracteur est conservateur. Notamment la romance
  centrale Pluie-Menue×Front-Levé est classée `ami-de` (l'ontologie `novel` n'a peut-être pas de
  `amant-de`/`aime`). Un chapitre = peu de relations ; ça s'enrichit en incrémental, mais le prompt relations
  de `novel-v1` gagnerait à couvrir amour/couple/refus.

---

## Comment vérifier un fix

Re-tourne le run T05 ci-dessus sur une db neuve, puis check précisément :
1. `Peuple du ciel-clair` et `Peuple des nuages` restent **DEUX entités distinctes** (P1).
2. Le graphe montre `Doigts-de-Craie —mentor-de→ Pluie-Menue` (bon sens) (P2).
3. `characters.md` a **une seule** entrée Front-Levé, pas de "Sage" séparé ; le nœud graphe = "Front-Levé" (P3).
4. Aucun profil pour un perso à 0 mention ; pas de "menton" collé à Main-de-Pierre (P4).
5. Oracle non genré à tort ; Cendre hors du glossaire des personnes (ou typée créature) (P5).

Merci — le moteur est solide, c'est vraiment le pass de tuning des prompts `novel-v1` qui reste.
```
