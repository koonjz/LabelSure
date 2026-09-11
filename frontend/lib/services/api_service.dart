// LabelSure — API Service
// All network calls go through this class; base URL comes from AppConfig only.
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show debugPrint;
import '../config/app_config.dart';
import '../models/scan.dart';
import '../models/user.dart';

/// Thrown when the backend cannot be reached or returns an unexpected error.
/// Always includes the URL that was tried so the user can diagnose config issues.
class ApiException implements Exception {
  final String message;
  final String? url;
  final int? statusCode;

  const ApiException(this.message, {this.url, this.statusCode});

  @override
  String toString() {
    final parts = <String>[message];
    if (url != null) parts.add('URL tried: $url');
    if (statusCode != null) parts.add('Status: $statusCode');
    return parts.join('\n');
  }
}

class ApiService {
  late final Dio _dio;

  /// The base URL in use — exposed so UI can show it in error messages.
  String get baseUrl => AppConfig.baseUrl;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.baseUrl,
      connectTimeout: AppConfig.connectTimeout,
      receiveTimeout: AppConfig.receiveTimeout,
      headers: {'Content-Type': 'application/json'},
    ));

    // Debug logging (strip in release if needed)
    assert(() {
      _dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: false, // avoid flooding logs with large payloads
        error: true,
        logPrint: (o) => debugPrint('[Dio] $o'),
      ));
      return true;
    }());
  }


  /// Set Bearer token on all subsequent requests.
  void setToken(String token) {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  /// Clear the auth token (logout).
  void clearToken() {
    _dio.options.headers.remove('Authorization');
  }

  // ─────────────────────────────────────────────
  // Error handling helper
  // ─────────────────────────────────────────────

  /// Converts Dio errors into [ApiException] with meaningful messages.
  ApiException _wrap(dynamic e, String endpoint) {
    final url = '${AppConfig.baseUrl}$endpoint';
    if (e is DioException) {
      switch (e.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
          return ApiException(
            'Connection timed out. Is the backend running?',
            url: url,
          );
        case DioExceptionType.connectionError:
          return ApiException(
            'Cannot reach the backend.\n'
            'Check that the backend is running with --host 0.0.0.0 '
            'and that the URL is correct.',
            url: url,
          );
        case DioExceptionType.badResponse:
          final code = e.response?.statusCode;
          final detail = _extractDetail(e.response);
          if (code == 401) return ApiException('Invalid email or password.', statusCode: 401, url: url);
          if (code == 403) return ApiException('Access denied.', statusCode: 403, url: url);
          if (code == 409) return ApiException('Email already registered.', statusCode: 409, url: url);
          if (code == 413) return ApiException('Image too large (max 20 MB).', statusCode: 413, url: url);
          return ApiException(detail ?? 'Server error (HTTP $code)', statusCode: code, url: url);
        default:
          return ApiException('Network error: ${e.message}', url: url);
      }
    }
    return ApiException(e.toString(), url: url);
  }

  String? _extractDetail(Response? response) {
    try {
      final data = response?.data;
      if (data is Map) return data['detail']?.toString();
    } catch (_) {}
    return null;
  }

  // ─────────────────────────────────────────────
  // Auth
  // ─────────────────────────────────────────────

  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await _dio.post('/auth/login', data: {
        'email': email,
        'password': password,
      });
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _wrap(e, '/auth/login');
    }
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? fullName,
    String role = 'consumer',
    String? region,
  }) async {
    try {
      final response = await _dio.post('/auth/register', data: {
        'email': email,
        'password': password,
        'full_name': fullName,
        'role': role,
        if (region != null) 'region': region,
      });
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _wrap(e, '/auth/register');
    }
  }

  Future<User> getMe() async {
    try {
      final response = await _dio.get('/auth/me');
      return User.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e, '/auth/me');
    }
  }

  // ─────────────────────────────────────────────
  // Scans
  // ─────────────────────────────────────────────

  /// Upload label image and run full compliance pipeline.
  Future<Scan> uploadScan({
    required File imageFile,
    double? salePrice,
    String fontType = 'printed',
    double? referenceWidthMm,
    double? referenceWidthPx,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          imageFile.path,
          filename: imageFile.path.split('/').last,
        ),
        if (salePrice != null) 'sale_price': salePrice.toString(),
        'font_type': fontType,
        if (referenceWidthMm != null) 'reference_width_mm': referenceWidthMm.toString(),
        if (referenceWidthPx != null) 'reference_width_px': referenceWidthPx.toString(),
      });

      final response = await _dio.post(
        '/scans/upload',
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );
      return Scan.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e, '/scans/upload');
    }
  }

  /// List scans (officers: all; consumers: own).
  Future<Map<String, dynamic>> listScans({
    String? verdict,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final response = await _dio.get('/scans', queryParameters: {
        if (verdict != null) 'verdict': verdict,
        'page': page,
        'page_size': pageSize,
      });
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _wrap(e, '/scans');
    }
  }

  /// Get full scan details.
  Future<Scan> getScan(String scanId) async {
    try {
      final response = await _dio.get('/scans/$scanId');
      return Scan.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e, '/scans/$scanId');
    }
  }

  // ─────────────────────────────────────────────
  // Reports
  // ─────────────────────────────────────────────

  /// Get the export URL for officers (CSV download).
  String exportReportUrl({String? verdict, String format = 'csv'}) {
    final params = <String, String>{'fmt': format};
    if (verdict != null) params['verdict'] = verdict;
    final query = params.entries.map((e) => '${e.key}=${e.value}').join('&');
    return '${AppConfig.baseUrl}/reports/export?$query';
  }
}
