// LabelSure — API Service
// Calls the FastAPI backend for all data operations.
import 'dart:io';
import 'package:dio/dio.dart';
import '../models/scan.dart';
import '../models/user.dart';

class ApiService {
  static const String _baseUrl = 'http://10.0.2.2:8000'; // Android emulator → host
  // For physical device, change to your machine's local IP, e.g. 'http://192.168.1.100:8000'

  late final Dio _dio;

  ApiService({String? baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl ?? _baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json'},
    ));

    // Logging interceptor (debug only)
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      error: true,
    ));
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
  // Auth
  // ─────────────────────────────────────────────

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
    });
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? fullName,
    String role = 'consumer',
    String? region,
  }) async {
    final response = await _dio.post('/auth/register', data: {
      'email': email,
      'password': password,
      'full_name': fullName,
      'role': role,
      if (region != null) 'region': region,
    });
    return response.data as Map<String, dynamic>;
  }

  Future<User> getMe() async {
    final response = await _dio.get('/auth/me');
    return User.fromJson(response.data as Map<String, dynamic>);
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
  }

  /// List scans (officers: all; consumers: own).
  Future<Map<String, dynamic>> listScans({
    String? verdict,
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await _dio.get('/scans', queryParameters: {
      if (verdict != null) 'verdict': verdict,
      'page': page,
      'page_size': pageSize,
    });
    return response.data as Map<String, dynamic>;
  }

  /// Get full scan details.
  Future<Scan> getScan(String scanId) async {
    final response = await _dio.get('/scans/$scanId');
    return Scan.fromJson(response.data as Map<String, dynamic>);
  }

  // ─────────────────────────────────────────────
  // Reports
  // ─────────────────────────────────────────────

  /// Get the export URL for officers (CSV download).
  String exportReportUrl({String? verdict, String format = 'csv'}) {
    final params = <String, String>{'fmt': format};
    if (verdict != null) params['verdict'] = verdict;
    final query = params.entries.map((e) => '${e.key}=${e.value}').join('&');
    return '$_baseUrl/reports/export?$query';
  }
}
