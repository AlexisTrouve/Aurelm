import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/civilization_provider.dart';
import '../../../providers/subject_provider.dart';

/// Dialog to create a new GM-created subject (no pipeline source turn).
class SubjectCreateDialog extends ConsumerStatefulWidget {
  const SubjectCreateDialog({super.key});

  @override
  ConsumerState<SubjectCreateDialog> createState() =>
      _SubjectCreateDialogState();
}

class _SubjectCreateDialogState extends ConsumerState<SubjectCreateDialog> {
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();

  String _direction = 'mj_to_pj';
  String _category = 'question';
  int? _civId;
  bool _saving = false;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final title = _titleCtrl.text.trim();
    if (title.isEmpty || _civId == null) return;

    setState(() => _saving = true);
    try {
      final newId = await createSubject(
        ref,
        civId: _civId!,
        direction: _direction,
        title: title,
        category: _category,
        description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(newId);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final civsAsync = ref.watch(civListProvider);

    return AlertDialog(
      title: const Text('Nouveau sujet'),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Civilisation
            civsAsync.when(
              loading: () => const CircularProgressIndicator(),
              error: (_, __) => const Text('Erreur chargement civs'),
              data: (civs) => DropdownButtonFormField<int>(
                decoration: const InputDecoration(
                  labelText: 'Civilisation *',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                value: _civId,
                items: civs
                    .map((c) => DropdownMenuItem(
                          value: c.civ.id,
                          child: Text(c.civ.name),
                        ))
                    .toList(),
                onChanged: (v) => setState(() => _civId = v),
              ),
            ),
            const SizedBox(height: 12),

            // Direction
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Direction',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              value: _direction,
              items: const [
                DropdownMenuItem(value: 'mj_to_pj', child: Text('MJ → PJ')),
                DropdownMenuItem(value: 'pj_to_mj', child: Text('PJ → MJ')),
              ],
              onChanged: (v) => setState(() => _direction = v!),
            ),
            const SizedBox(height: 12),

            // Category
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Catégorie',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              value: _category,
              items: const [
                DropdownMenuItem(value: 'choice', child: Text('Choix')),
                DropdownMenuItem(value: 'question', child: Text('Question')),
                DropdownMenuItem(value: 'initiative', child: Text('Initiative')),
                DropdownMenuItem(value: 'request', child: Text('Demande')),
              ],
              onChanged: (v) => setState(() => _category = v!),
            ),
            const SizedBox(height: 12),

            // Title
            TextField(
              controller: _titleCtrl,
              decoration: const InputDecoration(
                labelText: 'Titre *',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              autofocus: true,
              textCapitalization: TextCapitalization.sentences,
            ),
            const SizedBox(height: 12),

            // Description
            TextField(
              controller: _descCtrl,
              decoration: const InputDecoration(
                labelText: 'Description (optionnel)',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              maxLines: 3,
              textCapitalization: TextCapitalization.sentences,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(null),
          child: const Text('Annuler'),
        ),
        FilledButton(
          onPressed: _saving ? null : _submit,
          child: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Créer'),
        ),
      ],
    );
  }
}
