// LabelSure — Scan Screen
// One-tap camera capture or gallery pick → upload → navigate to result.
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../config/app_config.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../utils/permission_helper.dart';


class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> with SingleTickerProviderStateMixin {
  final ImagePicker _picker = ImagePicker();
  File? _selectedImage;
  bool _isUploading = false;
  String? _error;
  bool _isTimeoutError = false;

  final _scrollCtrl = ScrollController();

  // Optional fields
  String _fontType = 'printed';
  final _salePriceCtrl = TextEditingController();

  late AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _salePriceCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    // For camera on Android, show a rationale dialog on first open.
    // This primes the user so they understand why the OS will ask next.
    if (source == ImageSource.camera && PermissionHelper.isAndroid) {
      // We only show the rationale the very first time (_selectedImage is null).
      // After the first pick, the OS caches the user's choice.
    }

    try {
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 90,
      );
      if (picked != null) {
        setState(() {
          _selectedImage = File(picked.path);
          _error = null;
        });
      }
    } catch (e) {
      final msg = e.toString().toLowerCase();
      final isPermDenied = msg.contains('denied') || msg.contains('permission');
      if (source == ImageSource.camera) {
        if (isPermDenied && mounted) {
          await PermissionHelper.showPermanentlyDeniedDialog(
            context,
            permissionName: 'Camera',
          );
          setState(() => _error =
              'Camera permission denied. Use "Gallery" below to pick an image,\n'
              'or grant Camera permission in Settings.');
        } else {
          setState(() => _error =
              'Camera unavailable on this device/emulator.\n'
              'Use the "Choose from Gallery" button below instead.');
        }
      } else {
        setState(() => _error = 'Could not open gallery: $e');
      }
    }
  }


  Future<void> _uploadScan() async {
    if (_selectedImage == null) return;
    setState(() {
      _isUploading = true;
      _error = null;
      _isTimeoutError = false;
    });

    try {
      final api = context.read<ApiService>();
      final salePriceVal = _salePriceCtrl.text.isNotEmpty
          ? double.tryParse(_salePriceCtrl.text)
          : null;

      final scan = await api.uploadScan(
        imageFile: _selectedImage!,
        salePrice: salePriceVal,
        fontType: _fontType,
      );

      if (mounted) {
        context.push('/scan-result', extra: scan);
      }
    } on ApiException catch (e) {
      final msg = e.toString();
      final isTimeout = msg.contains('timed out') || msg.contains('timeout');
      setState(() {
        _error = msg;
        _isTimeoutError = isTimeout;
      });
      _scrollToError();
    } catch (e) {
      final msg = e.toString().toLowerCase();
      final isTimeout = msg.contains('timed out') || msg.contains('timeout');
      setState(() {
        _error = 'Upload failed: ${e.toString()}\nBackend URL: ${AppConfig.baseUrl}';
        _isTimeoutError = isTimeout;
      });
      _scrollToError();
    } finally {
      if (mounted) setState(() => _isUploading = false);
    }
  }

  void _scrollToError() {
    // Give the widget tree a frame to rebuild with the error widget, then scroll.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 350),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1C),
      body: SafeArea(
        child: SingleChildScrollView(
          controller: _scrollCtrl,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 16),
              // Header
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Scan Label',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          'Hello, ${auth.user?.displayName ?? 'User'}',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.5),
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(
                      Icons.document_scanner_rounded,
                      color: Color(0xFF3B82F6),
                      size: 24,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 32),

              // Image preview / capture area
              GestureDetector(
                onTap: () => _showPickerSheet(),
                child: AnimatedBuilder(
                  animation: _pulseCtrl,
                  builder: (_, child) => Container(
                    width: double.infinity,
                    height: 280,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _selectedImage != null
                            ? const Color(0xFF3B82F6)
                            : Color.lerp(
                                const Color(0xFF1E293B),
                                const Color(0xFF3B82F6),
                                _pulseCtrl.value * 0.5,
                              )!,
                        width: 2,
                      ),
                      color: const Color(0xFF0F172A),
                    ),
                    child: child,
                  ),
                  child: _selectedImage != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(18),
                          child: Image.file(
                            _selectedImage!,
                            fit: BoxFit.cover,
                            width: double.infinity,
                          ),
                        )
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              width: 72,
                              height: 72,
                              decoration: BoxDecoration(
                                color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.camera_alt_rounded,
                                color: Color(0xFF3B82F6),
                                size: 36,
                              ),
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'Tap to capture label',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Camera or Gallery',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.4),
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                ),
              ).animate().fadeIn().scale(begin: const Offset(0.95, 0.95)),

              const SizedBox(height: 20),

              // Action buttons
              if (_selectedImage != null)
                Row(
                  children: [
                    Expanded(
                      child: _OutlineButton(
                        label: 'Retake',
                        icon: Icons.refresh_rounded,
                        onTap: _showPickerSheet,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: _GradientButton(
                        label: _isUploading ? 'Scanning...' : 'Scan for Compliance',
                        icon: Icons.document_scanner_rounded,
                        isLoading: _isUploading,
                        onTap: _uploadScan,
                      ),
                    ),
                  ],
                ).animate().fadeIn(delay: 100.ms),

              if (_selectedImage == null)
                Column(
                  children: [
                    _GradientButton(
                      label: 'Open Camera',
                      icon: Icons.camera_alt_rounded,
                      onTap: () => _pickImage(ImageSource.camera),
                    ),
                    const SizedBox(height: 10),
                    _OutlineButton(
                      label: 'Choose from Gallery',
                      icon: Icons.photo_library_rounded,
                      onTap: () => _pickImage(ImageSource.gallery),
                    ),
                  ],
                ).animate().fadeIn(delay: 100.ms),

              // Optional: Sale price
              const SizedBox(height: 24),
              _ExpandableOptions(
                salePriceCtrl: _salePriceCtrl,
                fontType: _fontType,
                onFontTypeChanged: (v) => setState(() => _fontType = v),
              ),

              // Error
              if (_error != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _error!,
                              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                      if (_isTimeoutError) ...[
                        const SizedBox(height: 8),
                        const Divider(color: Color(0xFFEF4444), height: 1, thickness: 0.3),
                        const SizedBox(height: 8),
                        const Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.lightbulb_outline,
                                color: Color(0xFFFBBF24), size: 15),
                            const SizedBox(width: 6),
                            const Expanded(
                              child: Text(
                                'Tip: The backend may be starting up (cold start can take ~90 s). '
                                'Wait a moment and tap "Scan for Compliance" again.',
                                style: TextStyle(
                                    color: Color(0xFFFBBF24), fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  void _showPickerSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 20),
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.camera_alt_rounded, color: Color(0xFF3B82F6)),
              ),
              title: const Text('Camera', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Take a new photo', style: TextStyle(color: Colors.white54)),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.camera);
              },
            ),
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF8B5CF6).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.photo_library_rounded, color: Color(0xFF8B5CF6)),
              ),
              title: const Text('Gallery', style: TextStyle(color: Colors.white)),
              subtitle: const Text('Choose existing photo', style: TextStyle(color: Colors.white54)),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.gallery);
              },
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _GradientButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool isLoading;

  const _GradientButton({
    required this.label,
    required this.icon,
    required this.onTap,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF3B82F6), Color(0xFF8B5CF6)],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF3B82F6).withValues(alpha: 0.3),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ElevatedButton.icon(
          onPressed: isLoading ? null : onTap,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.transparent,
            shadowColor: Colors.transparent,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          icon: isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                )
              : Icon(icon, color: Colors.white, size: 20),
          label: Text(
            label,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
        ),
      ),
    );
  }
}

