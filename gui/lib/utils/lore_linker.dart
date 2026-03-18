// Lore auto-linking — injects Markdown hyperlinks for entities, civs, subjects,
// and turns found in LLM response text. Links use custom URI schemes so the
// chat bubble's onTapLink handler can open floating preview windows.

/// Types of lore objects that can be linked.
enum LoreLinkType { entity, civ, subject, turn }

/// A single linkable lore object — name, DB id, and route for navigation.
class LoreLink {
  final int id;
  final LoreLinkType type;
  /// GoRouter path for full-page navigation (e.g. '/entities/42').
  final String route;

  const LoreLink({required this.id, required this.type, required this.route});
}

/// Build a fuzzy regex from [query]: spaces and hyphens are interchangeable,
/// optional plural 's' on the last word, case-insensitive.
/// "Sans ciel" matches "sans-ciels", "Sans-Ciel", etc.
RegExp fuzzyRegex(String query) {
  final words = query
      .trim()
      .split(RegExp(r'[\s\-]+'))
      .where((w) => w.isNotEmpty)
      .toList();
  if (words.isEmpty) return RegExp(RegExp.escape(query), caseSensitive: false);
  final inner = [
    for (int i = 0; i < words.length; i++)
      i == words.length - 1
          ? '${RegExp.escape(words[i])}s?'
          : RegExp.escape(words[i]),
  ].join(r'[\s\-]+');
  // Unicode-aware word boundaries — \b is ASCII-only in Dart, so we use
  // lookbehind/lookahead that match start/end or any non-letter/non-accent char.
  // This prevents "civilisation" from matching inside "civilisationnelle".
  const lb = r'(?<=\s|^|[^\w\u00C0-\u024F])';
  const la = r'(?=\s|$|[^\w\u00C0-\u024F])';
  final pattern = '$lb$inner$la';
  return RegExp(pattern, caseSensitive: false, unicode: true);
}

/// Inject Markdown-style links into [text] for every name in [linkMap].
///
/// [linkMap] keys are lore names (entity names, civ names, etc.),
/// values are [LoreLink] objects. The map MUST be sorted by key length
/// descending (longest first) to avoid partial matches.
///
/// Skips names < 4 chars to avoid noise. Skips text already inside a
/// Markdown link `[...](...)`.
///
/// Links use the format `[matched text](lore://type/id)` so callers can
/// distinguish lore links from regular URLs.
String injectLoreLinks(String text, Map<String, LoreLink> linkMap) {
  if (linkMap.isEmpty) return text;

  String result = text;

  for (final entry in linkMap.entries) {
    final name = entry.key;
    // Skip very short names to avoid noise — but always allow:
    // - turn refs like "T1", "T5"
    // - subject refs like "#1", "#18" (hash-prefixed ids)
    if (name.length < 4 &&
        entry.value.type != LoreLinkType.turn &&
        !name.startsWith('#')) {
      continue;
    }

    final link = entry.value;
    final regex = fuzzyRegex(name);

    result = result.replaceAllMapped(regex, (match) {
      final start = match.start;

      // Don't replace inside existing Markdown links — check for preceding '['
      if (start > 0 && result[start - 1] == '[') return match.group(0)!;
      // Don't replace inside a link target (...) — check for preceding '('
      if (start > 0 && result[start - 1] == '(') return match.group(0)!;
      // Don't replace if we're inside a link text or URL (scan backwards for
      // unmatched '[' or '(' that indicates we're within a markdown link)
      if (_isInsideMarkdownLink(result, start)) return match.group(0)!;

      final scheme = link.type.name; // entity, civ, subject, turn
      return '[${match.group(0)}](lore://$scheme/${link.id})';
    });
  }

  // Clean up nested links: [text with [inner](lore://...)](lore://...)
  // Flatten inner links to plain text, keeping only the outermost link.
  result = _flattenNestedLinks(result);

  return result;
}

