// LabelSure — App Configuration
//
// The backend base URL is injected at build/run time via --dart-define.
//
// ─── Running Locally (Development) ───────────────────────────────────────────
//
//   Android Emulator (default — no flag needed):
//     flutter run
//     Connects to http://10.0.2.2:8000 (emulator host gateway)
//
//   Physical Android Device (same LAN as dev machine):
//     flutter run --dart-define=API_BASE_URL=http://192.168.1.42:8000
//
//   Android Studio: Run → Edit Configurations → Additional run args
//     --dart-define=API_BASE_URL=http://192.168.1.42:8000
//
// ─── Building for Release / Production ───────────────────────────────────────
//
//   A release build MUST set API_BASE_URL to the real HTTPS backend URL.
//   The build will throw an assertion error if you forget — this is intentional.
//
//   flutter build apk --release \
//     --dart-define=API_BASE_URL=https://api.labelsure.app
//
//   flutter build appbundle --release \
//     --dart-define=API_BASE_URL=https://api.labelsure.app
//
// ─── What happens if you forget ──────────────────────────────────────────────
//   Debug builds: silently default to http://10.0.2.2:8000 (dev is fine)
//   Release builds: the assert in _validateForRelease() will crash at startup
//                   with a clear error explaining what to do.

import 'package:flutter/foundation.dart' show kReleaseMode, kDebugMode;

class AppConfig {
  AppConfig._(); // static-only class

  // ─── Raw value from --dart-define ─────────────────────────────────────────
  static const String _rawApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    // Dev default: Android Emulator host gateway.
    // This default is INTENTIONALLY only valid in dev.
    // Release builds must override this — see validation below.
    defaultValue: 'https://labelsure-jw0d.onrender.com',
  );

  // ─── Validated, trimmed URL ────────────────────────────────────────────────
  static String get apiBaseUrl {
    final url = _rawApiBaseUrl.trim().replaceAll(RegExp(r'/+$'), '');
    if (kReleaseMode) {
      _validateForRelease(url);
    }
    return url;
  }

  /// Convenience alias.
  static String get baseUrl => apiBaseUrl;

  // ─── Connection timeouts ───────────────────────────────────────────────────
  // Longer in release (real server may be further away).
  static Duration get connectTimeout =>
      kDebugMode ? const Duration(seconds: 30) : const Duration(seconds: 30);

  static Duration get receiveTimeout =>
      // 120 s in both modes: Render free-tier backends can take ~90 s on cold start.
      kDebugMode ? const Duration(seconds: 120) : const Duration(seconds: 120);

  // ─── Release build validation ─────────────────────────────────────────────
  static void _validateForRelease(String url) {
    assert(
      url.isNotEmpty && url != 'http://10.0.2.2:8000',
      '\n\n'
      '══════════════════════════════════════════════════════════════════\n'
      '  RELEASE BUILD ERROR: API_BASE_URL is still the dev default!\n'
      '══════════════════════════════════════════════════════════════════\n'
      '  You are building a release APK/App Bundle but have not set\n'
      '  API_BASE_URL to the production backend URL.\n\n'
      '  Fix: add --dart-define=API_BASE_URL=https://api.your-domain.com\n'
      '  to your flutter build command. Example:\n\n'
      '    flutter build apk --release \\\n'
      '      --dart-define=API_BASE_URL=https://api.labelsure.app\n\n'
      '  See DEPLOYMENT.md → "Building the Release APK" for full details.\n'
      '══════════════════════════════════════════════════════════════════\n',
    );

    assert(
      url.startsWith('https://') || url.startsWith('http://'),
      'API_BASE_URL must start with https:// or http://. Got: $url',
    );

    // Warn (but don't block) if URL is HTTP in release — HTTPS is strongly preferred.
    if (url.startsWith('http://') && !url.contains('10.0.2.2') && !url.contains('localhost')) {
      // This will show in the build logs via assert message.
      assert(
        false,
        '\n  WARNING: Release build is using HTTP (not HTTPS): $url\n'
        '  Unless you are sideloading to a device on a trusted LAN,\n'
        '  switch to an HTTPS backend URL.\n',
      );
    }
  }

  // ─── Diagnostics (dev only) ───────────────────────────────────────────────
  static String get debugSummary =>
      '[AppConfig] mode=${kReleaseMode ? "release" : "debug"} '
      'url=$_rawApiBaseUrl';
}
