// LabelSure — App Entry Point
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'config/app_router.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final apiService = ApiService();
  final authService = AuthService(apiService);

  // Restore saved session from secure storage before launching UI
  await authService.tryAutoLogin();

  runApp(LabelSureApp(
    apiService: apiService,
    authService: authService,
  ));
}

class LabelSureApp extends StatefulWidget {
  final ApiService apiService;
  final AuthService authService;

  const LabelSureApp({
    super.key,
    required this.apiService,
    required this.authService,
  });

  @override
  State<LabelSureApp> createState() => _LabelSureAppState();
}

class _LabelSureAppState extends State<LabelSureApp> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = buildRouter(widget.authService);
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: widget.authService),
        Provider<ApiService>.value(value: widget.apiService),
      ],
      child: MaterialApp.router(
        title: 'LabelSure',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF3B82F6),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
          fontFamily: 'Inter',
        ),
        routerConfig: _router,
      ),
    );
  }
}

