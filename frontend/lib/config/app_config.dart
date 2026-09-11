// LabelSure — App Configuration
//
// The backend base URL is injected at build/run time via --dart-define.
// If not provided, defaults to the Android emulator gateway (10.0.2.2)
// which routes to the host machine's localhost:8000.
//
// How to run:
//   Android Emulator (default, no flag needed):
//     flutter run
//   Physical Android Device on same LAN (replace with YOUR machine's IP):
//     flutter run --dart-define=API_BASE_URL=http://192.168.1.42:8000
//   Deployed backend:
//     flutter run --dart-define=API_BASE_URL=https://api.labelsure.example.com
//   Android Studio run config: Edit Configurations → Additional run args → add the --dart-define flag

class AppConfig {
  AppConfig._(); // prevent instantiation

  /// Backend API base URL.
  ///
  /// Default: http://10.0.2.2:8000 — correct for Android Emulator talking to
  /// the host machine.  For a physical device on LAN, override at build time:
  ///   --dart-define=API_BASE_URL=http://<your-machine-LAN-IP>:8000
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  /// Convenience: base URL with no trailing slash.
  static String get baseUrl => apiBaseUrl.endsWith('/')
      ? apiBaseUrl.substring(0, apiBaseUrl.length - 1)
      : apiBaseUrl;

  // Connection timeouts
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 60);
}
