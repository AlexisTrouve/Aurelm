import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/database_provider.dart';
import '../../../providers/map_provider.dart';
import '../asset_importer.dart';

/// Left panel — asset library.
/// Each asset is a [Draggable<int>] (asset id) that can be dropped on canvas cells.
class AssetPanel extends ConsumerWidget {
  const AssetPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final assetsAsync = ref.watch(allAssetsProvider);
    final db = ref.read(databaseProvider);

    return Column(
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              const Text('Assets',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.add, size: 18),
                tooltip: 'Importer un asset',
                onPressed: () => showAssetImportDialog(context, ref),
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: assetsAsync.when(
            data: (assets) {
              if (assets.isEmpty) {
                return const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Aucun asset.\nClique + pour importer.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                  ),
                );
              }
              return ListView.builder(
                padding: const EdgeInsets.all(8),
                itemCount: assets.length,
                itemBuilder: (_, i) =>
                    _AssetTile(asset: assets[i], db: db),
              );
            },
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('$e')),
          ),
        ),
      ],
    );
  }
}

class _AssetTile extends StatelessWidget {
  final MapAssetRow asset;
  final AurelmDatabase? db;

  const _AssetTile({required this.asset, required this.db});

  @override
  Widget build(BuildContext context) {
    final thumb = Image.memory(
      asset.data,
      width: 40,
      height: 40,
      fit: BoxFit.contain,
      gaplessPlayback: true,
    );

    return Draggable<int>(
      data: asset.id,
      // Shown under the finger while dragging
      feedback: Material(
        elevation: 4,
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Image.memory(asset.data,
              width: 48, height: 48, fit: BoxFit.contain,
              gaplessPlayback: true),
        ),
      ),
      // Fades the tile during drag
      childWhenDragging: Opacity(opacity: 0.4, child: _tile(context, thumb)),
      child: _tile(context, thumb),
    );
  }

  Widget _tile(BuildContext context, Widget thumb) {
    return ListTile(
      dense: true,
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      leading: ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: thumb,
      ),
      title: Text(asset.name,
          style: const TextStyle(fontSize: 12),
          overflow: TextOverflow.ellipsis),
      subtitle: Text(
        '${asset.storedWidth}×${asset.storedHeight}px',
        style: const TextStyle(fontSize: 10),
      ),
      trailing: IconButton(
        icon: const Icon(Icons.delete_outline, size: 16),
        color: Colors.grey,
        tooltip: 'Supprimer l\'asset',
        onPressed: () => _confirmDelete(context),
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Supprimer "${asset.name}" ?'),
        content: const Text(
            'L\'asset sera retiré de toutes les cellules où il est placé.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Annuler')),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (ok == true) await db?.mapDao.deleteAsset(asset.id);
  }
}
