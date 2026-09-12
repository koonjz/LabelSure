// LabelSure — Design System & Color Palette
//
// Strict Semantic Role Enforcement:
//   • Brand: #1565C0 Deep Blue + #00897B Teal
//   • Status (RESERVED purely for compliance results):
//       - #2E7D32 Safe Green  → Compliant / Passed
//       - #D97706 Amber       → Needs Review / Warning
//       - #C62828 Red         → Non-Compliant / Violation

import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // ── Brand Colors ───────────────────────────────────────────────────────────
  static const Color brandBlue = Color(0xFF1565C0);       // Deep Blue
  static const Color brandBlueDark = Color(0xFF0D47A1);
  static const Color brandBlueLight = Color(0xFF1E88E5);

  static const Color brandTeal = Color(0xFF00897B);       // Teal
  static const Color brandTealDark = Color(0xFF00695C);
  static const Color brandTealLight = Color(0xFF26A69A);

  static const LinearGradient brandGradient = LinearGradient(
    colors: [brandBlue, brandTeal],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient brandGradientHorizontal = LinearGradient(
    colors: [brandBlue, brandTeal],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  // ── Status Colors (RESERVED for scan verdicts / compliance results) ────────
  static const Color statusCompliant = Color(0xFF2E7D32);      // Safe Green
  static const Color statusCompliantLight = Color(0xFF4CAF50);
  static Color get statusCompliantBg => const Color(0xFF2E7D32).withValues(alpha: 0.12);
  static Color get statusCompliantBorder => const Color(0xFF2E7D32).withValues(alpha: 0.35);

  static const Color statusReview = Color(0xFFD97706);         // Amber
  static const Color statusReviewLight = Color(0xFFF59E0B);
  static Color get statusReviewBg => const Color(0xFFD97706).withValues(alpha: 0.12);
  static Color get statusReviewBorder => const Color(0xFFD97706).withValues(alpha: 0.35);

  static const Color statusNonCompliant = Color(0xFFC62828);   // Red
  static const Color statusNonCompliantLight = Color(0xFFEF5350);
  static Color get statusNonCompliantBg => const Color(0xFFC62828).withValues(alpha: 0.12);
  static Color get statusNonCompliantBorder => const Color(0xFFC62828).withValues(alpha: 0.35);

  // ── Neutrals / Surfaces ───────────────────────────────────────────────────
  static const Color background = Color(0xFF0A0F1D);          // Premium deep slate
  static const Color surface = Color(0xFF121B2F);             // Elevated card background
  static const Color surfaceElevated = Color(0xFF18243E);     // High elevation card
  static const Color surfaceSubtle = Color(0xFF0E1626);       // Inset / secondary card

  static Color get borderSubtle => Colors.white.withValues(alpha: 0.08);
  static Color get borderHighlight => brandTeal.withValues(alpha: 0.3);

  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);
}

class AppTheme {
  AppTheme._();

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.background,
      fontFamily: 'Inter',
      colorScheme: const ColorScheme.dark(
        primary: AppColors.brandBlue,
        secondary: AppColors.brandTeal,
        surface: AppColors.surface,
        error: AppColors.statusNonCompliant,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: AppColors.textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.bold,
          letterSpacing: -0.3,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: AppColors.borderSubtle),
        ),
      ),
    );
  }
}
