# Plan : OpenRouter comme provider LLM alternatif

## Contexte

Le pipeline tourne sur Ollama local (qwen3:8b, RTX 4060 8GB). Problemes :
- Lent (~5 min par tour, 30-45 min full pipeline)
- GGML OOM crashes sur les gros contextes
- Limité à 8B (pas assez de VRAM pour 14B)

Solution : ajouter OpenRouter comme provider alternatif pour accéder à qwen3:14b (ou plus gros) dans le cloud.

## État actuel — Appels LLM

4 modules appellent Ollama directement, avec 2 patterns différents :

| Module | Lib | Endpoint | Prompt format |
|--------|-----|----------|---------------|
| `fact_extractor.py` | httpx | `/api/generate` | string `prompt` + `system` |
| `entity_profiler.py` | ollama lib | `/api/chat` | messages array |
| `summarizer.py` | ollama lib | `/api/chat` | messages array |
| `alias_resolver.py` | ollama lib | `/api/chat` | messages array |

Pas d'abstraction — chaque module a son propre client.

## Différences de format

| Aspect | Ollama `/api/generate` | Ollama `/api/chat` | OpenRouter |
|--------|------------------------|---------------------|-----------|
| Endpoint | `localhost:11434/api/generate` | `localhost:11434/api/chat` | `openrouter.ai/api/v1/chat/completions` |
| Prompt | `"prompt": "..."` | `"messages": [...]` | `"messages": [...]` |
| System | `"system": "..."` | dans messages | `{"role": "system"}` dans messages |
| Response | `["response"]` | `["message"]["content"]` | `["choices"][0]["message"]["content"]` |
| Max tokens | `options.num_predict` | `options.num_predict` | `max_tokens` |
| Context | `options.num_ctx` | `options.num_ctx` | Non configurable |
| JSON mode | `format: {schema}` | `format: "json"` | `response_format: {"type": "json_object"}` |
| Seed | `options.seed` | `options.seed` | Non supporté |
| Auth | Aucune | Aucune | `Authorization: Bearer {key}` |

## Architecture proposée

### Nouveau module : `pipeline/pipeline/llm_provider.py`

```python
class LLMProvider:
    """Interface abstraite pour les appels LLM."""
    def chat(self, model, messages, temperature, max_tokens, json_mode, seed) -> str:
        """Envoie un prompt et retourne le texte de réponse."""
        raise NotImplementedError

class OllamaProvider(LLMProvider):
    """Wraps httpx calls to Ollama /api/generate + /api/chat."""
    def __init__(self, base_url="http://localhost:11434"):
        ...

class OpenRouterProvider(LLMProvider):
    """Calls OpenRouter OpenAI-compatible API."""
    def __init__(self, api_key, base_url="https://openrouter.ai/api/v1"):
        ...
```

### Interface unifiée

Tous les modules reçoivent un `LLMProvider` au lieu de construire leur propre client :

```python
# Avant
extractor = FactExtractor(model="qwen3:8b")

# Après
provider = OllamaProvider()  # ou OpenRouterProvider(api_key="...")
extractor = FactExtractor(provider=provider, model="qwen3:8b")
```

### Mapping des modèles

| Ollama (local) | OpenRouter |
|----------------|-----------|
| `qwen3:8b` | `qwen/qwen3-8b` |
| `qwen3:14b` | `qwen/qwen3-14b` |
| `llama3.1:8b` | `meta-llama/llama-3.1-8b-instruct` |

Le mapping est automatique dans le provider — le user passe toujours le nom Ollama.

## Fichiers à modifier

| Fichier | Action |
|---------|--------|
| `pipeline/pipeline/llm_provider.py` | **Nouveau** — LLMProvider, OllamaProvider, OpenRouterProvider |
| `pipeline/pipeline/fact_extractor.py` | Refactor — utiliser LLMProvider au lieu de httpx direct |
| `pipeline/pipeline/entity_profiler.py` | Refactor — utiliser LLMProvider au lieu de ollama lib |
| `pipeline/pipeline/summarizer.py` | Refactor — utiliser LLMProvider au lieu de ollama lib |
| `pipeline/pipeline/alias_resolver.py` | Refactor — utiliser LLMProvider au lieu de ollama lib |
| `pipeline/pipeline/runner.py` | Ajouter `--llm-provider` flag, instancier le provider |
| `pipeline/benchmark.py` | Ajouter `--llm-provider` flag |

## CLI

```bash
# Ollama local (défaut, inchangé)
python -m pipeline.runner --data-dir ... --civ ... --extraction-version v13.2-validate --model qwen3:8b

# OpenRouter
python -m pipeline.runner --data-dir ... --civ ... --extraction-version v13.2-validate \
  --llm-provider openrouter --model qwen3:14b

# Benchmark sur OpenRouter
python -m benchmark --extraction-version v13.2-validate \
  --llm-provider openrouter --model qwen3:14b --turn 11
```

La clé API via env var `OPENROUTER_API_KEY`.

## Gestion du retry

Le retry existant (`_post_with_retry`, 3 tentatives, backoff 5/10/15s) est déplacé dans le provider. Chaque provider gère ses propres erreurs transitoires :
- **Ollama** : GGML OOM, timeout
- **OpenRouter** : 429 rate limit, 502/503 gateway errors

## Coûts

| Provider | Modèle | Coût estimé (full pipeline 14 tours) |
|----------|--------|--------------------------------------|
| Ollama | qwen3:8b | $0 (local) |
| OpenRouter | qwen3:14b | ~$2-5 |
| OpenRouter | qwen3:8b | ~$0.50-1 |

## Phases d'implémentation

### Phase 1 : Provider abstraction (~1h)
- Créer `llm_provider.py` avec OllamaProvider + OpenRouterProvider
- Tests unitaires avec mock responses
- Le retry est dans le provider

### Phase 2 : Refactor modules (~2h)
- Adapter fact_extractor, entity_profiler, summarizer, alias_resolver
- Passer le provider via le constructeur
- Garder la rétro-compatibilité (défaut = Ollama)

### Phase 3 : CLI + config (~30min)
- `--llm-provider` dans runner.py et benchmark.py
- `OPENROUTER_API_KEY` env var
- Model name mapping automatique

### Phase 4 : Validation
- Benchmark turn 11 avec OpenRouter qwen3:14b
- Comparer P/R/F1 vs Ollama qwen3:8b
- Vérifier les coûts réels

## Notes

- Le seed n'est pas supporté par OpenRouter — les résultats ne seront pas reproductibles
- Le format schema Ollama n'a pas d'équivalent exact sur OpenRouter — on utilise `response_format: json_object` (moins strict)
- `/no_think` dans le system prompt devrait marcher sur OpenRouter aussi (c'est qwen3 qui le gère, pas Ollama)
