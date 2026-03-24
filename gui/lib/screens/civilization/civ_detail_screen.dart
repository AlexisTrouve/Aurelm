import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import '../../providers/civilization_provider.dart';
import '../../services/sync_service.dart';
import '../../providers/entity_provider.dart';
import '../../providers/turn_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/stat_card.dart';
import '../../widgets/common/section_header.dart';
import '../../screens/entities/widgets/notes_menu_button.dart';
import 'widgets/entity_breakdown_chart.dart';
import 'widgets/top_entities_list.dart';
import 'widgets/recent_turns_list.dart';
import 'widgets/civ_subjects_frame.dart';
import 'widgets/civ_sessions_frame.dart';
import 'widgets/civ_relations_frame.dart';
import '../../providers/civ_alias_provider.dart';
import '../../data/database.dart';
import '../../providers/database_provider.dart';
import '../../services/bot_config_service.dart';

Future<void> _confirmDeleteCiv(
    BuildContext context, WidgetRef ref, String civName, int civId) async {
  // Step 1
  final ok1 = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Supprimer cette civilisation ?'),
      content: Text(
          'Toutes les donnees de "$civName" seront supprimees '
          '(tours, entites, sujets, notes, relations).'),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler')),
        TextButton(
          style: TextButton.styleFrom(foregroundColor: Colors.red),
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Continuer'),
        ),
      ],
    ),
  );
  if (ok1 != true || !context.mounted) return;

  // Step 2
  final ok2 = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Vraiment supprimer ?'),
      content: Text(
          'Cette action est irreversible. '
          'La civilisation "$civName" et toutes ses donnees seront perdues.'),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler')),
        TextButton(
          style: TextButton.styleFrom(foregroundColor: Colors.red),
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Oui, supprimer'),
        ),
      ],
    ),
  );
  if (ok2 != true || !context.mounted) return;

  // Step 3 — type the name
  final typed = await showDialog<String>(
    context: context,
    builder: (ctx) {
      String input = '';
      return AlertDialog(
        title: const Text('Derniere confirmation'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Tapez "$civName" pour confirmer la suppression.'),
            const SizedBox(height: 12),
            TextField(
              autofocus: true,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Nom de la civilisation',
              ),
              onChanged: (v) => input = v,
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, null),
              child: const Text('Annuler')),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, input),
            child: const Text('SUPPRIMER DEFINITIVEMENT'),
          ),
        ],
      );
    },
  );
  if (typed == null || typed.trim() != civName || !context.mounted) {
    if (typed != null && typed.trim() != civName && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Nom incorrect — suppression annulee')));
    }
    return;
  }

  // Execute
  final db = ref.read(databaseProvider);
  if (db == null) return;
  await db.civilizationDao.deleteCiv(civId);
  if (context.mounted) {
    context.go('/');
  }
}

class CivDetailScreen extends ConsumerWidget {
  final int civId;

