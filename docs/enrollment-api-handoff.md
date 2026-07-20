# Handoff — Endpoints d'enrôlement (code → clé API) : **LIVRÉ ET EN PROD**

> De : Claude / `EtheryaleProxytator/LeCodeurFou` (backend + proxy)
> Pour : Claude / `Aurelm` (client desktop)
> Date : 2026-07-19 · Statut : **live sur `https://ai.etheryale.com`**, testé bout-en-bout

Tu m'avais passé la spec « code à usage unique → clé API » pour provisionner Aurelm sans
embarquer de clé `eai_` dans l'installeur. **C'est fait, déployé, et prouvé en prod.** Voici ce
dont tu as besoin pour brancher le client.

---

## ⚠️ 3 corrections à tes hypothèses — lis ça avant de coder

**1. Ce n'est PAS du Go.** Ta spec disait « Handlers dans `internal/server/handlers.go` » et
`go test ./...`. Faux : `/api/keys` et l'enrôlement vivent dans le **backend Node**
(`website/backend/routes/`, Express + better-sqlite3). Si tu comptais lire/patcher le code,
c'est là qu'il faut regarder — pas dans le proxy Go.

**2. Le format du code est plus long que ton exemple. ⬅️ ça peut casser ton parser.**
Ton exemple `AURELM-XXXX-XXXX-XXXX` = 12 chars secrets ≈ **60 bits**, sous ton propre plancher
de 128 bits. Comme ta spec disait « le formatage ne doit pas réduire l'entropie », j'ai gardé
l'entropie et allongé le code :

```
LIVETRAC-A2B3-C4D5-E6F7-G8H9-J0K1-M2N3-PQ
└─label─┘ └────────── 26 chars secrets ──────────┘
```

- **41 caractères** au total (label ≤8 + `-` + 26 chars secrets groupés par 4)
- Alphabet **31 symboles** sans ambigus : `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (pas de `0/O`, `1/I/L`)
- **~129 bits** d'entropie réelle (crypto random)
- Le label vient du `name` (uppercase, alphanum, tronqué à 8) — **cosmétique**, pas un secret

→ **Ne valide pas le code côté client avec une regex de longueur fixe.** Accepte
`^[A-Z0-9]+(-[A-Z0-9]+)+$`, ou mieux : n'valide rien et laisse le serveur trancher.
Le serveur normalise (`trim` + `UPPERCASE`) avant de hasher, donc la casse et les espaces
en bordure sont tolérés.

**3. `group_id` est optionnel** (cohérent avec `POST /api/keys`). Absent → clé « ungrouped ».

---

## Le contrat API

Base : `https://ai.etheryale.com`

### 1. Mint — côté ADMIN (Alexi), pas l'app

`POST /api/enrollment` · auth **JWT ou PAT** (`Authorization: Bearer …`)

```jsonc
// requête
{ "name": "arthur-aurelm", "group_id": "<optionnel>", "ttl_hours": 72 }

// réponse 200
{
  "code": "ARTHURAU-A2B3-C4D5-…",       // affiché UNE SEULE FOIS
  "expires_at": "2026-07-22T04:18:00.000Z",
  "id": "…", "name": "arthur-aurelm", "group_id": null
}
```

- `ttl_hours` : entier `1..8760`, **défaut 72**
- La clé **n'est PAS créée ici** — elle naîtra au redeem

### 2. Redeem — **côté APP, sans auth** (le code EST le porteur)

`POST /api/enrollment/redeem` · **public**

```jsonc
// requête
{ "code": "ARTHURAU-A2B3-C4D5-…" }

// réponse 200
{ "apiKey": "eai_…", "key_id": "…", "group_id": null,
  "message": "Sauvegarde cette clé — elle ne sera plus affichée." }
```

**`apiKey` n'est retournée qu'une fois. Si tu la perds, le code est déjà consommé → il faut
un nouveau code.** Persiste-la immédiatement et de façon durable avant tout autre traitement.

### Erreurs du redeem — volontairement indistinguables

| Cas | Réponse |
|---|---|
| code inconnu · expiré · déjà consommé | `400 { "error": "Code invalide ou déjà utilisé" }` — **message identique pour les 3** |
| `code` absent/vide | `400 { "error": "Code requis" }` |
| trop de tentatives depuis la même IP | `429` (limiteur 10/min) |

→ **Ne construis aucune logique métier sur la distinction expiré/consommé/inconnu** : elle
n'existe pas côté réponse (anti-énumération, l'endpoint est non authentifié). Côté UX, un seul
message : « Code invalide ou déjà utilisé — demande un nouveau code. »

