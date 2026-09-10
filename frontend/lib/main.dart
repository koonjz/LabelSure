// LabelSure — Flutter App Entry Point
// Role-based routing: Officer → ScanHistory home; Consumer/Seller → Scan home.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'models/scan.dart';
import 'screens/login_screen.dart';
import 'screens/scan_screen.dart';
import 'screens/scan_result_screen.dart';
import 'screens/scan_history_screen.dart';
import 'screens/scan_detail_screen.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Enforce portrait mode
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));

  final apiService = ApiService();
  final authService = AuthService(apiService);
  await authService.tryAutoLogin();

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>.value(value: apiService),
        ChangeNotifierProvider<AuthService>.value(value: authService),
      ],
      child: const LabelSureApp(),
    ),
  );
}

class LabelSureApp extends StatelessWidget {
  const LabelSureApp({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();

    final router = GoRouter(
      initialLocation: auth.isLoggedIn ? '/home' : '/login',
      redirect: (context, state) {
        final loggedIn = auth.isLoggedIn;
        final goingToLogin = state.matchedLocation == '/login';
        if (!loggedIn && !goingToLogin) return '/login';
        if (loggedIn && goingToLogin) return '/home';
        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (_, __) => const LoginScreen(),
        ),
        // Main home — role-based
        GoRoute(
          path: '/home',
          builder: (_, __) {
            final isOfficer = auth.isOfficer;
            return _HomeShell(isOfficer: isOfficer);
          },
          routes: [
            GoRoute(
              path: 'scan-result',
              builder: (_, state) {
                final scan = state.extra as Scan;
                return ScanResultScreen(scan: scan);
              },
            ),
          ],
        ),
        GoRoute(
          path: '/scan-result',
          builder: (_, state) {
            final scan = state.extra as Scan;
            return ScanResultScreen(scan: scan);
          },
        ),
        GoRoute(
          path: '/scan-detail/:id',
          builder: (_, state) {
            final id = state.pathParameters['id']!;
            return ScanDetailScreen(scanId: id);
          },
        ),
      ],
    );

    return MaterialApp.router(
      title: 'LabelSure',
      debugShowCheckedModeBanner: false,
      theme: _buildTheme(),
      routerConfig: router,
    );
  }

  ThemeData _buildTheme() {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: const Color(0xFF0A0F1C),
      colorScheme: const ColorScheme.dark(
        primary: Color(0xFF3B82F6),
        secondary: Color(0xFF8B5CF6),
        surface: Color(0xFF1E293B),
        error: Color(0xFFEF4444),
      ),
      fontFamily: 'Roboto',
      useMaterial3: true,
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF0A0F1C),
        elevation: 0,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Color(0xFF0F172A),
        selectedItemColor: Color(0xFF3B82F6),
        unselectedItemColor: Colors.white38,
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Shell with bottom nav bar (role-based tabs)
// ─────────────────────────────────────────────────────────────────────────────
class _HomeShell extends StatefulWidget {
  final bool isOfficer;
  const _HomeShell({required this.isOfficer});

  @override
  State<_HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<_HomeShell> {
  int _selectedIndex = 0;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = widget.isOfficer
        ? [const ScanScreen(), const ScanHistoryScreen(), const _ProfilePage()]
        : [const ScanScreen(), const ScanHistoryScreen(), const _ProfilePage()];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _selectedIndex, children: _pages),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A),
          border: Border(top: BorderSide(color: Colors.white.withOpacity(0.08))),
        ),
        child: BottomNavigationBar(
          currentIndex: _selectedIndex,
          onTap: (i) => setState(() => _selectedIndex = i),
          backgroundColor: Colors.transparent,
          elevation: 0,
          items: [
            const BottomNavigationBarItem(
              icon: Icon(Icons.camera_alt_rounded),
              label: 'Scan',
            ),
            BottomNavigationBarItem(
              icon: const Icon(Icons.history_rounded),
              label: widget.isOfficer ? 'Dashboard' : 'History',
            ),
            const BottomNavigationBarItem(
              icon: Icon(Icons.person_rounded),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Simple Profile Page
// ─────────────────────────────────────────────────────────────────────────────
class _ProfilePage extends StatelessWidget {
  const _ProfilePage();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final user = auth.user;

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1C),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 40),
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF3B82F6), Color(0xFF8B5CF6)],
                  ),
                  shape: BoxShape.circle,
                ),
                child: Center(
                  child: Text(
                    (user?.displayName ?? 'U').substring(0, 1).toUpperCase(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                user?.displayName ?? 'User',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                user?.email ?? '',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFF3B82F6).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFF3B82F6).withOpacity(0.3)),
                ),
                child: Text(
                  user?.roleLabel ?? 'Consumer',
                  style: const TextStyle(color: Color(0xFF3B82F6), fontSize: 12),
                ),
              ),
              if (user?.region != null) ...[
                const SizedBox(height: 6),
                Text(
                  '📍 ${user!.region}',
                  style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 13),
                ),
              ],
              const SizedBox(height: 48),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.logout_rounded, size: 18),
                  label: const Text('Sign Out'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFFEF4444),
                    side: const BorderSide(color: Color(0xFFEF4444)),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: () async {
                    await auth.logout();
                    if (context.mounted) context.go('/login');
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
