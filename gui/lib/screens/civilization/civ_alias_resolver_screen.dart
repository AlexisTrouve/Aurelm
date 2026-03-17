import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositories/civ_alias_repository.dart';
import '../../providers/civ_alias_provider.dart';
import '../../providers/civilization_provider.dart';
import '../../models/civ_with_stats.dart';

/// Full-screen resolver: the GM maps LLM-extracted "civilization" entity names
/// to known civs (or dismisses them as false positives).
///
/// Opened from the Dashboard or Settings when unresolved civ names exist.
class CivAliasResolverScreen extends ConsumerStatefulWidget {
  const CivAliasResolverScreen({super.key});

  @override
  ConsumerState<CivAliasResolverScreen> createState() =>
      _CivAliasResolverScreenState();
}

class _CivAliasResolverScreenState
    extends ConsumerState<CivAliasResolverScreen> {
  List<UnresolvedCivName> _unresolved = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) {
      setState(() => _loading = false);
      return;
    }
    final list = await repo.loadUnresolved();
    if (mounted) setState(() { _unresolved = list; _loading = false; });
  }

  Future<void> _mapToCiv(UnresolvedCivName item, int civId) async {
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) return;
    await repo.addAlias(civId, item.name);
    await _load();
  }

  Future<void> _dismiss(UnresolvedCivName item) async {
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) return;
    await repo.dismiss(item.name);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final civsAsync = ref.watch(civListProvider);

    final civs = civsAsync.valueOrNull ?? [];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Résoudre les alias de civilisations'),
        actions: [
          if (!_loading)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  '${_unresolved.length} non résolu${_unresolved.length > 1 ? 's' : ''}',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: cs.onSurfaceVariant,
                  ),
                ),
              ),
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _unresolved.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.check_circle_outline,
                          size: 48, color: cs.primary),
                      const SizedBox(height: 12),
                      Text('Tout est résolu !',
                          style: theme.textTheme.titleMedium),
                      const SizedBox(height: 4),
                      Text(
                        'Aucun nom de civilisation non résolu.',
                        style: theme.textTheme.bodySmall
                            ?.copyWith(color: cs.onSurfaceVariant),
                      ),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _unresolved.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, i) {
                    final item = _unresolved[i];
                    return _UnresolvedCard(
                      item: item,
                      civs: civs,
                      onMap: (civId) => _mapToCiv(item, civId),
                      onDismiss: () => _dismiss(item),
                    );
                  },
                ),
    );
  }
}

class _UnresolvedCard extends StatefulWidget {
  final UnresolvedCivName item;
  final List<CivWithStats> civs;
  final Future<void> Function(int civId) onMap;
  final Future<void> Function() onDismiss;

  const _UnresolvedCard({
    required this.item,
    required this.civs,
    required this.onMap,
    required this.onDismiss,
  });

  @override
  State<_UnresolvedCard> createState() => _UnresolvedCardState();
}

class _UnresolvedCardState extends State<_UnresolvedCard> {
  int? _selectedCivId;
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Name + mention count badge
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.item.name,
                    style: theme.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '${widget.item.mentionCount} mention${widget.item.mentionCount > 1 ? 's' : ''}',
                    style: theme.textTheme.labelSmall
                        ?.copyWith(color: cs.onSurfaceVariant),
                  ),
                ),
              ],
            ),

            // Mention passages — help GM identify what this name refers to
            if (widget.item.passages.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: cs.surfaceContainerLowest,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: cs.outlineVariant),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: widget.item.passages.map((p) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      p,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: cs.onSurfaceVariant,
                        height: 1.4,
                      ),
                    ),
                  )).toList(),
                ),
              ),
            ],

            const SizedBox(height: 12),

            // Dropdown + Mapper button
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<int>(
                    value: _selectedCivId,
                    hint: const Text('Mapper vers une civ...'),
                    decoration: const InputDecoration(
                      isDense: true,
                      contentPadding:
                          EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      border: OutlineInputBorder(),
                    ),
                    items: widget.civs
                        .map((c) => DropdownMenuItem(
                              value: c.civ.id,
                              child: Text(c.civ.name),
                            ))
                        .toList(),
                    onChanged: (v) => setState(() => _selectedCivId = v),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _selectedCivId == null || _busy
                      ? null
                      : () async {
                          setState(() => _busy = true);
                          await widget.onMap(_selectedCivId!);
                          if (mounted) setState(() => _busy = false);
                        },
                  child: _busy
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Mapper'),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // Dismiss as false positive
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                icon: const Icon(Icons.visibility_off_outlined, size: 16),
                label: const Text('Ignorer (faux positif)'),
                style: TextButton.styleFrom(
                  foregroundColor: cs.onSurfaceVariant,
                ),
                onPressed: _busy ? null : widget.onDismiss,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
