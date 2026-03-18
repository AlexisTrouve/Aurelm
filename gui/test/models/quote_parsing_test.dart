/// Tests de parsing des messages quotés.
///
/// _parseMessageSegments est privé (dans chat_screen.dart) — on ne peut pas
/// l'appeler directement. Ce fichier valide la logique de construction du
/// message côté _buildMessage() : le format produit doit être reconnu.
///
/// On teste le format attendu avec des regex simples.
library;

import 'package:flutter_test/flutter_test.dart';

void main() {
  // Le format produit par _buildMessage() pour un message quoté.
  // [Role a écrit :]\n> line1\n> line2\nTexte de l'utilisateur
  group('Quote format (préparation côté _buildMessage)', () {
    String buildQuotedMessage(String role, String quotedContent, String userText) {
      final quoted = quotedContent.split('\n').map((l) => '> $l').join('\n');
      final parts = <String>['[$role a écrit :]\n$quoted'];
      if (userText.isNotEmpty) parts.add(userText);
      return parts.join('\n\n');
    }

    test('format simple - une ligne', () {
      final msg = buildQuotedMessage('Aurelm', 'Réponse de l\'agent.', 'Ma question');
      expect(msg, startsWith('[Aurelm a écrit :]\n> Réponse de l\'agent.'));
      expect(msg, contains('Ma question'));
    });

    test('format multi-ligne', () {
      final msg = buildQuotedMessage(
        'Vous',
        'Ligne 1\nLigne 2\nLigne 3',
        'Suite',
      );
      expect(msg, contains('> Ligne 1'));
      expect(msg, contains('> Ligne 2'));
      expect(msg, contains('> Ligne 3'));
    });

    test('regex de détection du bloc quote', () {
      final msg = buildQuotedMessage('Aurelm', 'Texte cité.', 'Question de suivi');
      // Le regex utilisé dans _parseMessageSegments
      final quoteRe = RegExp(r'^\[([^\]]+) a écrit :\]\n((?:> [^\n]*(?:\n|$))*)');
      final match = quoteRe.firstMatch(msg);

      expect(match, isNotNull);
      expect(match!.group(1), 'Aurelm');
      // Le contenu brut avec les "> "
      final rawLines = match.group(2) ?? '';
      expect(rawLines, contains('> Texte cité.'));

      // Après strip des "> " : doit contenir le texte propre
      final content = rawLines
          .split('\n')
          .where((l) => l.startsWith('> '))
          .map((l) => l.length > 2 ? l.substring(2) : '')
          .join('\n')
          .trim();
      expect(content, 'Texte cité.');
      // Pas de "> " dans le résultat parsé
      expect(content, isNot(contains('> ')));
    });

    test('regex - quote uniquement (sans texte après)', () {
      final msg = buildQuotedMessage('Vous', 'Message original.', '');
      final quoteRe = RegExp(r'^\[([^\]]+) a écrit :\]\n((?:> [^\n]*(?:\n|$))*)');
      final match = quoteRe.firstMatch(msg);
      expect(match, isNotNull);
      // Reste après le match = vide (pas de texte utilisateur)
      final remainder = msg.substring(match!.end).trimLeft();
      expect(remainder, isEmpty);
    });

    test('regex - texte sans quote = pas de match', () {
      const msg = 'Simple question sans quote.';
      final quoteRe = RegExp(r'^\[([^\]]+) a écrit :\]\n((?:> [^\n]*(?:\n|$))*)');
      expect(quoteRe.firstMatch(msg), isNull);
    });

    test('regex - message avec fichier sans quote = pas de match', () {
      const msg = '[Fichier: test.py]\ncontenu du fichier';
      final quoteRe = RegExp(r'^\[([^\]]+) a écrit :\]\n((?:> [^\n]*(?:\n|$))*)');
      expect(quoteRe.firstMatch(msg), isNull);
    });
  });
}
