import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../data/database.dart'; // AliasRow, RelationRow
import '../../data/daos/entity_dao.dart';
import '../../data/daos/relation_dao.dart'; // RelationWithNames
import '../../providers/entity_provider.dart';
import '../../providers/civilization_provider.dart';
import '../../providers/database_provider.dart';
import '../../providers/favorites_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/entity_type_badge.dart';
import '../../widgets/common/section_header.dart';
import 'widgets/naming_history.dart';
import 'widgets/notes_menu_button.dart';
import 'widgets/relation_list.dart';
import 'widgets/mention_timeline.dart';
import '../../models/entity_with_details.dart';

class EntityDetailScreen extends ConsumerStatefulWidget {
  final int entityId;
  const EntityDetailScreen({super.key, required this.entityId});

  @override
  ConsumerState<EntityDetailScreen> createState() => _EntityDetailScreenState();
}

class _EntityDetailScreenState extends ConsumerState<EntityDetailScreen> {
  // --------------- edit mode state ---------------
  bool _editMode = false;
  bool _saving = false;

  // Basic fields
  final _nameCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  String? _selectedType;
  int? _selectedCivId;

  // Tags (mutable copy of JSON array)
  List<String> _editTags = [];

  // Add-alias inline
  final _aliasCtrl = TextEditingController();