/// Check if position [pos] falls inside an existing Markdown link's text or URL.
/// Scans backwards for unmatched '[' or '(' characters.
bool _isInsideMarkdownLink(String text, int pos) {
  int bracketDepth = 0;
  int parenDepth = 0;
  for (int i = pos - 1; i >= 0; i--) {
    final ch = text[i];
    if (ch == ']') {
      bracketDepth++;
    } else if (ch == '[') {
      if (bracketDepth > 0) {
        bracketDepth--;
      } else {
        // Unmatched '[' — we're inside a link text
        return true;
      }
    } else if (ch == ')') {
      parenDepth++;
    } else if (ch == '(') {
      if (parenDepth > 0) {
        parenDepth--;
      } else if (i > 0 && text[i - 1] == ']') {
        // Unmatched '(' preceded by ']' → this is a Markdown link URL opener
        return true;
      }
      // Bare '(' in normal text — not a link, ignore it
    }
  }
  return false;
}

/// Remove nested Markdown links, keeping only the outermost link.
/// e.g. `[Dresseurs de [regards-libres](lore://entity/31)](lore://entity/34)`
/// becomes `[Dresseurs de regards-libres](lore://entity/34)`
String _flattenNestedLinks(String text) {
  // Regex won't cleanly handle arbitrary nesting — use a character-level scan.
  // Strategy: find markdown links `[...](...)`, check if the text part contains
  // inner links, and strip their markdown syntax (keep display text only).
  final buf = StringBuffer();
  int i = 0;

  while (i < text.length) {
    if (text[i] == '[') {
      // Try to parse a complete markdown link starting here
      final linkEnd = _findMarkdownLinkEnd(text, i);
      if (linkEnd != null) {
        // Extract the text and URL parts
        final closeBracket = _findMatchingBracket(text, i);
        if (closeBracket != null &&
            closeBracket + 1 < text.length &&
            text[closeBracket + 1] == '(') {
          final closeParenIdx = _findMatchingParen(text, closeBracket + 1);
          if (closeParenIdx != null) {
            final linkText = text.substring(i + 1, closeBracket);
            final linkUrl = text.substring(closeBracket + 2, closeParenIdx);
            // Strip any inner markdown links from the text part
            final cleanText = _stripMarkdownLinks(linkText);
            buf.write('[$cleanText]($linkUrl)');
            i = closeParenIdx + 1;
            continue;
          }
        }
      }
    }
    buf.write(text[i]);
    i++;
  }
  return buf.toString();
}

/// Find the closing ']' that matches the '[' at [start], respecting nesting.
int? _findMatchingBracket(String text, int start) {
  assert(text[start] == '[');
  int depth = 1;
  for (int i = start + 1; i < text.length; i++) {
    if (text[i] == '[') depth++;
    if (text[i] == ']') {
      depth--;
      if (depth == 0) return i;
    }
  }
  return null;
}

/// Find the closing ')' that matches the '(' at [start], respecting nesting.
int? _findMatchingParen(String text, int start) {
  assert(text[start] == '(');
  int depth = 1;
  for (int i = start + 1; i < text.length; i++) {
    if (text[i] == '(') depth++;
    if (text[i] == ')') {
      depth--;
      if (depth == 0) return i;
    }
  }
  return null;
}

/// Find the end of a markdown link `[...](...)` starting at [start].
/// Returns the index AFTER the closing ')' or null if not a valid link.
int? _findMarkdownLinkEnd(String text, int start) {
  final closeBracket = _findMatchingBracket(text, start);
  if (closeBracket == null) return null;
  if (closeBracket + 1 >= text.length || text[closeBracket + 1] != '(') {
    return null;
  }
  final closeParen = _findMatchingParen(text, closeBracket + 1);
  if (closeParen == null) return null;
  return closeParen + 1;
}

/// Strip markdown link syntax from [text], keeping only display text.
/// `[foo](url)` becomes `foo`. Handles nested links recursively.
String _stripMarkdownLinks(String text) {
  final buf = StringBuffer();
  int i = 0;
  while (i < text.length) {
    if (text[i] == '[') {
      final closeBracket = _findMatchingBracket(text, i);
      if (closeBracket != null &&
          closeBracket + 1 < text.length &&
          text[closeBracket + 1] == '(') {
        final closeParen = _findMatchingParen(text, closeBracket + 1);
        if (closeParen != null) {
          // Recursively strip the inner text part
          final innerText = text.substring(i + 1, closeBracket);
          buf.write(_stripMarkdownLinks(innerText));
          i = closeParen + 1;
          continue;
        }
      }
    }
    buf.write(text[i]);
    i++;
  }
  return buf.toString();
}
