// LabelSure — Auth Service (ChangeNotifier)
// Manages login state, JWT token persistence, and user profile.
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user.dart';
import 'api_service.dart'; // also imports ApiException

class AuthService extends ChangeNotifier {
  static const _tokenKey = 'labelsure_jwt';

  final ApiService _api;
  final FlutterSecureStorage _storage;

  User? _user;
  bool _isLoading = false;
  String? _error;

  AuthService(this._api) : _storage = const FlutterSecureStorage();

  User? get user => _user;
  bool get isLoggedIn => _user != null;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isOfficer => _user?.isOfficer ?? false;

  /// Restore session from secure storage on app start.
  Future<void> tryAutoLogin() async {
    _isLoading = true;
    notifyListeners();
    try {
      final token = await _storage.read(key: _tokenKey);
      if (token != null) {
        _api.setToken(token);
        _user = await _api.getMe();
      }
    } catch (_) {
      await _storage.delete(key: _tokenKey);
      _api.clearToken();
      _user = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final data = await _api.login(email, password);
      final token = data['access_token'] as String;
      _user = User.fromJson(data['user'] as Map<String, dynamic>);
      _api.setToken(token);
      await _storage.write(key: _tokenKey, value: token);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = _parseError(e);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> register({
    required String email,
    required String password,
    String? fullName,
    String role = 'consumer',
    String? region,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      await _api.register(
        email: email,
        password: password,
        fullName: fullName,
        role: role,
        region: region,
      );
      // Auto-login after registration
      return await login(email, password);
    } catch (e) {
      _error = _parseError(e);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    _user = null;
    _api.clearToken();
    await _storage.delete(key: _tokenKey);
    notifyListeners();
  }

  String _parseError(dynamic e) {
    // ApiException already contains the URL tried and a human-readable message.
    if (e is ApiException) return e.toString();
    final msg = e.toString();
    if (msg.contains('401')) return 'Invalid email or password.';
    if (msg.contains('409')) return 'Email already registered.';
    return msg;
  }
}