  // Add-relation inline
  bool _showAddRelation = false;
  String? _newRelType;
  int? _newRelTargetId;
  final _newRelDescCtrl = TextEditingController();
  final _relSearchCtrl = TextEditingController();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _descCtrl.dispose();
    _aliasCtrl.dispose();
    _newRelDescCtrl.dispose();
    _relSearchCtrl.dispose();
    super.dispose();
  }

  List<String> _parseTags(String? raw) {
    if (raw == null || raw.isEmpty) return [];
    try {
      return List<String>.from(jsonDecode(raw));
    } catch (_) {
      return [];
    }
  }

  void _enterEditMode(EntityWithDetails entity) {
    _nameCtrl.text = entity.entity.canonicalName;
    _descCtrl.text = entity.entity.description ?? '';
    _selectedType = entity.entity.entityType;
    _selectedCivId = entity.entity.civId;
    _editTags = _parseTags(entity.entity.tags);
    _showAddRelation = false;
    setState(() => _editMode = true);
  }

  void _cancelEditMode() {
    setState(() {
      _editMode = false;
      _showAddRelation = false;
    });
  }

  Future<void> _saveEditMode() async {
    final db = ref.read(databaseProvider);
    if (db == null) return;
    setState(() => _saving = true);
    try {
      await db.entityDao.updateEntity(
        entityId: widget.entityId,
        canonicalName: _nameCtrl.text.trim(),
        entityType: _selectedType!,
        civId: _selectedCivId,
        description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
      );
      await db.entityDao.updateEntityTags(widget.entityId, _editTags);
      if (mounted) setState(() => _editMode = false);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _confirmDisable(bool currentlyDisabled) async {
    if (currentlyDisabled) {
      final db = ref.read(databaseProvider);
      if (db == null) return;
      await db.entityDao.setEntityDisabled(widget.entityId, disabled: false);
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Désactiver cette entité ?'),
        content: const Text(
          'L\'entité sera retirée de toutes les vues.\n'
          'Vous pourrez la réactiver depuis la vue "Désactivées".',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Désactiver'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      final db = ref.read(databaseProvider);
      if (db == null) return;
      await db.entityDao.setEntityDisabled(widget.entityId, disabled: true);
      if (mounted) {
        if (context.canPop()) context.pop();
        else context.go('/entities');
      }
    }
  }

  // --------------- build ---------------

  @override
  Widget build(BuildContext context) {
    final entityAsync = ref.watch(entityDetailProvider(widget.entityId));

    return entityAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (entity) {
        if (entity == null) {
          return SelectionArea(
            child: Scaffold(
              appBar: AppBar(),
              body: const Center(child: Text('Entity not found')),
            ),
          );
        }
        return SelectionArea(
          child: Scaffold(
            appBar: _editMode
                ? _buildEditAppBar(context)
                : _buildViewAppBar(context, entity),
            body: NotesSideRail(
              attachment: NoteAttachment.entity,
              attachmentId: widget.entityId,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: _editMode
                      ? _buildEditBody(context, entity)
                      : _buildViewBody(context, entity),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  AppBar _buildViewAppBar(BuildContext context, EntityWithDetails entity) {
    final isFav = ref
        .watch(favoritesProvider)
        .contains('entity_${widget.entityId}');

    return AppBar(
      toolbarHeight: 44,
      title: Text(entity.entity.canonicalName),
      leading: IconButton(
        icon: const Icon(Icons.arrow_back),
        onPressed: () =>
            context.canPop() ? context.pop() : context.go('/entities'),
      ),
      actions: [
        // Favorite toggle
        IconButton(
          icon: Icon(
            isFav ? Icons.star : Icons.star_border,
            color: isFav ? Colors.amber : null,
          ),
          tooltip: isFav ? 'Retirer des favoris' : 'Ajouter aux favoris',
          onPressed: () => ref
              .read(favoritesProvider.notifier)
              .toggle('entity', widget.entityId, entity.entity.civId),
        ),
        IconButton(
          icon: const Icon(Icons.edit_outlined),
          tooltip: 'Modifier',
          onPressed: () => _enterEditMode(entity),
        ),
        IconButton(
          icon: const Icon(Icons.hub),
          tooltip: 'View in graph',
          onPressed: () =>
              context.go('/graph', extra: {'entityId': widget.entityId}),
        ),
        IconButton(
          icon: Icon(
            entity.entity.hidden ? Icons.visibility : Icons.visibility_off,
            color: entity.entity.hidden ? Colors.orange : null,
          ),
          tooltip: entity.entity.hidden
              ? 'Afficher (retirer du masquage)'
              : 'Cacher (masquer de la vue principale)',
          onPressed: () async {
            final db = ref.read(databaseProvider);
            if (db == null) return;
            await db.entityDao.setEntityHidden(
              widget.entityId,
              hidden: !entity.entity.hidden,
            );
          },
        ),
        IconButton(
          icon: Icon(Icons.block,
              color: entity.entity.disabled ? Colors.red : null),
          tooltip: entity.entity.disabled
              ? 'Réactiver cette entité'
              : 'Désactiver cette entité (retrait complet)',
          onPressed: () => _confirmDisable(entity.entity.disabled),
        ),
      ],
    );
  }

  AppBar _buildEditAppBar(BuildContext context) {
    return AppBar(
      toolbarHeight: 44,
      title: const Text('Modifier l\'entité'),
      leading: IconButton(
        icon: const Icon(Icons.close),
        tooltip: 'Annuler',
        onPressed: _cancelEditMode,
      ),
      actions: [
        FilledButton(
          onPressed: _saving ? null : _saveEditMode,
          child: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Enregistrer'),
        ),
        const SizedBox(width: 8),
      ],
    );
  }

  List<Widget> _buildViewBody(BuildContext context, EntityWithDetails entity) {
    final tags = _parseTags(entity.entity.tags);
    return [
      // Type + mention count + inactive badge
      Row(
        children: [
          EntityTypeBadge(entityType: entity.entity.entityType),
          const SizedBox(width: 12),
          Text(
            '${entity.mentionCount} mentions',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
          if (entity.entity.isActive == 0) ...[
            const SizedBox(width: 12),
            Chip(
              label: const Text('Inactive'),
              backgroundColor:
                  Theme.of(context).colorScheme.errorContainer,
              labelStyle: TextStyle(
                color: Theme.of(context).colorScheme.onErrorContainer,
              ),
            ),
          ],
        ],
      ),

      // Tags (semantic)
      if (tags.isNotEmpty) ...[
        const SizedBox(height: 8),
        Wrap(
          spacing: 4,
          runSpacing: 4,
          children: tags.map((tag) {
            final color = AppColors.entityTagColor(tag);
            return Chip(
              label: Text(
                tag,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      fontSize: 10,
                      color: color,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 4),
              side: BorderSide(color: color.withValues(alpha: 0.5)),
              backgroundColor: color.withValues(alpha: 0.08),
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              visualDensity: VisualDensity.compact,
            );
          }).toList(),
        ),
      ],

      // Description
      if (entity.entity.description != null) ...[
        const SizedBox(height: 16),
        Text(entity.entity.description!),
      ],

      // Naming history
      const SizedBox(height: 24),
      const SectionHeader(title: 'Historique des noms'),
      NamingHistory(entityId: widget.entityId),

      // Relations
      const SizedBox(height: 24),
      const SectionHeader(title: 'Relations'),
      RelationList(entityId: widget.entityId),

      // Mentions
      const SizedBox(height: 24),
      const SectionHeader(title: 'Mentions'),
      MentionTimeline(
          entityId: widget.entityId,
          entityName: entity.entity.canonicalName),
    ];
  }

  List<Widget> _buildEditBody(BuildContext context, EntityWithDetails entity) {
    final civsAsync = ref.watch(civListProvider);
    return [
      // Nom canonique
      TextFormField(
        controller: _nameCtrl,
        autofocus: true,
        decoration: const InputDecoration(labelText: 'Nom canonique *'),
      ),
      const SizedBox(height: 16),

      // Type
      DropdownButtonFormField<String>(
        value: _selectedType,
        decoration: const InputDecoration(labelText: 'Type *'),
        items: AppConstants.entityTypes
            .map((t) => DropdownMenuItem(value: t, child: Text(t)))
            .toList(),
        onChanged: (v) => setState(() => _selectedType = v),
      ),
      const SizedBox(height: 16),

      // Civilisation
      civsAsync.when(
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const SizedBox.shrink(),
        data: (civs) => DropdownButtonFormField<int?>(
          value: _selectedCivId,
          decoration: const InputDecoration(labelText: 'Civilisation'),
          items: [
            const DropdownMenuItem<int?>(value: null, child: Text('Aucune')),
            ...civs.map((c) => DropdownMenuItem(
                  value: c.civ.id,
                  child: Text(c.civ.name),
                )),
          ],
          onChanged: (v) => setState(() => _selectedCivId = v),
        ),
      ),
      const SizedBox(height: 16),

      // Description
      TextFormField(
        controller: _descCtrl,
        decoration: const InputDecoration(
          labelText: 'Description',
          alignLabelWithHint: true,
        ),
        maxLines: 5,
        minLines: 2,
      ),
      const SizedBox(height: 24),

      // Tags
      const SectionHeader(title: 'Tags'),
      _buildTagsEdit(context),
      const SizedBox(height: 24),

      // Aliases
      const SectionHeader(title: 'Aliases'),
      _buildAliasesEdit(context),
      const SizedBox(height: 24),

      // Relations
      const SectionHeader(title: 'Relations'),
      _buildRelationsEdit(context),
      const SizedBox(height: 24),

      // Mentions (read-only)
      const SectionHeader(title: 'Mentions'),
      MentionTimeline(
          entityId: widget.entityId,
          entityName: entity.entity.canonicalName),
    ];
  }

  Widget _buildTagsEdit(BuildContext context) {
    final allTagsAsync = ref.watch(entityTagsProvider);
    const vocab = [
      'militaire', 'religieux', 'politique', 'economique', 'culturel',
      'diplomatique', 'technologique', 'mythologique', 'actif', 'disparu',
      'emergent', 'legendaire',
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 4,
          runSpacing: 4,
          children: _editTags.map((tag) {
            final color = AppColors.entityTagColor(tag);
            return InputChip(
              label: Text(tag,
                  style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
              side: BorderSide(color: color.withValues(alpha: 0.5)),
              backgroundColor: color.withValues(alpha: 0.08),
              deleteIconColor: color,
              onDeleted: () => setState(() => _editTags.remove(tag)),
            );
          }).toList(),
        ),
        const SizedBox(height: 8),
        allTagsAsync.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (dbTags) {
            final available = {...dbTags, ...vocab}
                .where((t) => !_editTags.contains(t))
                .toList()..sort();
            if (available.isEmpty) return const SizedBox.shrink();
            return DropdownButton<String>(
              hint: const Text('+ Ajouter un tag'),
              value: null,
              items: available
                  .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                  .toList(),
              onChanged: (tag) {
                if (tag != null) setState(() => _editTags.add(tag));
              },
            );
          },
        ),
      ],
    );
  }

  Widget _buildAliasesEdit(BuildContext context) {
    final db = ref.watch(databaseProvider);
    if (db == null) return const SizedBox.shrink();
    return StreamBuilder<List<AliasRow>>(
      stream: db.entityDao.watchAliasesForEntity(widget.entityId),
      builder: (context, snapshot) {
        final aliases = snapshot.data ?? [];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Existing aliases — each with delete button
            ...aliases.map((a) => Row(
                  children: [
                    const Icon(Icons.label_outline, size: 16),
                    const SizedBox(width: 8),
                    Expanded(child: Text(a.alias)),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18),
                      tooltip: 'Supprimer cet alias',
                      color: Colors.red,
                      onPressed: () async {
                        await db.entityDao.removeAlias(a.id);
                      },
                    ),
                  ],
                )),
            // Add alias row
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _aliasCtrl,
                    decoration: const InputDecoration(
                      hintText: 'Nouvel alias…',
                      isDense: true,
                    ),
                    onSubmitted: (_) => _addAlias(db),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.add),
                  tooltip: 'Ajouter',
                  onPressed: () => _addAlias(db),
                ),
              ],
            ),
          ],
        );
      },
    );
  }

  Future<void> _addAlias(dynamic db) async {
    final text = _aliasCtrl.text.trim();
    if (text.isEmpty) return;
    await db.entityDao.addAlias(widget.entityId, text);
    _aliasCtrl.clear();
  }
  Widget _buildRelationsEdit(BuildContext context) {
    final db = ref.watch(databaseProvider);
    if (db == null) return const SizedBox.shrink();
    return StreamBuilder<List<RelationWithNames>>(
      stream: db.relationDao.watchRelationsWithNamesForEntity(widget.entityId),
      builder: (context, snapshot) {
        final relations = snapshot.data ?? [];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Existing relations — each with delete button
            ...relations.map((r) => Row(
                  children: [
                    Icon(r.isOutgoing ? Icons.arrow_forward : Icons.arrow_back,
                        size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${r.relatedName} · ${r.relation.relationType.replaceAll('_', ' ')}',
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18),
                      tooltip: 'Supprimer',
                      color: Colors.red,
                      onPressed: () async {
                        await db.relationDao.removeRelation(r.relation.id);
                      },
                    ),
                  ],
                )),
            // Add relation toggle
            if (!_showAddRelation)
              TextButton.icon(
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Ajouter une relation'),
                onPressed: () => setState(() {
                  _showAddRelation = true;
                  _newRelType = AppConstants.relationTypes.first;
                  _newRelTargetId = null;
                  // reset target
                  _newRelDescCtrl.clear();
                  _relSearchCtrl.clear();
                }),
              )
            else
              _buildAddRelationForm(context, db),
          ],
        );
      },
    );
  }

  Widget _buildAddRelationForm(BuildContext context, dynamic db) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Entity search autocomplete
            Autocomplete<EntityWithDetails>(
              fieldViewBuilder:
                  (context, ctrl, focusNode, onSubmit) => TextField(
                controller: ctrl,
                focusNode: focusNode,
                decoration: const InputDecoration(
                  labelText: 'Entité cible *',
                  isDense: true,
                ),
              ),
              optionsBuilder: (value) async {
                if (value.text.length < 2) return [];
                return db.entityDao.searchEntities(value.text);
              },
              displayStringForOption: (e) => e.entity.canonicalName,
              onSelected: (e) => setState(() {
                _newRelTargetId = e.entity.id;
              }),
            ),
            const SizedBox(height: 8),
            // Relation type dropdown
            DropdownButtonFormField<String>(
              value: _newRelType,
              decoration: const InputDecoration(
                  labelText: 'Type de relation *', isDense: true),
              items: AppConstants.relationTypes
                  .map((t) => DropdownMenuItem(
                      value: t,
                      child: Text(t.replaceAll('_', ' '))))
                  .toList(),
              onChanged: (v) => setState(() => _newRelType = v),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _newRelDescCtrl,
              decoration: const InputDecoration(
                  labelText: 'Description (optionnel)', isDense: true),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => setState(() => _showAddRelation = false),
                  child: const Text('Annuler'),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _newRelTargetId == null
                      ? null
                      : () async {
                          await db.relationDao.addRelation(
                            sourceEntityId: widget.entityId,
                            targetEntityId: _newRelTargetId!,
                            relationType: _newRelType!,
                            description: _newRelDescCtrl.text.trim().isEmpty
                                ? null
                                : _newRelDescCtrl.text.trim(),
                          );
                          setState(() => _showAddRelation = false);
                        },
                  child: const Text('Ajouter'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
