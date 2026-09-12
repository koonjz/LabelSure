import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../config/app_theme.dart';
import '../models/scan.dart';
import '../widgets/compliance_badge.dart';
import '../widgets/profile_button.dart';
import '../widgets/rule_checklist.dart';

class ScanResultScreen extends StatelessWidget {
  final Scan scan;

  const ScanResultScreen({super.key, required this.scan});

  @override
  Widget build(BuildContext context) {
    final verdict = scan.verdict ?? 'NEEDS_REVIEW';
    final Color verdictColor = verdict == 'COMPLIANT'
        ? AppColors.statusCompliant        // #2E7D32 Safe Green
        : verdict == 'NON_COMPLIANT'
            ? AppColors.statusNonCompliant // #C62828 Red
            : AppColors.statusReview;      // #D97706 Amber

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            backgroundColor: AppColors.background,
            expandedHeight: 300,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      verdictColor.withValues(alpha: 0.18),
                      AppColors.background,
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
                          color: AppColors.statusReviewBg,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppColors.statusReviewBorder),
                        ),
                        child: const Text(
                          '⚠ Manual review required by officer',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppColors.statusReviewLight,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
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
            actions: const [
              Padding(
                padding: EdgeInsets.only(right: 16),
                child: ProfileButton(),
              ),
            ],
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
                      color: AppColors.statusReviewBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.statusReviewBorder),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.info_outline_rounded,
                            color: AppColors.statusReviewLight, size: 18),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            scan.reviewReason!,
                            style: const TextStyle(
                              color: AppColors.statusReviewLight,
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
                const Text(
                  'Extracted Fields',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                _ExtractedFieldsCard(fields: scan.extractedFields),

                const SizedBox(height: 20),

                // Raw OCR text (collapsible debug section)
                if (scan.rawOcrText != null && scan.rawOcrText!.trim().isNotEmpty)
                  _RawOcrCard(rawText: scan.rawOcrText!),

                const SizedBox(height: 30),

                // New scan button
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: AppColors.brandGradientHorizontal,
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.brandBlue.withValues(alpha: 0.35),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
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
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderSubtle),
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
          if (scan.ocrEngine != null) ...[
            const Divider(color: Colors.white12, height: 20),
            _InfoRow(
              label: 'OCR Engine',
              value: _engineLabel(scan.ocrEngine!),
              icon: Icons.memory_rounded,
            ),
          ],
          const Divider(color: Colors.white12, height: 20),
          _InfoRow(
            label: 'Rules Passed',
            value: '${scan.passCount} / ${scan.ruleResults.length}',
            icon: Icons.check_circle_outline_rounded,
            valueColor: scan.passCount == scan.ruleResults.length
                ? AppColors.statusCompliant
                : AppColors.statusNonCompliant,
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

  String _engineLabel(String engine) {
    switch (engine.toLowerCase()) {
      case 'paddleocr': return 'PaddleOCR ✦';
      case 'tesseract': return 'Tesseract';
      case 'paddleocr+tesseract': return 'PaddleOCR + Tesseract';
      case 'mlkit': return 'Google ML Kit (On-Device)';
      default: return engine;
    }
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
        Icon(icon, color: AppColors.brandTealLight, size: 18),
        const SizedBox(width: 10),
        Text(
          label,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
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
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.borderSubtle),
        ),
        child: const Center(
          child: Text(
            'No fields extracted',
            style: TextStyle(color: AppColors.textMuted),
          ),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderSubtle),
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
                    style: const TextStyle(
                      color: AppColors.textSecondary,
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

// ─── Raw OCR Text Card ────────────────────────────────────────────────────────
class _RawOcrCard extends StatefulWidget {
  final String rawText;
  const _RawOcrCard({required this.rawText});

  @override
  State<_RawOcrCard> createState() => _RawOcrCardState();
}

class _RawOcrCardState extends State<_RawOcrCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceSubtle,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.brandTeal.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  const Icon(Icons.document_scanner_rounded,
                      color: AppColors.brandTealLight, size: 18),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'Raw OCR Text',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Text(
                    _expanded ? 'Hide' : 'Show',
                    style: const TextStyle(
                        color: AppColors.brandTealLight, fontSize: 12),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: AppColors.brandTealLight,
                    size: 20,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            const Divider(color: Colors.white10, height: 1),
            Padding(
              padding: const EdgeInsets.all(14),
              child: SelectableText(
                widget.rawText,
                style: const TextStyle(
                  color: Color(0xFFCBD5E1),
                  fontSize: 11,
                  fontFamily: 'monospace',
                  height: 1.6,
                ),
              ),
            ),
          ],
        ],
      ),
    ).animate().fadeIn(delay: 300.ms);
  }
}
