// LabelSure — Auth Service (ChangeNotifier)
// Manages login state, JWT token persistence, and user profile.
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user.dart';
import 'api_service.dart'; // also imports ApiException

class AuthService extends ChangeNotifier {
  static const _tokenKey = 'labelsure_jwt';
  static const _userKey = 'labelsure_user_profile';

  static const _androidOptions = AndroidOptions(
    encryptedSharedPreferences: true,
  );
  static const _iosOptions = IOSOptions(
    accessibility: KeychainAccessibility.first_unlock,
  );

  final ApiService _api;
  final FlutterSecureStorage _storage;

  User? _user;
  bool _isLoading = false;
  String? _error;

  AuthService(this._api)
      : _storage = const FlutterSecureStorage(
          aOptions: _androidOptions,
          iOptions: _iosOptions,
        );

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
      if (token != null && token.isNotEmpty) {
        _api.setToken(token);

        // 1. Restore cached user profile immediately if available
        final userJson = await _storage.read(key: _userKey);
        if (userJson != null && userJson.isNotEmpty) {
          try {
            final map = jsonDecode(userJson) as Map<String, dynamic>;
            _user = User.fromJson(map);
          } catch (_) {}
        }

        // 2. Validate/refresh user profile from server
        try {
          final freshUser = await _api.getMe();
          _user = freshUser;
          await _storage.write(
            key: _userKey,
            value: jsonEncode(freshUser.toJson()),
          );
        } on ApiException catch (e) {
          // If token is invalid or expired (401), clean up session
          if (e.statusCode == 401) {
            await _storage.delete(key: _tokenKey);
            await _storage.delete(key: _userKey);
            _api.clearToken();
            _user = null;
          }
          // For network / timeout / cold start errors, keep existing session!
        } catch (_) {
          // Network or parsing error: keep token and cached user
        }
      }
    } catch (_) {
      // Storage read failure
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
      final user = User.fromJson(data['user'] as Map<String, dynamic>);
      _user = user;
      _api.setToken(token);
      await _storage.write(key: _tokenKey, value: token);
      await _storage.write(key: _userKey, value: jsonEncode(user.toJson()));
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
    await _storage.delete(key: _userKey);
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