  const CivDetailScreen({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final civAsync = ref.watch(civDetailProvider(civId));

    return civAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (civWithStats) {
        if (civWithStats == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Civilization not found')),
          );
        }

        final civ = civWithStats.civ;
        final briefAsync = ref.watch(civBriefProvider(civId));
        return Scaffold(
          appBar: AppBar(
            title: Text(civ.name),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.go('/'),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.hub_outlined),
                tooltip: 'Relations de cette civilisation',
                onPressed: () => context.push(
                  '/civs/relations',
                  extra: <String, dynamic>{'focusCivId': civId},
                ),
              ),
              IconButton(
                icon: Icon(Icons.delete_forever,
                    color: Colors.red[300]),
                tooltip: 'Supprimer cette civilisation',
                onPressed: () =>
                    _confirmDeleteCiv(context, ref, civ.name, civId),
              ),
            ],
          ),
          body: NotesSideRail(
            attachment: NoteAttachment.civ,
            attachmentId: civId,
            child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Civ brief — recent turn summaries
                briefAsync.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (turns) {
                    if (turns.isEmpty) return const SizedBox.shrink();
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 24),
                      child: Theme(
                        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                        child: ExpansionTile(
                          tilePadding: EdgeInsets.zero,
                          initiallyExpanded: true,
                          title: Text('Historique récent',
                              style: Theme.of(context).textTheme.titleSmall),
                          children: turns.map((turn) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Tour ${turn.turnNumber}',
                                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                        color: Theme.of(context).colorScheme.primary,
                                        fontWeight: FontWeight.w600,
                                      ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  turn.detailedSummary!,
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                                        height: 1.5,
                                      ),
                                ),
                              ],
                            ),
                          )).toList(),
                        ),
                      ),
                    );
                  },
                ),

                // Header info — player + discord channel
                _CivInfoHeader(civ: civ),

                // Discord sync — pending messages + import
                if (civ.discordChannelId != null &&
                    civ.discordChannelId!.isNotEmpty)
                  _CivSyncSection(civ: civ),

                // Stats row
                Row(
                  children: [
                    Expanded(
                      child: StatCard(
                        icon: Icons.history,
                        label: 'Turns',
                        value: '${civWithStats.turnCount}',
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: StatCard(
                        icon: Icons.category,
                        label: 'Entities',
                        value: '${civWithStats.entityCount}',
                        color: Theme.of(context).colorScheme.tertiary,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Entity breakdown chart
                const SectionHeader(title: 'Entity Breakdown'),
                SizedBox(
                  height: 250,
                  child: EntityBreakdownChart(civId: civId),
                ),

                const SizedBox(height: 24),

                // Top entities — "View all" pré-filtre par civ
                SectionHeader(
                  title: 'Top Entities',
                  trailing: TextButton(
                    onPressed: () {
                      ref.read(entityFilterProvider.notifier).setCivId(civId);
                      context.go('/entities');
                    },
                    child: const Text('View all'),
                  ),
                ),
                TopEntitiesList(civId: civId),

                const SizedBox(height: 24),

                // Sujets (5 récents + stats + lien filtré)
                CivSubjectsFrame(civId: civId),

                const SizedBox(height: 24),

                // Sessions chat taggées avec cette civ
                CivSessionsFrame(civName: civ.name),

                // Civ aliases — noms alternatifs gérés par le GM
                _CivAliasesSection(civId: civId),


                // Inter-civ relations (populated by pipeline profiler)
                CivRelationsFrame(civId: civId),

                const SizedBox(height: 24),

                // Recent turns — tiles cliquables + "View all" pré-filtré par civ
                SectionHeader(
                  title: 'Recent Turns',
                  trailing: TextButton(
                    onPressed: () {
                      ref.read(timelineFilterProvider.notifier).setCivId(civId);
                      context.go('/timeline');
                    },
                    child: const Text('View all'),
                  ),
                ),
                RecentTurnsList(civId: civId),
              ],
            ),
          ),
          ),
        );
      },
    );
  }
}

/// Shows aliases for a civ with add + delete. Inline, no separate screen.
class _CivAliasesSection extends ConsumerStatefulWidget {
  final int civId;
  const _CivAliasesSection({required this.civId});

  @override
  ConsumerState<_CivAliasesSection> createState() => _CivAliasesSectionState();
}

class _CivAliasesSectionState extends ConsumerState<_CivAliasesSection> {
  final _controller = TextEditingController();
  bool _adding = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final name = _controller.text.trim();
    if (name.isEmpty) return;
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) return;
    await repo.addAlias(widget.civId, name);
    _controller.clear();
    setState(() => _adding = false);
    ref.invalidate(civAliasesProvider(widget.civId));
  }

  Future<void> _delete(int aliasId) async {
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) return;
    await repo.deleteAlias(aliasId);
    ref.invalidate(civAliasesProvider(widget.civId));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final aliasesAsync = ref.watch(civAliasesProvider(widget.civId));

    final aliases = aliasesAsync.valueOrNull ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: Text('Aliases',
                  style: theme.textTheme.titleSmall
                      ?.copyWith(fontWeight: FontWeight.w600)),
            ),
            IconButton(
              icon: const Icon(Icons.add, size: 18),
              tooltip: 'Ajouter un alias',
              onPressed: () => setState(() => _adding = !_adding),
            ),
          ],
        ),
        if (_adding) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  autofocus: true,
                  decoration: const InputDecoration(
                    hintText: 'Nom alternatif...',
                    isDense: true,
                    border: OutlineInputBorder(),
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  ),
                  onSubmitted: (_) => _add(),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(onPressed: _add, child: const Text('Ajouter')),
              const SizedBox(width: 4),
              TextButton(
                onPressed: () => setState(() { _adding = false; _controller.clear(); }),
                child: const Text('Annuler'),
              ),
            ],
          ),
        ],
        if (aliases.isEmpty && !_adding)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 4),
            child: Text('Aucun alias',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: cs.onSurfaceVariant)),
          )
        else ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: aliases.map((a) => Chip(
                  label: Text(a.aliasName, style: theme.textTheme.labelSmall),
                  deleteIcon: const Icon(Icons.close, size: 14),
                  onDeleted: () => _delete(a.id),
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                )).toList(),
          ),
        ],
      ],
    );
  }
}

