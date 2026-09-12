import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../config/app_theme.dart';
import '../models/scan.dart';

class ScanCard extends StatelessWidget {
  final ScanListItem scan;
  final VoidCallback onTap;

  const ScanCard({super.key, required this.scan, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final verdict = scan.verdict ?? 'UNKNOWN';
    final config = _verdictConfig(verdict);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: config.color.withValues(alpha: 0.3),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Verdict indicator
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: config.color.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                  border: Border.all(color: config.color.withValues(alpha: 0.4)),
                ),
                child: Icon(config.icon, color: config.color, size: 24),
              ),
              const SizedBox(width: 14),
              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      scan.imageFilename ?? 'Label Scan',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        _Chip(
                          label: verdict.replaceAll('_', ' '),
                          color: config.color,
                        ),
                        if (scan.needsManualReview) ...[
                          const SizedBox(width: 6),
                          const _Chip(label: 'REVIEW', color: AppColors.statusReviewLight),
                        ],
                        if (scan.detectedLanguage != null && scan.detectedLanguage != 'en') ...[
                          const SizedBox(width: 6),
                          _Chip(
                            label: scan.detectedLanguage!.toUpperCase(),
                            color: AppColors.brandTealLight,
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      DateFormat('dd MMM yyyy, hh:mm a').format(scan.createdAt.toLocal()),
                      style: const TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              // Confidence
              if (scan.overallConfidence != null)
                Column(
                  children: [
                    Text(
                      '${(scan.overallConfidence! * 100).toStringAsFixed(0)}%',
                      style: TextStyle(
                        color: config.color,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Text(
                      'OCR',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  _VerdictConfig _verdictConfig(String verdict) {
    switch (verdict) {
      case 'COMPLIANT':
        return const _VerdictConfig(
          color: AppColors.statusCompliant,          // #2E7D32 Safe Green
          icon: Icons.verified_rounded,
        );
      case 'NON_COMPLIANT':
        return const _VerdictConfig(
          color: AppColors.statusNonCompliant,       // #C62828 Red
          icon: Icons.cancel_rounded,
        );
      default:
        return const _VerdictConfig(
          color: AppColors.statusReview,             // #D97706 Amber
          icon: Icons.help_outline_rounded,
        );
    }
  }
}

class _VerdictConfig {
  final Color color;
  final IconData icon;
  const _VerdictConfig({required this.color, required this.icon});
}

class _Chip extends StatelessWidget {
  final String label;
  final Color color;
  const _Chip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 9,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
