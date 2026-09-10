// LabelSure — Scan Card Widget
// Used in the Scan History list.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
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
          gradient: LinearGradient(
            colors: [
              const Color(0xFF1E293B),
              const Color(0xFF0F172A),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: config.color.withOpacity(0.25),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Verdict indicator
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: config.color.withOpacity(0.15),
                  shape: BoxShape.circle,
                  border: Border.all(color: config.color.withOpacity(0.4)),
                ),
                child: Icon(config.icon, color: config.color, size: 26),
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
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _Chip(
                          label: verdict.replaceAll('_', ' '),
                          color: config.color,
                        ),
                        if (scan.needsManualReview) ...[
                          const SizedBox(width: 6),
                          _Chip(label: 'REVIEW', color: const Color(0xFFF59E0B)),
                        ],
                        if (scan.detectedLanguage != null && scan.detectedLanguage != 'en') ...[
                          const SizedBox(width: 6),
                          _Chip(
                            label: scan.detectedLanguage!.toUpperCase(),
                            color: const Color(0xFF60A5FA),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      DateFormat('dd MMM yyyy, hh:mm a').format(scan.createdAt.toLocal()),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.45),
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
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'OCR',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.4),
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              const SizedBox(width: 8),
              Icon(Icons.chevron_right, color: Colors.white24, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  _VerdictConfig _verdictConfig(String verdict) {
    switch (verdict) {
      case 'COMPLIANT':
        return _VerdictConfig(
          color: const Color(0xFF22C55E),
          icon: Icons.verified_rounded,
        );
      case 'NON_COMPLIANT':
        return _VerdictConfig(
          color: const Color(0xFFEF4444),
          icon: Icons.cancel_rounded,
        );
      default:
        return _VerdictConfig(
          color: const Color(0xFFF59E0B),
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
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.3)),
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
