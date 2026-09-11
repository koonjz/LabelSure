// LabelSure — App Entry Point
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'config/app_router.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';

void main() {
  runApp(const LabelSureApp());
}

class LabelSureApp extends StatelessWidget {
  const LabelSureApp({super.key});

  @override
  Widget build(BuildContext context) {
    final apiService = ApiService();
    final authService = AuthService(apiService);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: authService),
        Provider<ApiService>.value(value: apiService),
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
        routerConfig: buildRouter(authService),
      ),
    );
  }
}
