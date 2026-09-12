import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../config/app_theme.dart';

class ComplianceBadge extends StatelessWidget {
  final String verdict; // 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW'
  final bool large;

  const ComplianceBadge({
    super.key,
    required this.verdict,
    this.large = true,
  });

  @override
  Widget build(BuildContext context) {
    final config = _badgeConfig(verdict);
    final double size = large ? 180 : 80;
    final double fontSize = large ? 18 : 10;
    final double iconSize = large ? 60 : 26;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [config.lightColor, config.color],
          center: const Alignment(-0.3, -0.3),
        ),
        boxShadow: [
          BoxShadow(
            color: config.color.withValues(alpha: 0.4),
            blurRadius: large ? 30 : 12,
            spreadRadius: large ? 6 : 2,
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(config.icon, color: Colors.white, size: iconSize),
          const SizedBox(height: 8),
          Text(
            config.label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    )
        .animate()
        .scale(
          begin: const Offset(0.6, 0.6),
          duration: 600.ms,
          curve: Curves.elasticOut,
        )
        .fade(duration: 300.ms);
  }

  _BadgeConfig _badgeConfig(String verdict) {
    switch (verdict) {
      case 'COMPLIANT':
        return const _BadgeConfig(
          color: AppColors.statusCompliant,          // #2E7D32 Safe Green
          lightColor: AppColors.statusCompliantLight,
          icon: Icons.verified_rounded,
          label: 'COMPLIANT',
        );
      case 'NON_COMPLIANT':
        return const _BadgeConfig(
          color: AppColors.statusNonCompliant,       // #C62828 Red
          lightColor: AppColors.statusNonCompliantLight,
          icon: Icons.cancel_rounded,
          label: 'NON\nCOMPLIANT',
        );
      default:
        return const _BadgeConfig(
          color: AppColors.statusReview,             // #D97706 Amber
          lightColor: AppColors.statusReviewLight,
          icon: Icons.help_outline_rounded,
          label: 'NEEDS\nREVIEW',
        );
    }
  }
}

class _BadgeConfig {
  final Color color;
  final Color lightColor;
  final IconData icon;
  final String label;
  const _BadgeConfig({
    required this.color,
    required this.lightColor,
    required this.icon,
    required this.label,
  });
}

