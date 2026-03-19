import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:path/path.dart' as p;

import '../../data/database.dart';
import '../../providers/database_provider.dart';
import 'package:drift/drift.dart' show Value;
import 'package:flutter_riverpod/flutter_riverpod.dart';

// ---------------------------------------------------------------------------
// Asset import dialog
// ---------------------------------------------------------------------------

/// Shows a dialog to import an image as a map asset.
/// Lets the user pick a file, set a name and a max dimension,
/// then compresses to WebP and stores in map_assets.
Future<MapAssetRow?> showAssetImportDialog(
  BuildContext context,
  WidgetRef ref,
) async {
  return showDialog<MapAssetRow?>(
    context: context,
    builder: (ctx) => _AssetImportDialog(ref: ref),
  );
}

class _AssetImportDialog extends StatefulWidget {
  final WidgetRef ref;
  const _AssetImportDialog({required this.ref});

  @override
  State<_AssetImportDialog> createState() => _AssetImportDialogState();
}

class _AssetImportDialogState extends State<_AssetImportDialog> {
  String? _filePath;
  String _name = '';
  int _maxDim = 128;
  bool _loading = false;
  String? _error;

  // Preview thumbnail decoded from picked file
  Uint8List? _previewBytes;
  int? _origW;
  int? _origH;

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return;
    final path = result.files.single.path;
    if (path == null) return;

    // Decode just to get dimensions for the preview
    final bytes = await File(path).readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      setState(() => _error = 'Format non reconnu');
      return;
    }

    setState(() {
      _filePath = path;
      _name = p.basenameWithoutExtension(path);
      _origW = decoded.width;
      _origH = decoded.height;
      _previewBytes = Uint8List.fromList(img.encodePng(
        img.copyResize(decoded, width: 96, height: 96),
      ));
      _error = null;
    });
  }

  Future<void> _import() async {
    if (_filePath == null) return;
    final db = widget.ref.read(databaseProvider);
    if (db == null) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final result = await _compressToWebP(
        filePath: _filePath!,
        maxDim: _maxDim,
      );

      final ext = p.extension(_filePath!).replaceFirst('.', '').toLowerCase();
      final now = DateTime.now().toIso8601String();

      final id = await db.mapDao.insertAsset(MapAssetsCompanion(
        name: Value(_name.trim().isEmpty
            ? p.basenameWithoutExtension(_filePath!)
            : _name.trim()),
        data: Value(result.bytes),
        originalFormat: Value(ext),
        storedWidth: Value(result.width),
        storedHeight: Value(result.height),
        createdAt: Value(now),
      ));

      // Fetch and return the inserted row
      final row = await (db.select(db.mapAssets)
            ..where((a) => a.id.equals(id)))
          .getSingleOrNull();

      if (mounted) Navigator.of(context).pop(row);
    } catch (e) {
      setState(() {
        _error = 'Erreur : $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final bigAsset = _maxDim > 512;

    return AlertDialog(
      title: const Text('Importer un asset'),
      content: SizedBox(
        width: 360,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // File picker
            Row(
              children: [
                Expanded(
                  child: Text(
                    _filePath == null
                        ? 'Aucun fichier sélectionné'
                        : p.basename(_filePath!),
                    style: TextStyle(
                      color: _filePath == null ? Colors.grey : null,
                      fontSize: 13,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: _loading ? null : _pickFile,
                  child: const Text('Choisir'),
                ),
              ],
            ),

            // Preview + original dims
            if (_previewBytes != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Image.memory(_previewBytes!,
                      width: 48, height: 48, fit: BoxFit.contain),
                  const SizedBox(width: 12),
                  Text('${_origW}×${_origH}px original',
                      style: const TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ],

            const SizedBox(height: 12),

            // Name
            TextField(
              decoration: const InputDecoration(
                labelText: 'Nom',
                border: OutlineInputBorder(),
              ),
              controller: TextEditingController(text: _name),
              onChanged: (v) => _name = v,
            ),
            const SizedBox(height: 12),

            // Max dimension
            Row(
              children: [
                const Text('Taille max (px) : '),
                const SizedBox(width: 8),
                SizedBox(
                  width: 80,
                  child: TextField(
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    keyboardType: TextInputType.number,
                    controller:
                        TextEditingController(text: _maxDim.toString()),
                    onChanged: (v) =>
                        setState(() => _maxDim = int.tryParse(v) ?? _maxDim),
                  ),
                ),
                if (bigAsset) ...[
                  const SizedBox(width: 8),
                  const Icon(Icons.warning_amber_rounded,
                      color: Colors.orange, size: 16),
                  const SizedBox(width: 4),
                  const Text('Lourd en DB',
                      style: TextStyle(color: Colors.orange, fontSize: 11)),
                ],
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'L\'image sera redimensionnée à ${_maxDim}×${_maxDim}px max et encodée en PNG.',
              style:
                  const TextStyle(fontSize: 11, color: Colors.grey),
            ),

            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(null),
          child: const Text('Annuler'),
        ),
        FilledButton(
          onPressed: _loading || _filePath == null ? null : _import,
          child: _loading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Importer'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Compression helper — pure Dart via `image` package
// ---------------------------------------------------------------------------

class _CompressResult {
  final Uint8List bytes;
  final int width;
  final int height;
  const _CompressResult(
      {required this.bytes, required this.width, required this.height});
}

Future<_CompressResult> _compressToWebP({
  required String filePath,
  required int maxDim,
}) async {
  final rawBytes = await File(filePath).readAsBytes();
  final decoded = img.decodeImage(rawBytes);
  if (decoded == null) throw Exception('Format image non reconnu');

  // Resize keeping aspect ratio
  final img.Image resized;
  if (decoded.width > maxDim || decoded.height > maxDim) {
    if (decoded.width >= decoded.height) {
      resized = img.copyResize(decoded, width: maxDim,
          interpolation: img.Interpolation.average);
    } else {
      resized = img.copyResize(decoded, height: maxDim,
          interpolation: img.Interpolation.average);
    }
  } else {
    resized = decoded;
  }

  // Encode PNG — transparent-friendly, well-compressed for icon sizes
  final pngBytes = Uint8List.fromList(img.encodePng(resized));

  return _CompressResult(
    bytes: pngBytes,
    width: resized.width,
    height: resized.height,
  );
}
