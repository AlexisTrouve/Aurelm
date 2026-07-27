part of '../chat_screen.dart';

// ---------------------------------------------------------------------------
// Message segment parser — splits user messages into text and file parts
// ---------------------------------------------------------------------------

/// Represents a segment of a user message: plain text, attached file, or a quote.
sealed class _MessageSegment {}

class _TextSegment extends _MessageSegment {
  final String text;
  _TextSegment(this.text);
}

class _FileSegment extends _MessageSegment {
  final String filename;
  final String content;
  _FileSegment(this.filename, this.content);
}

/// A quoted message — rendered as a collapsed card inside the user bubble.
class _QuoteSegment extends _MessageSegment {
  final String role;    // 'Vous' or 'Aurelm'
  final String content; // quote text with > stripped
  _QuoteSegment(this.role, this.content);
}

/// Parse a message string into segments: quote (optional, at start), then
/// alternating text/file blocks.
List<_MessageSegment> _parseMessageSegments(String message) {
  final segments = <_MessageSegment>[];

  // Detect optional quote block at the very start.
  // Format produced by _buildMessage(): [Role a écrit :]\n> line1\n> line2...
  final quoteRe = RegExp(r'^\[([^\]]+) a écrit :\]\n((?:> [^\n]*(?:\n|$))*)');
  final qMatch = quoteRe.firstMatch(message);
  if (qMatch != null) {
    final role = qMatch.group(1)!;
    final rawLines = qMatch.group(2) ?? '';
    // Strip the "> " prefix from each line
    final content = rawLines
        .split('\n')
        .where((l) => l.startsWith('> '))
        .map((l) => l.length > 2 ? l.substring(2) : '')
        .join('\n')
        .trim();
    segments.add(_QuoteSegment(role, content));
    // Continue parsing the remainder (text + files)
    message = message.substring(qMatch.end).trimLeft();
  }

  // Parse file blocks and text from the remaining string.
  final pattern = RegExp(r'\[Fichier: ([^\]]+)\]\n');
  int cursor = 0;

  for (final match in pattern.allMatches(message)) {
    // Text before this file marker
    if (match.start > cursor) {
      final text = message.substring(cursor, match.start).trim();
      if (text.isNotEmpty) segments.add(_TextSegment(text));
    }

    final filename = match.group(1)!;
    // File content runs from end of marker to next marker or end of string
    final contentStart = match.end;
    final nextMatch = pattern.firstMatch(message.substring(contentStart));
    final contentEnd = nextMatch != null
        ? contentStart + nextMatch.start
        : message.length;
    final content = message.substring(contentStart, contentEnd).trimRight();
    segments.add(_FileSegment(filename, content));
    cursor = contentEnd;
  }

  // Trailing text after last file
  if (cursor < message.length) {
    final text = message.substring(cursor).trim();
    if (text.isNotEmpty) segments.add(_TextSegment(text));
  }

  return segments;
}

/// Pick an icon based on file extension.
IconData _fileIcon(String filename) {
  final ext = filename.contains('.') ? filename.split('.').last.toLowerCase() : '';
  return switch (ext) {
    'py' || 'dart' => Icons.code,
    'ts' || 'js' => Icons.javascript,
    'json' => Icons.data_object,
    'sql' => Icons.storage,
    'md' => Icons.description,
    'csv' => Icons.table_chart,
    'txt' => Icons.text_snippet,
    _ => Icons.insert_drive_file,
  };
}

/// Build user message content with file cards when attachments are present.
Widget _buildUserContent(String content, ColorScheme colorScheme) {
  final segments = _parseMessageSegments(content);

  // Fast path: single text segment = plain message, no overhead
  if (segments.length == 1 && segments.first is _TextSegment) {
    return Text(
      (segments.first as _TextSegment).text,
      style: TextStyle(color: colorScheme.onPrimary),
    );
  }

  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: segments.map((seg) {
      if (seg is _TextSegment) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(
            seg.text,
            style: TextStyle(color: colorScheme.onPrimary),
          ),
        );
      }
      if (seg is _QuoteSegment) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: _QuoteCard(role: seg.role, content: seg.content),
        );
      }
      final file = seg as _FileSegment;
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: _FileCard(filename: file.filename, content: file.content),
      );
    }).toList(),
  );
}

// ---------------------------------------------------------------------------
// File card — collapsible, shown inside user bubbles for attached files
// ---------------------------------------------------------------------------

class _FileCard extends StatefulWidget {
  final String filename;
  final String content;

  const _FileCard({required this.filename, required this.content});

  @override
  State<_FileCard> createState() => _FileCardState();
}

class _FileCardState extends State<_FileCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    // Human-readable size label
    final chars = widget.content.length;
    final sizeLabel = chars >= 1024
        ? '${(chars / 1024).toStringAsFixed(1)} KB'
        : '$chars chars';

    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: colorScheme.secondary.withValues(alpha: 0.5),
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => setState(() => _expanded = !_expanded),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(_fileIcon(widget.filename),
                      size: 14, color: colorScheme.secondary),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      widget.filename,
                      style: textTheme.labelSmall?.copyWith(
                        color: colorScheme.onSurface,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    sizeLabel,
                    style: textTheme.labelSmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    size: 14,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
              if (_expanded) ...[
                const Divider(height: 10, thickness: 0.5),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 300),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      widget.content,
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                        fontFamily: 'monospace',
                        fontSize: 11,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Quote card — collapsed by default, shown inside user bubble for quoted msgs
// ---------------------------------------------------------------------------

class _QuoteCard extends StatefulWidget {
  final String role;    // 'Vous' or 'Aurelm'
  final String content; // quote body with > stripped

  const _QuoteCard({required this.role, required this.content});

  @override
  State<_QuoteCard> createState() => _QuoteCardState();
}

class _QuoteCardState extends State<_QuoteCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    // Colors adapted for dark primary background (user bubble)
    final onPrimary = Theme.of(context).colorScheme.onPrimary;
    final preview = widget.content.replaceAll('\n', ' ');

    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: onPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border(
            left: BorderSide(color: onPrimary.withValues(alpha: 0.45), width: 2),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Text(
                  widget.role,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: onPrimary.withValues(alpha: 0.85),
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const Spacer(),
                Icon(
                  _expanded ? Icons.expand_less : Icons.expand_more,
                  size: 11,
                  color: onPrimary.withValues(alpha: 0.5),
                ),
              ],
            ),
            const SizedBox(height: 2),
            Text(
              _expanded ? widget.content : preview,
              maxLines: _expanded ? null : 1,
              overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: onPrimary.withValues(alpha: 0.7),
                    fontStyle: FontStyle.italic,
                    fontSize: 11,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
