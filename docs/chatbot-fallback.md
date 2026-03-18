# Chatbot — Graceful Fallback API → claude -p

## Contexte

Le chatbot utilise l'API Anthropic (Claude) comme backend principal. Quand l'API est indisponible (503, 500, panne, quota dépassé, etc.), le bot tombait en erreur et renvoyait le message brut dans l'UI Flutter.

## Solution implémentée

### Comportement

1. L'API Anthropic lève n'importe quelle exception → le bot l'attrape
2. Un event `fallback` est émis dans le stream NDJSON
3. Le bot appelle `claude -p <message>` en subprocess (CLI Claude Code)
4. La réponse du CLI est émise comme event `text` normal
5. L'UI Flutter affiche un toast orange en bas à droite : *"API indisponible — bascule sur claude -p"*
6. Le backend reste `anthropic` — le message suivant retentera l'API normalement

### Pourquoi `claude -p` et pas Ollama

- Le chatbot tourne sur la machine d'Alexi (dev) ou d'Arthur (prod), pas sur une machine avec Ollama pour le chat
- `claude -p` utilise les credentials Claude Code (indépendants de l'API key du bot)
- Même modèle, même qualité de réponse — juste via un autre canal d'accès

### Fichiers modifiés

**`bot/agent.py`**
- Import `subprocess` ajouté
- Fonction `_run_claude_cli(prompt, timeout=120)` : wrapper async autour de `subprocess.run(["claude", "-p", prompt])`
- Dans `answer_streaming()`, le bloc `except Exception` sur l'appel Anthropic :
  ```python
  except Exception as _api_exc:
      yield ("fallback", {"reason": str(_api_exc)[:200], "backend": "claude-cli"})
      cli_response = await _run_claude_cli(new_message)
      yield ("text", {"content": cli_response, "tool_calls": []})
      return
  ```

**`gui/lib/services/chat_service.dart`**
- `FallbackEvent` ajouté comme nouveau subtype de `ChatEvent`
- Case `'fallback'` ajouté dans le switch NDJSON

**`gui/lib/providers/chat_provider.dart`**
- `usedFallback: bool` ajouté à `ChatState` (défaut `false`)
- Case `FallbackEvent` dans le switch → `state.copyWith(usedFallback: true)`

**`gui/lib/screens/chat/chat_screen.dart`**
- `ref.listen<bool>` sur `chatProvider.select((s) => s.usedFallback)` → `SnackBar` orange bottom-right à la transition `false → true`

### Tests

`bot/tests/test_agent_fallback.py` — 4 tests :
- `test_fallback_emits_event_on_503` — 503 → event fallback + réponse cli
- `test_no_fallback_on_clean_anthropic` — API OK → pas de fallback
- `test_any_error_triggers_fallback` — 401 → aussi un fallback
- `test_fallback_cli_also_fails` — CLI introuvable → message d'erreur gracieux, pas de crash

## Limites connues

- La réponse `claude -p` est **sans contexte** — le CLI ne reçoit que le dernier message, pas l'historique de la session
- Si `claude` CLI n'est pas installé ou pas authentifié sur la machine, la réponse sera `*(Fallback claude -p indisponible : ...)*`
- Non testé en condition réelle (l'API était up lors du dev — vérifier lors de la prochaine panne)

## À tester

Provoquer manuellement : couper temporairement le réseau ou changer l'URL `anthropic_base_url` dans `aurelm_config.json` vers une URL invalide, puis envoyer un message → vérifier le toast + réponse CLI.
