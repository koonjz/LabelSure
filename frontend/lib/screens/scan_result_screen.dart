// LabelSure — Scan Result Screen
// Shows COMPLIANT/NON_COMPLIANT badge + full rule checklist.
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../models/scan.dart';
import '../widgets/compliance_badge.dart';
import '../widgets/rule_checklist.dart';

class ScanResultScreen extends StatelessWidget {
  final Scan scan;

  const ScanResultScreen({super.key, required this.scan});

  @override
  Widget build(BuildContext context) {
    final verdict = scan.verdict ?? 'NEEDS_REVIEW';
    final Color verdictColor = verdict == 'COMPLIANT'
        ? const Color(0xFF22C55E)
        : verdict == 'NON_COMPLIANT'
            ? const Color(0xFFEF4444)
            : const Color(0xFFF59E0B);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1C),
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            backgroundColor: const Color(0xFF0A0F1C),
            expandedHeight: 300,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      verdictColor.withOpacity(0.15),
                      const Color(0xFF0A0F1C),
                    ],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 60),
                    ComplianceBadge(verdict: verdict),
                    const SizedBox(height: 16),
                    if (scan.needsManualReview)
                      Container(
                        margin: const EdgeInsets.symmetric(horizontal: 32),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF59E0B).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFF59E0B).withOpacity(0.3)),
                        ),
                        child: const Text(
                          '⚠ Manual review required',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Color(0xFFF59E0B), fontSize: 12),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            leading: IconButton(
              onPressed: () => context.go('/home'),
              icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                // Summary card
                _SummaryCard(scan: scan),
                const SizedBox(height: 20),

                // Review reason
                if (scan.reviewReason != null)
                  Container(
                    padding: const EdgeInsets.all(14),
                    margin: const EdgeInsets.only(bottom: 20),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF59E0B).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFF59E0B).withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.info_outline_rounded,
                            color: Color(0xFFF59E0B), size: 18),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            scan.reviewReason!,
                            style: const TextStyle(
                              color: Color(0xFFF59E0B),
                              fontSize: 12,
                              height: 1.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                // Rule checklist
                Text(
                  'Compliance Check (${scan.passCount} of ${scan.ruleResults.length} passed)',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                RuleChecklist(ruleResults: scan.ruleResults),

                const SizedBox(height: 20),

                // Extracted fields
                Text(
                  'Extracted Fields',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                _ExtractedFieldsCard(fields: scan.extractedFields),

                const SizedBox(height: 30),

                // New scan button
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF3B82F6), Color(0xFF8B5CF6)],
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: ElevatedButton.icon(
                      onPressed: () => context.go('/home'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14)),
                      ),
                      icon: const Icon(Icons.camera_alt_rounded,
                          color: Colors.white, size: 20),
                      label: const Text(
                        'Scan Another Label',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ).animate().fadeIn(delay: 400.ms),
                const SizedBox(height: 40),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final Scan scan;

  const _SummaryCard({required this.scan});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Column(
        children: [
          _InfoRow(
            label: 'Scan ID',
            value: scan.id.substring(0, 8).toUpperCase(),
            icon: Icons.qr_code_rounded,
          ),
          const Divider(color: Colors.white12, height: 20),
          _InfoRow(
            label: 'Date & Time',
            value: DateFormat('dd MMM yyyy, hh:mm a').format(scan.createdAt.toLocal()),
            icon: Icons.schedule_rounded,
          ),
          if (scan.overallConfidence != null) ...[
            const Divider(color: Colors.white12, height: 20),
            _InfoRow(
              label: 'OCR Confidence',
              value: '${(scan.overallConfidence! * 100).toStringAsFixed(1)}%',
              icon: Icons.analytics_rounded,
            ),
          ],
          if (scan.detectedLanguage != null) ...[
            const Divider(color: Colors.white12, height: 20),
            _InfoRow(
              label: 'Detected Language',
              value: _langLabel(scan.detectedLanguage!),
              icon: Icons.translate_rounded,
            ),
          ],
          const Divider(color: Colors.white12, height: 20),
          _InfoRow(
            label: 'Rules Passed',
            value: '${scan.passCount} / ${scan.ruleResults.length}',
            icon: Icons.check_circle_outline_rounded,
            valueColor: scan.passCount == scan.ruleResults.length
                ? const Color(0xFF22C55E)
                : const Color(0xFFEF4444),
          ),
        ],
      ),
    ).animate().fadeIn().slideY(begin: 0.05, end: 0);
  }

  String _langLabel(String code) {
    const map = {
      'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu',
      'kn': 'Kannada', 'bn': 'Bengali', 'ml': 'Malayalam',
      'gu': 'Gujarati', 'pa': 'Punjabi', 'mr': 'Marathi',
    };
    return map[code] ?? code.toUpperCase();
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color? valueColor;

  const _InfoRow({
    required this.label,
    required this.value,
    required this.icon,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: const Color(0xFF60A5FA), size: 18),
        const SizedBox(width: 10),
        Text(
          label,
          style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 13),
        ),
        const Spacer(),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _ExtractedFieldsCard extends StatelessWidget {
  final List<ExtractedField> fields;

  const _ExtractedFieldsCard({required this.fields});

  @override
  Widget build(BuildContext context) {
    final nonEmpty = fields.where((f) => f.fieldValue != null).toList();
    if (nonEmpty.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Center(
          child: Text(
            'No fields extracted',
            style: TextStyle(color: Colors.white.withOpacity(0.4)),
          ),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: nonEmpty.length,
        separatorBuilder: (_, __) =>
            const Divider(color: Colors.white12, height: 1),
        itemBuilder: (_, i) {
          final f = nonEmpty[i];
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 2,
                  child: Text(
                    f.displayName,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 12,
                    ),
                  ),
                ),
                Expanded(
                  flex: 3,
                  child: Text(
                    f.fieldValue ?? '—',
                    textAlign: TextAlign.end,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    ).animate().fadeIn(delay: 200.ms);
  }
}
