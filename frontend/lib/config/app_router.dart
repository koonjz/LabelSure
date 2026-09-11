// LabelSure — App Router (go_router)
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../models/scan.dart';
import '../screens/login_screen.dart';
import '../screens/scan_detail_screen.dart';
import '../screens/scan_history_screen.dart';
import '../screens/scan_result_screen.dart';
import '../screens/scan_screen.dart';
import '../services/auth_service.dart';

/// Shell that hosts the bottom navigation bar.
class _HomeShell extends StatefulWidget {
  final Widget child;
  const _HomeShell({required this.child});

  @override
  State<_HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<_HomeShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1C),
      body: widget.child,
      bottomNavigationBar: BottomNavigationBar(
        backgroundColor: const Color(0xFF0F172A),
        selectedItemColor: const Color(0xFF3B82F6),
        unselectedItemColor: Colors.white38,
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() => _currentIndex = index);
          switch (index) {
            case 0:
              context.go('/home');
            case 1:
              context.go('/history');
          }
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.document_scanner_rounded),
            label: 'Scan',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history_rounded),
            label: 'History',
          ),
        ],
      ),
    );
  }
}

GoRouter buildRouter(AuthService authService) {
  return GoRouter(
    initialLocation: '/home',
    redirect: (context, state) {
      final loggedIn = authService.isLoggedIn;
      final onLogin = state.uri.path == '/login';
      if (!loggedIn && !onLogin) return '/login';
      if (loggedIn && onLogin) return '/home';
      return null;
    },
    refreshListenable: authService,
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      ShellRoute(
        builder: (context, state, child) => _HomeShell(child: child),
        routes: [
          GoRoute(
            path: '/home',
            builder: (context, state) => const ScanScreen(),
          ),
          GoRoute(
            path: '/history',
            builder: (context, state) => const ScanHistoryScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/scan-result',
        builder: (context, state) {
          final scan = state.extra as Scan;
          return ScanResultScreen(scan: scan);
        },
      ),
      GoRoute(
        path: '/scan-detail/:id',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return ScanDetailScreen(scanId: id);
        },
      ),
    ],
  );
}