/// Editable header: player name + Discord channel picker.
class _CivInfoHeader extends ConsumerStatefulWidget {
  final CivRow civ;
  const _CivInfoHeader({required this.civ});

  @override
  ConsumerState<_CivInfoHeader> createState() => _CivInfoHeaderState();
}

class _CivInfoHeaderState extends ConsumerState<_CivInfoHeader> {
  List<Map<String, dynamic>>? _discordChannels;
  bool _fetching = false;

  String _channelLabel() {
    final civ = widget.civ;
    if (civ.discordChannelId == null || civ.discordChannelId!.isEmpty) {
      return 'Aucun';
    }
    // Use stored names (never show raw ID)
    if (civ.discordGuildName != null && civ.discordChannelName != null) {
      return '#${civ.discordGuildName}/${civ.discordChannelName}';
    }
    // Fallback: try fetched channels
    final ch = _discordChannels
        ?.where((c) => c['id'] == civ.discordChannelId)
        .firstOrNull;
    if (ch != null) return '#${ch['guild_name']}/${ch['name']}';
    return 'Channel lie';
  }

  Future<void> _fetchChannels() async {
    setState(() => _fetching = true);
    _discordChannels = await BotConfigService.fetchDiscordChannels();
    if (mounted) setState(() => _fetching = false);
  }

