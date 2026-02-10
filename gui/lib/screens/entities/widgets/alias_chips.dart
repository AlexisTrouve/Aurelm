import 'package:flutter/material.dart';

class AliasChips extends StatelessWidget {
  final List<String> aliases;

  const AliasChips({super.key, required this.aliases});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 4,
      children: aliases.map((alias) {
        return Chip(
          label: Text(alias),
          visualDensity: VisualDensity.compact,
        );
      }).toList(),
    );
  }
}
