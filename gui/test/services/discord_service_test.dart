// Regression test for the blanket `catch (_)` bug in DiscordService.verify():
// ANY exception (timeout, socket error, JSON parse error, ...) was reported as
// DiscordFailure.network, so a real server-side hiccup (a malformed body on
// step 2/3, a non-socket I/O error) surfaced to Arthur as "impossible de
// joindre Discord" — a network diagnosis for a non-network failure. That sent
// him chasing his internet connection instead of the real cause.
//
// verify() already handles the 401 case explicitly (line ~109) before this
// catch-all is ever reached, so this suite targets the catch-all itself:
// only a genuine network primitive (TimeoutException, SocketException) should
// map to DiscordFailure.network; anything else must map to
// DiscordFailure.server.
import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:aurelm_gui/services/discord_service.dart';

void main() {
  group('DiscordService — failure classification', () {
    test('classifyException: TimeoutException -> network', () {
      expect(
        DiscordService.classifyException(TimeoutException('timed out')),
        DiscordFailure.network,
      );
    });

    test('classifyException: SocketException -> network', () {
      expect(
        DiscordService.classifyException(
            const SocketException('Connection refused')),
        DiscordFailure.network,
      );
    });

    test('classifyException: FormatException (bad JSON body) -> server', () {
      // A malformed response body is Discord answering unexpectedly, not a
      // reachability problem — must NOT be reported as "network".
      expect(
        DiscordService.classifyException(const FormatException('bad json')),
        DiscordFailure.server,
      );
    });

    test('classifyException: arbitrary Exception -> server', () {
      expect(
        DiscordService.classifyException(Exception('boom')),
        DiscordFailure.server,
      );
    });
  });
}
