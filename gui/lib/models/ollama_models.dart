/// Curated Ollama models offered for the ingestion pipeline.
///
/// WHY a single registry here rather than a hardcoded dropdown: this is the one
/// place the recommendations live, so the wizard and (later) Settings read the same
/// list — change a model or the recommended one here and both follow. Sized for the
/// target machine (RTX 5070 Ti, 16 GB VRAM); anything that wouldn't fit is left out
/// on purpose rather than offered and then swapping to slow CPU/RAM.
class RecommendedModel {
  /// The Ollama tag, e.g. `qwen3:14b` — exactly what `ollama pull` takes.
  final String id;

  /// Human label for the picker.
  final String label;

  /// Approximate on-disk / VRAM size, for the "~9 GB" hint next to the choice.
  final String size;

  /// One line on why you'd pick it.
  final String note;

  /// Exactly one entry should be recommended; the wizard preselects it.
  final bool recommended;

  const RecommendedModel({
    required this.id,
    required this.label,
    required this.size,
    required this.note,
    this.recommended = false,
  });
}

/// The offered models, recommended first. Kept short and curated — a wall of
/// models is a worse default than one good pick.
const List<RecommendedModel> kRecommendedModels = [
  RecommendedModel(
    id: 'qwen3:14b',
    label: 'Qwen3 14B',
    size: '~9 Go',
    note: 'Recommandé — excellent français, tourne à 100 % sur le GPU (16 Go).',
    recommended: true,
  ),
  RecommendedModel(
    id: 'qwen3:8b',
    label: 'Qwen3 8B',
    size: '~5 Go',
    note: 'Plus léger et plus rapide, bon français. Pour une machine plus modeste.',
  ),
  RecommendedModel(
    id: 'llama3.1:8b',
    label: 'Llama 3.1 8B',
    size: '~5 Go',
    note: 'Alternative solide ; français un cran en dessous de Qwen.',
  ),
];

/// The recommended model's id — the wizard's default selection and the app-wide
/// fallback when nothing else is chosen.
String get kDefaultRecommendedModelId =>
    kRecommendedModels.firstWhere((m) => m.recommended).id;