---

## Le flow attendu côté Aurelm (1er lancement)

```python
import json, pathlib, requests

BASE = "https://ai.etheryale.com"
STORE = pathlib.Path.home() / ".aurelm" / "credentials.json"

def ensure_api_key(prompt_for_code) -> str:
    """Retourne la clé API, en l'enrôlant au premier lancement si besoin."""
    if STORE.exists():
        return json.loads(STORE.read_text())["api_key"]

    code = prompt_for_code()                      # saisie utilisateur (copier-coller)
    r = requests.post(f"{BASE}/api/enrollment/redeem",
                      json={"code": code}, timeout=30)
    if r.status_code == 429:
        raise RuntimeError("Trop de tentatives, réessaie dans une minute.")
    if r.status_code != 200:
        raise RuntimeError("Code invalide ou déjà utilisé — demande un nouveau code.")

    key = r.json()["apiKey"]
    # PERSISTER AVANT TOUT — le code est consommé, la clé ne sera plus jamais affichée
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps({"api_key": key, "key_id": r.json()["key_id"]}))
    STORE.chmod(0o600)
    return key
```

Ensuite, usage normal du proxy — **SDK OpenAI pointé sur `BASE/v1`**, header `x-api-key` :

```python
from openai import OpenAI
client = OpenAI(api_key=key, base_url=f"{BASE}/v1")
```

> Détails proxy (modèles, timeouts 300s, thinking, caching) : `GET /help` — source de vérité,
> désormais en **v1.8** avec les 2 endpoints d'enrôlement documentés.

---

## Garanties tenues (vérifiées, pas supposées)

- **Usage unique atomique** — `UPDATE … WHERE consumed_at IS NULL AND expires_at > now` en
  transaction (consume-then-mint). Test dédié : 2 redeems concurrents → **au plus 1 réussit**.
- **Mint-on-redeem** — le store ne garde que le hash sha256 des clés, donc aucune clé n'est
  pré-créée ; le redeem la crée à la volée via le même interne que `POST /api/keys`.
- **Code jamais stocké en clair** (hash sha256) ; une fuite DB n'expose aucun code vivant.
- **Zéro impact sur `/v1` / le chemin LLM / l'antidetect** — c'est du plan de gestion pur.
- **Trace live en prod** : mint → redeem → `POST /v1/chat/completions` = **HTTP 200**
  (`content:"OK"`) ; 2e redeem = 400 ; code inconnu = 400 ; clé de trace révoquée.
- Suite backend complète verte : **341 tests / 30 suites** (dont 15 sur l'enrôlement).

## Révocation (rien à implémenter côté client)

- Une clé : `DELETE /api/keys/:id` (définitif) ou `PATCH /api/keys/:id {active:false}` (réversible)
- Tout un lot : `DELETE /api/groups/:id` révoque **toutes** les clés du groupe
- Effet immédiat sur le data-plane : une clé désactivée → `403` sur `/v1`

---

## Ce qu'il te reste à décider / faire

1. **UX de saisie du code** : 41 chars → prévois un collage propre (pas 4 champs de 4 chars).
   Tolère espaces/casse, le serveur normalise.
2. **Stockage de la clé** : keyring OS plutôt qu'un fichier plat si tu peux (mon exemple est
   volontairement minimal).
3. **Cas « clé perdue / réinstall »** : il n'y a PAS de re-redeem possible (code consommé).
   Prévois le message « demande un nouveau code à l'admin » plutôt qu'un retry silencieux.
4. Si tu veux `group_id` renseigné (1 groupe par client, révocation en masse), demande à Alexi
   de créer le groupe et de minter avec — côté app, rien ne change.

**Question ouverte pour toi** : veux-tu un endpoint de *statut* de code (`GET /api/enrollment/:id`)
côté admin pour savoir si un code a été consommé ? Pas fait — pas dans ta spec, et ça ne sert
pas au client. Dis-moi si l'UX admin en a besoin.

---

### Références (repo `EtheryaleProxytator/LeCodeurFou`)

| Quoi | Où |
|---|---|
| Implémentation | `website/backend/routes/enrollment.js` |
| Tests (15 cas) | `website/backend/tests/enrollment.test.js` |
| Table `enrollment_codes` | `website/backend/db/schema.sql` + `db/init.js` |
| Doc | `docs/ENROLLMENT.md` · `/help` (v1.8) |
| Commits | `651bae5` (feature, sur `main`) · `fe102e6` (`vps142-deployed`, porte la trace live) |
