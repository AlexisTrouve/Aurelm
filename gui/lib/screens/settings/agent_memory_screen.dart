import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositories/agent_memory_repository.dart';
import '../../providers/agent_memory_provider.dart';
import '../../widgets/common/empty_state.dart';
import '../../widgets/common/loading_indicator.dart';

/// GM review surface for the agent's self-authored memories (migration 039).
///
/// The bot writes these from Arthur's feedback (saveMemory tool); here Arthur
/// audits them — edit a mis-stored one, toggle it off (same effect as the bot's
/// forgetMemory), or delete it for good. Reached from Settings (a sub-route, not
/// a rail destination).
class AgentMemoryScreen extends ConsumerWidget {
  const AgentMemoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final memoriesAsync = ref.watch(agentMemoryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mémoire de l\'agent')),
      body: memoriesAsync.when(
        loading: () => const LoadingIndicator(message: 'Chargement des mémoires…'),
        error: (e, _) => Center(child: Text('Erreur : $e')),
        data: (memories) {
          if (memories.isEmpty) {
            return const EmptyState(
              icon: Icons.psychology_outlined,
              message: 'Aucune mémoire',
              subtitle:
                  'L\'agent enregistrera ici ce qu\'il retient de tes retours (corrections, rulings, préférences).',
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: memories.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _MemoryCard(memory: memories[i]),
          );
        },
      ),
    );
  }
}

/// One memory row: type + scope chips, description/content, and per-row actions.
class _MemoryCard extends ConsumerWidget {
  final AgentMemory memory;
  const _MemoryCard({required this.memory});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final isPref = memory.memType == 'preference';
    final typeColor = isPref ? Colors.green : Colors.blue;

    return Opacity(
      // Dim forgotten (inactive) memories — kept visible so the GM can restore them.
      opacity: memory.active ? 1.0 : 0.5,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _chip(isPref ? 'préférence' : 'fait', typeColor),
                  const SizedBox(width: 6),
                  _chip(memory.civName ?? 'global', scheme.secondary),
                  if (memory.sourceTurn != null) ...[
                    const SizedBox(width: 6),
                    _chip('dès T${memory.sourceTurn}', Colors.orange),
                  ],
                  if (!memory.active) ...[
                    const SizedBox(width: 6),
                    _chip('oubliée', Colors.grey),
                  ],
                  const Spacer(),
                  Text(memory.memKey,
                      style: TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: scheme.onSurfaceVariant)),
                ],
              ),
              const SizedBox(height: 6),
              if (memory.description.isNotEmpty)
                Text(memory.description,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
              Text(memory.content),
              if (memory.links.isNotEmpty) ...[
                const SizedBox(height: 6),
                // Linked database articles (entities / turns / subjects) this memory concerns.
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    for (final label in memory.links)
                      _chip('🔗 $label', scheme.tertiary),
                  ],
                ),
              ],
              const SizedBox(height: 4),
              Row(
                children: [
                  const Spacer(),
                  // Toggle active — mirrors the bot's forgetMemory / restore.
                  IconButton(
                    tooltip: memory.active ? 'Oublier (désactiver)' : 'Réactiver',
                    icon: Icon(
                        memory.active ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                        size: 20),
                    onPressed: () async {
                      final repo = ref.read(agentMemoryRepositoryProvider);
                      if (repo == null) return;
                      await repo.setActive(memory.id, !memory.active);
                      ref.invalidate(agentMemoryProvider);
                    },
                  ),
                  IconButton(
                    tooltip: 'Modifier',
                    icon: const Icon(Icons.edit_outlined, size: 20),
                    onPressed: () => _openEdit(context, ref),
                  ),
                  IconButton(
                    tooltip: 'Supprimer',
                    icon: const Icon(Icons.delete_outline, size: 20),
                    color: Colors.red,
                    onPressed: () => _confirmDelete(context, ref),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _chip(String label, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(label, style: TextStyle(fontSize: 11, color: color)),
      );

  Future<void> _openEdit(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => _MemoryEditDialog(memory: memory),
    );
    if (ok == true) ref.invalidate(agentMemoryProvider);
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer cette mémoire ?'),
        content: Text('« ${memory.memKey} » sera définitivement supprimée.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Conserver')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      final repo = ref.read(agentMemoryRepositoryProvider);
      if (repo == null) return;
      await repo.delete(memory.id);
      ref.invalidate(agentMemoryProvider);
    }
  }
}

/// Edit dialog — the GM correcting a memory the bot stored.
class _MemoryEditDialog extends ConsumerStatefulWidget {
  final AgentMemory memory;
  const _MemoryEditDialog({required this.memory});

  @override
  ConsumerState<_MemoryEditDialog> createState() => _MemoryEditDialogState();
}

class _MemoryEditDialogState extends ConsumerState<_MemoryEditDialog> {
  late final TextEditingController _descCtrl;
  late final TextEditingController _contentCtrl;
  late String _type;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _descCtrl = TextEditingController(text: widget.memory.description);
    _contentCtrl = TextEditingController(text: widget.memory.content);
    _type = widget.memory.memType == 'preference' ? 'preference' : 'fact';
  }

  @override
  void dispose() {
    _descCtrl.dispose();
    _contentCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final content = _contentCtrl.text.trim();
    if (content.isEmpty) return;
    setState(() => _saving = true);
    final repo = ref.read(agentMemoryRepositoryProvider);
    if (repo != null) {
      await repo.update(
        widget.memory.id,
        description: _descCtrl.text.trim(),
        content: content,
        memType: _type,
      );
    }
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Modifier « ${widget.memory.memKey} »'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _descCtrl,
              decoration: const InputDecoration(labelText: 'Description (résumé)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _contentCtrl,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Contenu'),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              // CI builds on Flutter 3.27.4 where `value:` is the correct param
              // (`initialValue` does not exist there); it's only deprecated on dev 3.38.
              // ignore: deprecated_member_use
              value: _type,
              decoration: const InputDecoration(labelText: 'Type'),
              items: const [
                DropdownMenuItem(value: 'fact', child: Text('Fait / ruling')),
                DropdownMenuItem(value: 'preference', child: Text('Préférence')),
              ],
              onChanged: (v) => setState(() => _type = v ?? 'fact'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
            onPressed: _saving ? null : () => Navigator.of(context).pop(false),
            child: const Text('Annuler')),
        FilledButton(
          onPressed: _saving ? null : _save,
          child: const Text('Enregistrer'),
        ),
      ],
    );
  }
}
