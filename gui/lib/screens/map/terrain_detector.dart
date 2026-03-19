import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

/// Result of terrain auto-detection for one cell.
class CellTerrainProposal {
  final int q;
  final int r;
  final String terrain;

  /// Average HSV used for classification (for debug/tooltip).
  final double hue;
  final double sat;
  final double val;

  const CellTerrainProposal({
    required this.q,
    required this.r,
    required this.terrain,
    required this.hue,
    required this.sat,
    required this.val,
  });
}

/// Decodes [imagePath], samples each cell, and returns terrain proposals.
///
/// [gridType]  'hex' or 'square'
/// [gridCols]  number of columns
/// [gridRows]  number of rows
/// [cellSize]  hex outer radius or square side in canvas units —
///             only the grid *shape* matters; actual pixel radius is derived
///             from the image-to-canvas ratio.
Future<List<CellTerrainProposal>> detectTerrainFromImage({
  required String imagePath,
  required String gridType,
  required int gridCols,
  required int gridRows,
  required double cellSize,
}) async {
  // --- 1. Decode image to RGBA bytes ---
  final bytes = await File(imagePath).readAsBytes();
  final codec = await ui.instantiateImageCodec(bytes);
  final frame = await codec.getNextFrame();
  final image = frame.image;
  final byteData =
      await image.toByteData(format: ui.ImageByteFormat.rawRgba);
  if (byteData == null) return [];

  final imgW = image.width;
  final imgH = image.height;
  final pixels = byteData.buffer.asUint8List();

  // --- 2. Compute canvas dimensions (same logic as GridPainter) ---
  final double canvasW;
  final double canvasH;
  if (gridType == 'hex') {
    canvasW = cellSize * sqrt(3) * (gridCols + 0.5);
    canvasH = cellSize * 1.5 * gridRows + cellSize * 0.5;
  } else {
    canvasW = cellSize * gridCols;
    canvasH = cellSize * gridRows;
  }

  // Scale factors: canvas unit → image pixel
  final scaleX = imgW / canvasW;
  final scaleY = imgH / canvasH;

  final proposals = <CellTerrainProposal>[];

  for (int r = 0; r < gridRows; r++) {
    for (int q = 0; q < gridCols; q++) {
      // --- 3. Cell center in canvas units ---
      final double cx;
      final double cy;
      if (gridType == 'hex') {
        cx = cellSize * sqrt(3) * (q + r * 0.5);
        cy = cellSize * 1.5 * r;
      } else {
        cx = q * cellSize + cellSize / 2;
        cy = r * cellSize + cellSize / 2;
      }

      // Center in image pixels
      final cxPx = cx * scaleX;
      final cyPx = cy * scaleY;

      // Sample radius: 45% of cell size in image pixels
      final radiusPx = cellSize * 0.45 * ((scaleX + scaleY) / 2);

      // --- 4. Sample pixels within the circle ---
      final avg = _sampleCircle(
          pixels, imgW, imgH, cxPx, cyPx, radiusPx);

      // --- 5. Classify ---
      final hsv = _rgbToHsv(avg.r, avg.g, avg.b);
      final terrain = _classify(hsv.h, hsv.s, hsv.v);

      proposals.add(CellTerrainProposal(
        q: q,
        r: r,
        terrain: terrain,
        hue: hsv.h,
        sat: hsv.s,
        val: hsv.v,
      ));
    }
  }

  return proposals;
}

// ---------------------------------------------------------------------------
// Pixel sampling
// ---------------------------------------------------------------------------

/// Returns the average RGB of all pixels within [radius] of (cx, cy).
({double r, double g, double b}) _sampleCircle(
  Uint8List pixels,
  int imgW,
  int imgH,
  double cx,
  double cy,
  double radius,
) {
  double sumR = 0, sumG = 0, sumB = 0;
  int count = 0;

  final x0 = max(0, (cx - radius).floor());
  final x1 = min(imgW - 1, (cx + radius).ceil());
  final y0 = max(0, (cy - radius).floor());
  final y1 = min(imgH - 1, (cy + radius).ceil());

  final r2 = radius * radius;

  for (int py = y0; py <= y1; py++) {
    for (int px = x0; px <= x1; px++) {
      final dx = px - cx;
      final dy = py - cy;
      if (dx * dx + dy * dy > r2) continue;

      final idx = (py * imgW + px) * 4;
      sumR += pixels[idx];
      sumG += pixels[idx + 1];
      sumB += pixels[idx + 2];
      count++;
    }
  }

  if (count == 0) return (r: 128.0, g: 128.0, b: 128.0);
  return (r: sumR / count, g: sumG / count, b: sumB / count);
}

// ---------------------------------------------------------------------------
// RGB → HSV
// ---------------------------------------------------------------------------

({double h, double s, double v}) _rgbToHsv(double r, double g, double b) {
  final rf = r / 255.0;
  final gf = g / 255.0;
  final bf = b / 255.0;

  final cMax = max(rf, max(gf, bf));
  final cMin = min(rf, min(gf, bf));
  final delta = cMax - cMin;

  double h = 0;
  if (delta > 0) {
    if (cMax == rf) {
      h = 60 * (((gf - bf) / delta) % 6);
    } else if (cMax == gf) {
      h = 60 * (((bf - rf) / delta) + 2);
    } else {
      h = 60 * (((rf - gf) / delta) + 4);
    }
  }
  if (h < 0) h += 360;

  final s = cMax == 0 ? 0.0 : delta / cMax;
  final v = cMax;

  return (h: h, s: s, v: v);
}

// ---------------------------------------------------------------------------
// HSV → terrain (priority order — first match wins)
// ---------------------------------------------------------------------------

String _classify(double h, double s, double v) {
  // Glacier: near-white
  if (v > 0.88 && s < 0.12) return 'glacier';

  // Sea: deep blue
  if (h >= 200 && h <= 240 && s > 0.40) return 'sea';

  // Coast: light cyan-blue
  if (h >= 175 && h <= 215 && s >= 0.15 && s <= 0.50) return 'coast';

  // Tundra: muted cyan
  if (h >= 165 && h <= 200 && s < 0.35) return 'tundra';

  // Forest: dark green
  if (h >= 90 && h <= 155 && s > 0.35 && v < 0.55) return 'forest';

  // Swamp: murky green (low sat, dark)
  if (h >= 58 && h <= 95 && s < 0.35 && v < 0.45) return 'swamp';

  // Plain: light green / meadow
  if (h >= 70 && h <= 125 && s >= 0.15 && s <= 0.65 && v > 0.45) {
    return 'plain';
  }

  // Desert: yellow / ochre
  if (h >= 35 && h <= 70 && s > 0.35 && v > 0.50) return 'desert';

  // Hills: warm brown-green
  if (h >= 22 && h <= 52 && s >= 0.18 && s <= 0.58 &&
      v >= 0.28 && v <= 0.68) {
    return 'hills';
  }

  // Mountain: grey-brown
  if ((h >= 0 && h <= 35) && s < 0.25 && v >= 0.20 && v <= 0.70) {
    return 'mountain';
  }

  // Ruins: fallback
  return 'ruins';
}