  Future<void> _pickChannel() async {
    if (_discordChannels == null) await _fetchChannels();
    if (_discordChannels == null || _discordChannels!.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content:
                Text('Bot non connecte - impossible de charger les channels')));
      }
      return;
    }
    if (!mounted) return;
    final picked = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('Choisir un channel Discord'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(ctx, ''),
            child: const Text('Aucun (retirer le lien)',
                style: TextStyle(color: Colors.grey)),
          ),
          ..._discordChannels!.map((ch) => SimpleDialogOption(
                onPressed: () => Navigator.pop(ctx, ch['id'] as String),
                child: Text('#${ch['guild_name']}/${ch['name']}'),
              )),
        ],
      ),
    );
    if (picked == null) return;
    final db = ref.read(databaseProvider);
    if (db == null) return;
    // Find names for the picked channel
    final pickedCh = _discordChannels
        ?.where((c) => c['id'] == picked)
        .firstOrNull;
    await db.civilizationDao.updateCivChannel(
      widget.civ.id,
      channelId: picked.isEmpty ? null : picked,
      guildName: picked.isEmpty ? null : pickedCh?['guild_name'] as String?,
      channelName: picked.isEmpty ? null : pickedCh?['name'] as String?,
    );
    ref.invalidate(civDetailProvider(widget.civ.id));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.civ.playerName != null)
            Text('Joueur: ${widget.civ.playerName}',
                style: theme.textTheme.titleMedium
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
          const SizedBox(height: 4),
          Row(
            children: [
              const Icon(Icons.tag, size: 16, color: Colors.grey),
              const SizedBox(width: 4),
              Text(
                  'Discord: ${_channelLabel()}',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
              const SizedBox(width: 8),
              TextButton.icon(
                onPressed: _fetching ? null : _pickChannel,
                icon: _fetching
                    ? const SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.edit, size: 14),
                label: const Text('Changer'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Discord sync section: check pending messages, preview, import.
class _CivSyncSection extends ConsumerStatefulWidget {
  final CivRow civ;
  const _CivSyncSection({required this.civ});

  @override
  ConsumerState<_CivSyncSection> createState() => _CivSyncSectionState();
}

class _CivSyncSectionState extends ConsumerState<_CivSyncSection> {
  Map<String, dynamic>? _pending;
  bool _checking = false;
  bool _syncing = false;

  // Progress polling is now handled by the modal _SyncProgressDialog

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _checkPending() async {
    setState(() => _checking = true);
    final service = SyncService();
    final result =
        await service.channelPending(widget.civ.discordChannelId!);
    if (mounted) setState(() { _pending = result; _checking = false; });
  }

  /// Warning card when no GM author is detected — lets user pick one from the
  /// list of unique authors returned by the pending endpoint.
  Widget _buildNoGmWarning(BuildContext context) {
    final authors =
        (_pending?['authors'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    return Padding(
      padding: const EdgeInsets.only(top: 8, bottom: 4),
      child: Card(
        color: Colors.orange.withAlpha(30),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.warning_amber, color: Colors.orange, size: 18),
                  const SizedBox(width: 8),
                  Text('Aucun auteur MJ detecte',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: Colors.orange, fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 8),
              const Text('Selectionnez le compte Discord du MJ :'),
              const SizedBox(height: 4),
              ...authors.map((a) => ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      a['is_gm'] == true ? Icons.shield : Icons.person,
                      size: 18,
                      color: a['is_gm'] == true ? Colors.green : null,
                    ),
                    title: Text(a['name'] as String? ?? '?'),
                    subtitle: Text('ID: ${a['id']}',
                        style: Theme.of(context).textTheme.bodySmall),
                    trailing: a['is_gm'] == true
                        ? const Chip(label: Text('MJ'))
                        : TextButton(
                            onPressed: () => _assignGmAuthor(
                                a['id'] as String, a['name'] as String),
                            child: const Text('Definir comme MJ'),
                          ),
                  )),
            ],
          ),
        ),
      ),
    );
  }

  /// Save the selected Discord user ID as a GM author in the config,
  /// then re-check pending to refresh turn detection.
  Future<void> _assignGmAuthor(String discordId, String displayName) async {
    final dbPath = ref.read(dbPathProvider);
    if (dbPath == null) return;

    final config = await BotConfigService.load(dbPath);

    // Add both the Discord ID and the display name (for pipeline fallback)
    final updatedIds = [...config.gmDiscordIds];
    if (!updatedIds.contains(discordId)) updatedIds.add(discordId);

    final updatedNames = [...config.gmAuthors];
    if (!updatedNames.any((n) =>
        displayName.toLowerCase().startsWith(n.toLowerCase()))) {
      updatedNames.add(displayName);
    }

    await BotConfigService.save(dbPath, config.copyWith(
      gmAuthors: updatedNames,
      gmDiscordIds: updatedIds,
    ));

    // Tell the bot to reload its config
    try {
      await http.post(Uri.parse('http://127.0.0.1:${config.botPort}/reload-config'));
    } catch (_) {
      // Bot may not support this endpoint yet — config saved, restart will pick it up
    }

    // Re-check pending with updated detection
    if (mounted) _checkPending();
  }

  Future<void> _syncChannel({List<int>? turnIndices}) async {
    if (!mounted) return;
    setState(() => _syncing = true);

    // Show blocking modal dialog with progress
    final channelId = widget.civ.discordChannelId!;
    final label = turnIndices != null
        ? 'Import de ${turnIndices.length} tour(s)'
        : 'Import de tous les tours';

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => _SyncProgressDialog(
        channelId: channelId,
        turnIndices: turnIndices,
        title: label,
      ),
    ).then((result) {
      if (!mounted) return;
      setState(() { _syncing = false; _pending = null; });

      if (result == true) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$label - termine')));
      } else if (result is String) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Erreur: $result')));
      }

      // Always refresh civ data + re-check pending after sync (success or failure).
      // Invalidate all civ-related providers — Drift streams don't detect external
      // writes (Python pipeline writes via a separate SQLite connection).
      ref.invalidate(civDetailProvider(widget.civ.id));
      ref.invalidate(civListProvider);
      ref.invalidate(civBriefProvider(widget.civ.id));
      _checkPending();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final newMsgs = _pending?['new_messages'] as int? ?? 0;
    final gmTurns = _pending?['gm_turns'] as int? ?? 0;
    final playerTurns = _pending?['player_turns'] as int? ?? 0;
    final turns =
        (_pending?['turns'] as List?)?.cast<Map<String, dynamic>>() ?? [];

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.sync, size: 18),
                const SizedBox(width: 8),
                Text('Discord Sync',
                    style: theme.textTheme.titleSmall),
                const Spacer(),
                TextButton.icon(
                  onPressed: _checking ? null : _checkPending,
                  icon: _checking
                      ? const SizedBox(
                          width: 14, height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.refresh, size: 16),
                  label: const Text('Verifier'),
                ),
              ],
            ),

            // Status
            if (_pending == null && !_checking)
              Text('Cliquez "Verifier" pour detecter les nouveaux messages.',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: Colors.grey)),

            if (_pending != null) ...[
              const SizedBox(height: 8),
              // Summary
              Row(
                children: [
                  _statChip(Icons.message, '$newMsgs messages',
                      newMsgs > 0 ? Colors.amber : Colors.grey),
                  const SizedBox(width: 8),
                  _statChip(Icons.auto_stories, '$gmTurns tours MJ',
                      gmTurns > 0 ? Colors.green : Colors.grey),
                  const SizedBox(width: 8),
                  _statChip(Icons.person, '$playerTurns reponses PJ',
                      playerTurns > 0 ? Colors.blue : Colors.grey),
                ],
              ),

              // Warn if no GM detected — offer to assign one
              if (_pending != null && gmTurns == 0 && newMsgs > 0)
                _buildNoGmWarning(context),

              // Turn preview (grouped, not raw messages)
              if (turns.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('Tours detectes',
                    style: theme.textTheme.labelMedium),
                const SizedBox(height: 4),
                Container(
                  constraints: const BoxConstraints(maxHeight: 250),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerLow,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: ListView.separated(
                    shrinkWrap: true,
                    padding: const EdgeInsets.all(8),
                    itemCount: turns.length,
                    separatorBuilder: (_, __) =>
                        const Divider(height: 1),
                    itemBuilder: (_, i) {
                      final turn = turns[i];
                      final isMj = turn['type'] == 'MJ';
                      final msgCount = turn['messages'] as int? ?? 0;
                      return Padding(
                        padding: const EdgeInsets.symmetric(
                            vertical: 4),
                        child: Row(
                          crossAxisAlignment:
                              CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: isMj
                                    ? Colors.green.withAlpha(40)
                                    : Colors.blue.withAlpha(40),
                                borderRadius:
                                    BorderRadius.circular(4),
                              ),
                              child: Text(
                                isMj ? 'MJ' : 'PJ',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: isMj
                                      ? Colors.green
                                      : Colors.blue,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${turn['author']} ($msgCount msgs)',
                                    style: theme.textTheme.labelSmall
                                        ?.copyWith(
                                            fontWeight:
                                                FontWeight.w600),
                                  ),
                                  Text(
                                    turn['preview'] as String? ?? '',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: theme.textTheme.bodySmall,
                                  ),
                                ],
                              ),
                            ),
                            // Per-turn import button
                            IconButton(
                              icon: const Icon(Icons.download,
                                  size: 16),
                              tooltip: 'Importer ce tour',
                              padding: EdgeInsets.zero,
                              constraints: const BoxConstraints(),
                              onPressed: _syncing
                                  ? null
                                  : () => _syncChannel(
                                      turnIndices: [i]),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ],

              // Progress is now shown in the modal dialog

              // Import button
              if (newMsgs > 0 && !_syncing) ...[
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: _syncChannel,
                  icon: const Icon(Icons.download),
                  label: Text(
                      'Importer tout ($gmTurns tours MJ)'),
                ),
              ],

              if (newMsgs == 0 && !_syncing)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text('Aucun nouveau message a importer.',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: Colors.green)),
                ),
            ],
          ],
        ),
      ),
    );
  }

  // Progress is now shown in the blocking _SyncProgressDialog
  // (progress is shown in the modal _SyncProgressDialog)

  Widget _statChip(IconData icon, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withAlpha(30),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(80)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(label,
              style: TextStyle(fontSize: 12, color: color)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Blocking modal dialog that shows sync progress with polling
// ---------------------------------------------------------------------------

class _SyncProgressDialog extends StatefulWidget {
  final String channelId;
  final List<int>? turnIndices;
  final String title;

  const _SyncProgressDialog({
    required this.channelId,
    required this.turnIndices,
    required this.title,
  });

  @override
  State<_SyncProgressDialog> createState() => _SyncProgressDialogState();
}

class _SyncProgressDialogState extends State<_SyncProgressDialog> {
  Timer? _timer;
  Map<String, dynamic>? _progress;
  bool _done = false;
  String? _error;

  // ETA tracking: measure elapsed time vs calls done to estimate remaining
  DateTime? _startTime;

  @override
  void initState() {
    super.initState();
    _startTime = DateTime.now();
    // Start sync request + progress polling
    _startSync();
    _timer = Timer.periodic(
        const Duration(seconds: 2), (_) => _pollProgress());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _startSync() async {
    try {
      final service = SyncService();
      await service.syncChannel(widget.channelId,
          turnIndices: widget.turnIndices);
      if (mounted) {
        setState(() => _done = true);
        // Auto-close after brief delay so user sees "done"
        Future.delayed(const Duration(milliseconds: 800), () {
          if (mounted) Navigator.of(context).pop(true);
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() { _done = true; _error = e.toString(); });
        // Don't auto-close on error — let user read
      }
    }
  }

  Future<void> _pollProgress() async {
    if (_done) return;
    try {
      final resp = await http
          .get(Uri.parse('http://127.0.0.1:8473/progress'))
          .timeout(const Duration(seconds: 3));
      if (!mounted) return;
      if (resp.statusCode == 200) {
        setState(() =>
            _progress = jsonDecode(resp.body) as Map<String, dynamic>);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: Row(
        children: [
          if (!_done)
            const SizedBox(
                width: 20, height: 20,
                child: CircularProgressIndicator(strokeWidth: 2.5))
          else if (_error != null)
            const Icon(Icons.error, color: Colors.red, size: 20)
          else
            const Icon(Icons.check_circle, color: Colors.green, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(widget.title,
              style: theme.textTheme.titleSmall)),
        ],
      ),
      content: SizedBox(
        width: 400,
        child: _done
            ? _buildDoneContent(theme)
            : _buildProgressContent(theme),
      ),
      actions: _done && _error != null
          ? [
              FilledButton(
                onPressed: () => Navigator.of(context).pop(_error),
                child: const Text('Fermer'),
              ),
            ]
          : null,
    );
  }

  Widget _buildDoneContent(ThemeData theme) {
    if (_error != null) {
      return Text('Erreur: $_error',
          style: TextStyle(color: theme.colorScheme.error));
    }
    return const Text('Import termine !');
  }

  Widget _buildProgressContent(ThemeData theme) {
    final phases = (_progress?['phases'] as List?) ?? [];
    if (phases.isEmpty) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Demarrage du pipeline...'),
          const SizedBox(height: 16),
          const LinearProgressIndicator(),
        ],
      );
    }

    if (phases[0] is! Map<String, dynamic>) {
      return const LinearProgressIndicator();
    }

    final p = phases[0] as Map<String, dynamic>;
    final currentTurn = p['current_unit'] as int? ?? 0;
    final totalTurns = p['total_units'] as int? ?? 1;
    final stageName = p['stage_name'] as String? ?? '';
    final callsDone = p['llm_calls_done'] as int? ?? 0;
    final callsTotal = p['llm_calls_total'] as int? ?? 1;
    final turnNumber = p['turn_number'] as int?;

    final stageLabel = switch (stageName) {
      'extraction' => 'Extraction entites',
      'validation' => 'Validation entites',
      'summarization' => 'Resume',
      'subjects' => 'Sujets MJ/PJ',
      'profiling' => 'Profiling entites',
      'pj_extraction' => 'Extraction PJ',
      'preanalysis' => 'Pre-analyse',
      'civ_relations' => 'Relations inter-civs',
      'aliases' => 'Resolution aliases',
      _ => stageName.isNotEmpty ? stageName : 'En cours...',
    };

    // Determine the current pipeline step (for the top-level progress bar)
    // Steps: extraction (6) -> preanalysis (6.5) -> subjects (7) -> profiling (8)
    //        -> civ_relations (8.5) -> aliases (9) -> wiki (10)
    const pipelineSteps = [
      'extraction', 'validation', 'summarization', 'pj_extraction',
      'preanalysis', 'subjects', 'profiling', 'civ_relations', 'aliases',
    ];
    const pipelineStepLabels = [
      '6. Extraction', '6. Validation', '6. Resume', '6. PJ',
      '6.5 Pre-analyse', '7. Sujets', '8. Profiling', '8.5 Relations', '9. Aliases',
    ];
    // Find current step index (defaults to 0 if unknown)
    int stepIdx = pipelineSteps.indexOf(stageName);
    if (stepIdx < 0) stepIdx = 0;
    final stepLabel = pipelineStepLabels[stepIdx];
    final stepProgress = (stepIdx + 1) / pipelineSteps.length;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Pipeline stage (top-level)
        Row(
          children: [
            const Icon(Icons.list_alt, size: 16),
            const SizedBox(width: 6),
            Text('Etape: $stepLabel',
                style: theme.textTheme.labelMedium
                    ?.copyWith(fontWeight: FontWeight.w600)),
            const Spacer(),
            Text('${stepIdx + 1}/${pipelineSteps.length}',
                style: theme.textTheme.bodySmall),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: stepProgress,
            minHeight: 6,
            color: Colors.deepPurple,
          ),
        ),
        const SizedBox(height: 12),
        // Macro: Turn X/Y (only meaningful during extraction stages)
        Row(
          children: [
            const Icon(Icons.autorenew, size: 16),
            const SizedBox(width: 6),
            Text(
              turnNumber != null
                  ? 'Tour $turnNumber ($currentTurn/$totalTurns)'
                  : 'Tour $currentTurn/$totalTurns',
              style: theme.textTheme.labelMedium
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withAlpha(30),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(stageLabel,
                  style: theme.textTheme.labelSmall
                      ?.copyWith(color: theme.colorScheme.primary)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // Macro progress bar
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: totalTurns > 0 ? currentTurn / totalTurns : null,
            minHeight: 8,
          ),
        ),
        const SizedBox(height: 12),
        // Micro: LLM calls
        Row(
          children: [
            Text('Calls LLM: $callsDone / $callsTotal',
                style: theme.textTheme.bodySmall),
            const Spacer(),
            if (callsTotal > 0)
              Text('${(callsDone / callsTotal * 100).toStringAsFixed(0)}%',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: callsTotal > 0 ? callsDone / callsTotal : null,
            minHeight: 6,
            color: Colors.amber,
          ),
        ),
        // ETA estimate based on elapsed time and calls done
        if (callsDone > 2 && _startTime != null) ...[
          const SizedBox(height: 8),
          _buildEta(callsDone, callsTotal, stepIdx, pipelineSteps.length, theme),
        ],
      ],
    );
  }

  /// Estimate remaining time from elapsed time and progress ratio.
  Widget _buildEta(int callsDone, int callsTotal,
      int stepIdx, int totalSteps, ThemeData theme) {
    final elapsed = DateTime.now().difference(_startTime!);
    if (elapsed.inSeconds < 5) return const SizedBox.shrink();

    // Combine LLM call progress with stage progress for a blended estimate.
    // LLM calls track the extraction phase well, stage index tracks post-turn phases.
    final callRatio = callsTotal > 0 ? callsDone / callsTotal : 0.0;
    final stageRatio = totalSteps > 0 ? (stepIdx + callRatio) / totalSteps : 0.0;
    // Use the more optimistic of the two (avoids stuck-looking estimates)
    final progress = stageRatio.clamp(0.01, 0.99);

    final estimatedTotal = elapsed.inSeconds / progress;
    final remaining = (estimatedTotal - elapsed.inSeconds).round();

    if (remaining <= 0) return const SizedBox.shrink();

    final etaStr = remaining >= 60
        ? '~${remaining ~/ 60}m ${remaining % 60}s restant'
        : '~${remaining}s restant';

    return Row(
      children: [
        Icon(Icons.timer_outlined, size: 14,
            color: theme.colorScheme.onSurface.withAlpha(120)),
        const SizedBox(width: 4),
        Text(etaStr,
            style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withAlpha(120),
                fontStyle: FontStyle.italic)),
        const Spacer(),
        Text('${elapsed.inSeconds}s ecoules',
            style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withAlpha(80))),
      ],
    );
  }
}
