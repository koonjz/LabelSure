// LabelSure — Rule Checklist Widget
// Displays a list of rule results with ✓/✗ icons and explanations.
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/scan.dart';

class RuleChecklist extends StatelessWidget {
  final List<RuleResult> ruleResults;

  const RuleChecklist({super.key, required this.ruleResults});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: ruleResults
          .asMap()
          .entries
          .map((entry) => _RuleItem(
                result: entry.value,
                index: entry.key,
              ))
          .toList(),
    );
  }
}

class _RuleItem extends StatefulWidget {
  final RuleResult result;
  final int index;

  const _RuleItem({required this.result, required this.index});

  @override
  State<_RuleItem> createState() => _RuleItemState();
}

class _RuleItemState extends State<_RuleItem> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final passed = widget.result.passed;
    final isInfo = widget.result.severity == 'info';

    final Color statusColor = isInfo
        ? const Color(0xFF60A5FA)
        : passed
            ? const Color(0xFF22C55E)
            : const Color(0xFFEF4444);

    final IconData statusIcon = isInfo
        ? Icons.info_outline_rounded
        : passed
            ? Icons.check_circle_rounded
            : Icons.cancel_rounded;

    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: statusColor.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(statusIcon, color: statusColor, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.result.ruleName,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.9),
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          passed ? 'PASS' : (isInfo ? 'INFO' : 'FAIL'),
                          style: TextStyle(
                            color: statusColor,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    color: Colors.white38,
                    size: 20,
                  ),
                ],
              ),
            ),
            if (_expanded && widget.result.explanation != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                child: Text(
                  widget.result.explanation!,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 12,
                    height: 1.5,
                  ),
                ),
              ),
          ],
        ),
      ),
    )
        .animate(delay: Duration(milliseconds: 80 * widget.index))
        .fadeIn()
        .slideY(begin: 0.2, end: 0);
  }
}
