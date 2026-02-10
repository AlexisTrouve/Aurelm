import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../core/theme/app_colors.dart';
import '../../../providers/entity_provider.dart';

class EntityBreakdownChart extends ConsumerWidget {
  final int civId;

  const EntityBreakdownChart({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final breakdown = ref.watch(entityTypeBreakdownProvider(civId));

    return breakdown.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(child: Text('Error loading chart')),
      data: (data) {
        if (data.isEmpty) {
          return const Center(child: Text('No entity data'));
        }

        final entries = data.entries.toList()
          ..sort((a, b) => b.value.compareTo(a.value));

        return BarChart(
          BarChartData(
            alignment: BarChartAlignment.spaceAround,
            maxY: (entries.first.value * 1.2).toDouble(),
            barGroups: entries.asMap().entries.map((e) {
              final color = AppColors.entityColor(e.value.key);
              return BarChartGroupData(
                x: e.key,
                barRods: [
                  BarChartRodData(
                    toY: e.value.value.toDouble(),
                    color: color,
                    width: 24,
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(4),
                    ),
                  ),
                ],
              );
            }).toList(),
            titlesData: FlTitlesData(
              leftTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: true, reservedSize: 32),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  getTitlesWidget: (value, _) {
                    final idx = value.toInt();
                    if (idx < 0 || idx >= entries.length) {
                      return const SizedBox.shrink();
                    }
                    return Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        entries[idx].key,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    );
                  },
                ),
              ),
              topTitles:
                  const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles:
                  const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            ),
            borderData: FlBorderData(show: false),
            gridData: const FlGridData(show: false),
          ),
        );
      },
    );
  }
}