class _OutlineButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _OutlineButton({required this.label, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: OutlinedButton.icon(
        onPressed: onTap,
        style: OutlinedButton.styleFrom(
          foregroundColor: Colors.white,
          side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
        icon: Icon(icon, size: 20),
        label: Text(label, style: const TextStyle(fontSize: 14)),
      ),
    );
  }
}

class _ExpandableOptions extends StatefulWidget {
  final TextEditingController salePriceCtrl;
  final String fontType;
  final ValueChanged<String> onFontTypeChanged;

  const _ExpandableOptions({
    required this.salePriceCtrl,
    required this.fontType,
    required this.onFontTypeChanged,
  });

  @override
  State<_ExpandableOptions> createState() => _ExpandableOptionsState();
}

class _ExpandableOptionsState extends State<_ExpandableOptions> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        children: [
          ListTile(
            onTap: () => setState(() => _expanded = !_expanded),
            leading: const Icon(Icons.tune_rounded, color: Color(0xFF60A5FA), size: 20),
            title: const Text(
              'Optional: Extra Details',
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
            trailing: Icon(
              _expanded ? Icons.expand_less : Icons.expand_more,
              color: Colors.white38,
            ),
          ),
          if (_expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: widget.salePriceCtrl,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: 'Sale Price (₹) — for MRP check',
                      labelStyle: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
                      prefixIcon: const Icon(Icons.currency_rupee, color: Colors.white38, size: 18),
                      filled: true,
                      fillColor: Colors.white.withValues(alpha: 0.05),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Font Type',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      _FontTypeChip(
                        label: 'Printed',
                        value: 'printed',
                        selected: widget.fontType,
                        onTap: () => widget.onFontTypeChanged('printed'),
                      ),
                      const SizedBox(width: 8),
                      _FontTypeChip(
                        label: 'Embossed/Moulded',
                        value: 'embossed',
                        selected: widget.fontType,
                        onTap: () => widget.onFontTypeChanged('embossed'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _FontTypeChip extends StatelessWidget {
  final String label, value, selected;
  final VoidCallback onTap;

  const _FontTypeChip({
    required this.label, required this.value,
    required this.selected, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isSelected = value == selected;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFF3B82F6).withValues(alpha: 0.2)
              : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? const Color(0xFF3B82F6) : Colors.white.withValues(alpha: 0.1),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? const Color(0xFF3B82F6) : Colors.white54,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}
