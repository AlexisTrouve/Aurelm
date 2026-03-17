import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../../../providers/civilization_provider.dart';
import '../../../providers/database_provider.dart';

/// Shared dialog for creating or editing an entity (GM action).
///
/// Create mode: pass no [entityId], form starts empty.
/// Edit mode: pass [entityId] + initial values, form pre-filled.
/// Returns the new entity id (int) on create, true on edit, null on cancel.
class EntityEditDialog extends ConsumerStatefulWidget {
  final int? entityId;
  final String? initialName;
  final String? initialType;
  final int? initialCivId;
  final String? initialDescription;

  const EntityEditDialog({
    super.key,
    this.entityId,
    this.initialName,
    this.initialType,
    this.initialCivId,
    this.initialDescription,
  });

  @override
  ConsumerState<EntityEditDialog> createState() => _EntityEditDialogState();
}

class _EntityEditDialogState extends ConsumerState<EntityEditDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameCtrl;
  late final TextEditingController _descCtrl;
  late String? _selectedType;
  late int? _selectedCivId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.initialName ?? '');
    _descCtrl = TextEditingController(text: widget.initialDescription ?? '');
    _selectedType = widget.initialType ?? AppConstants.entityTypes.first;
    _selectedCivId = widget.initialCivId;
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final db = ref.read(databaseProvider);
    if (db == null) return;
    setState(() => _saving = true);
    try {
      final name = _nameCtrl.text.trim();
      final desc = _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim();
      if (widget.entityId == null) {
        // Create new entity
        final newId = await db.entityDao.createEntity(
          canonicalName: name,
          entityType: _selectedType!,
          civId: _selectedCivId,
          description: desc,
        );
        if (mounted) Navigator.of(context).pop(newId);
      } else {
        // Update existing entity
        await db.entityDao.updateEntity(
          entityId: widget.entityId!,
          canonicalName: name,
          entityType: _selectedType!,
          civId: _selectedCivId,
          description: desc,
        );
        if (mounted) Navigator.of(context).pop(true);
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final civsAsync = ref.watch(civListProvider);
    final isCreate = widget.entityId == null;

    return AlertDialog(
      title: Text(isCreate ? 'Nouvelle entité' : 'Modifier l\'entité'),
      content: SizedBox(
        width: 480,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Canonical name
              TextFormField(
                controller: _nameCtrl,
                autofocus: true,
                decoration: const InputDecoration(labelText: 'Nom canonique *'),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Requis' : null,
              ),
              const SizedBox(height: 16),

              // Entity type dropdown
              DropdownButtonFormField<String>(
                value: _selectedType,
                decoration: const InputDecoration(labelText: 'Type *'),
                items: AppConstants.entityTypes
                    .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                    .toList(),
                onChanged: (v) => setState(() => _selectedType = v),
                validator: (v) => v == null ? 'Requis' : null,
              ),
              const SizedBox(height: 16),

              // Civ dropdown (optional) — populated from DB
              civsAsync.when(
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
                data: (civs) => DropdownButtonFormField<int?>(
                  value: _selectedCivId,
                  decoration: const InputDecoration(labelText: 'Civilisation'),
                  items: [
                    const DropdownMenuItem<int?>(
                        value: null, child: Text('Aucune')),
                    ...civs.map((c) => DropdownMenuItem(
                          value: c.civ.id,
                          child: Text(c.civ.name),
                        )),
                  ],
                  onChanged: (v) => setState(() => _selectedCivId = v),
                ),
              ),
              const SizedBox(height: 16),

              // Description (optional, multiline)
              TextFormField(
                controller: _descCtrl,
                decoration: const InputDecoration(
                  labelText: 'Description',
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                minLines: 2,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(),
          child: const Text('Annuler'),
        ),
        FilledButton(
          onPressed: _saving ? null : _save,
          child: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(isCreate ? 'Créer' : 'Enregistrer'),
        ),
      ],
    );
  }
}
