import 'package:flutter_test/flutter_test.dart';
import 'package:labelsure/main.dart';
import 'package:labelsure/services/api_service.dart';
import 'package:labelsure/services/auth_service.dart';

void main() {
  testWidgets('LabelSureApp smoke test', (WidgetTester tester) async {
    final apiService = ApiService();
    final authService = AuthService(apiService);

    await tester.pumpWidget(LabelSureApp(
      apiService: apiService,
      authService: authService,
    ));

    expect(find.byType(LabelSureApp), findsOneWidget);
  });
}

