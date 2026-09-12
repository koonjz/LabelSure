// LabelSure — Scan Screen
// One-tap camera capture or gallery pick → compress → upload → navigate to result.
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import '../config/app_config.dart';
import '../config/app_theme.dart';
import '../models/scan.dart';
import '../services/api_service.dart';
import '../services/ocr_service.dart';
import '../utils/permission_helper.dart';
import '../widgets/profile_button.dart';


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


  /// Compress the image to max 1280px & 75% JPEG quality before upload.
  /// Reduces a typical 5 MB photo to ~200–400 KB — 10-20× faster upload.
  Future<File> _compressImage(File original) async {
    try {
      if (!original.existsSync()) return original;
      final dir = await getTemporaryDirectory();
      final outPath =
          '${dir.path}/labelsure_upload_${DateTime.now().millisecondsSinceEpoch}.jpg';
      final result = await FlutterImageCompress.compressAndGetFile(
        original.absolute.path,
        outPath,
        quality: 75,
        minWidth: 800,
        minHeight: 800,
        keepExif: true,   // preserve orientation so OCR sees correct side up
      );
      // Fall back to original if compression fails
      return result != null ? File(result.path) : original;
    } catch (e) {
      debugPrint('[Scan] Image compression skipped: $e');
      return original;
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

      // ── Step 1: On-device OCR (fast path — no image upload needed) ────────
      debugPrint('[Scan] Running on-device OCR with ML Kit...');
      Scan? scan;
      try {
        final ocrResult = await OnDeviceOcrService.extractText(_selectedImage!);
        debugPrint('[Scan] On-device OCR done: ${ocrResult.blockCount} blocks, '
            'script=${ocrResult.script}, chars=${ocrResult.fullText.length}');

        if (!ocrResult.isEmpty && ocrResult.fullText.trim().length >= 30) {
          // Good OCR result — send only text to backend (1KB vs 300KB+ image)
          final langCode = OnDeviceOcrService.scriptToLangCode(ocrResult.script);
          scan = await api.uploadTextScan(
            ocrText: ocrResult.fullText,
            langCode: langCode,
            salePrice: salePriceVal,
            fontType: _fontType,
          );
          debugPrint('[Scan] Text-based scan complete (on-device OCR path).');
        } else {
          debugPrint('[Scan] On-device OCR produced insufficient text '
              '(${ocrResult.fullText.trim().length} chars) — falling back to image upload.');
        }
      } catch (ocrErr) {
        debugPrint('[Scan] On-device OCR failed: $ocrErr — falling back to image upload.');
      }

      // ── Step 2: Fallback — upload compressed image if on-device OCR failed ─
      if (scan == null) {
        debugPrint('[Scan] Using image upload fallback...');
        final fileToUpload = await _compressImage(_selectedImage!);
        final origKb = (_selectedImage!.lengthSync() / 1024).round();
        final compKb  = (fileToUpload.lengthSync()  / 1024).round();
        debugPrint('[Scan] Upload: ${origKb}KB → ${compKb}KB '
            '(${((1 - compKb / origKb) * 100).round()}% smaller)');

        scan = await api.uploadScan(
          imageFile: fileToUpload,
          salePrice: salePriceVal,
          fontType: _fontType,
        );
      }

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
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          controller: _scrollCtrl,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Top Header with Title & Top-Right Profile Section
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 32,
                              height: 32,
                              padding: const EdgeInsets.all(5),
                              decoration: BoxDecoration(
                                gradient: AppColors.brandGradient,
                                borderRadius: BorderRadius.circular(9),
                              ),
                              child: Image.asset(
                                'assets/icons/app_icon.png',
                                fit: BoxFit.contain,
                                errorBuilder: (_, __, ___) => const Icon(
                                  Icons.document_scanner_rounded,
                                  color: Colors.white,
                                  size: 18,
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            const Text(
                              'LabelSure',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                letterSpacing: -0.5,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Legal Metrology Compliance Scanner',
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const ProfileButton(),
                ],
              ),
              const SizedBox(height: 24),

              // Image preview / capture area with Brand Viewfinder
              GestureDetector(
                onTap: () => _showPickerSheet(),
                child: AnimatedBuilder(
                  animation: _pulseCtrl,
                  builder: (_, child) => Container(
                    width: double.infinity,
                    height: 290,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _selectedImage != null
                            ? AppColors.brandTeal
                            : Color.lerp(
                                AppColors.surfaceElevated,
                                AppColors.brandTeal,
                                _pulseCtrl.value * 0.6,
                              )!,
                        width: 2,
                      ),
                      color: AppColors.surface,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.3),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
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
                                color: AppColors.brandTeal.withValues(alpha: 0.15),
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: AppColors.brandTeal.withValues(alpha: 0.3),
                                ),
                              ),
                              child: const Icon(
                                Icons.camera_alt_rounded,
                                color: AppColors.brandTealLight,
                                size: 36,
                              ),
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'Tap to capture product label',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Supports English & Indic packaged commodities',
                              style: TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                ),
              ).animate().fadeIn().scale(begin: const Offset(0.97, 0.97)),

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
                        label: _isUploading ? 'Analyzing...' : 'Scan for Compliance',
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

              // Optional: Sale price & Font type
              const SizedBox(height: 20),
              _ExpandableOptions(
                salePriceCtrl: _salePriceCtrl,
                fontType: _fontType,
                onFontTypeChanged: (v) => setState(() => _fontType = v),
              ),

              // Error banner
              if (_error != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.statusNonCompliantBg,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.statusNonCompliantBorder),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.error_outline_rounded, color: AppColors.statusNonCompliantLight, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _error!,
                              style: const TextStyle(color: AppColors.statusNonCompliantLight, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                      if (_isTimeoutError) ...[
                        const SizedBox(height: 8),
                        Divider(color: AppColors.statusNonCompliantBorder, height: 1, thickness: 0.5),
                        const SizedBox(height: 8),
                        const Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(Icons.lightbulb_outline_rounded,
                                color: AppColors.statusReviewLight, size: 15),
                            SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'Tip: The backend may be warming up from cold start (~60-90s). '
                                'Please try scanning again in a moment.',
                                style: TextStyle(
                                    color: AppColors.statusReviewLight, fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  void _showPickerSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
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
                  color: AppColors.brandBlue.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.camera_alt_rounded, color: AppColors.brandBlueLight),
              ),
              title: const Text('Camera', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
              subtitle: const Text('Take a photo of product label', style: TextStyle(color: AppColors.textSecondary)),
              onTap: () {
                Navigator.pop(context);
                _pickImage(ImageSource.camera);
              },
            ),
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.brandTeal.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.photo_library_rounded, color: AppColors.brandTealLight),
              ),
              title: const Text('Gallery', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
              subtitle: const Text('Choose an image from gallery', style: TextStyle(color: AppColors.textSecondary)),
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
          gradient: AppColors.brandGradientHorizontal,
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: AppColors.brandBlue.withValues(alpha: 0.35),
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
          side: BorderSide(color: AppColors.borderSubtle),
          backgroundColor: AppColors.surface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
        icon: Icon(icon, color: AppColors.brandTealLight, size: 20),
        label: Text(label, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
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
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.borderSubtle),
      ),
      child: Column(
        children: [
          ListTile(
            onTap: () => setState(() => _expanded = !_expanded),
            leading: const Icon(Icons.tune_rounded, color: AppColors.brandTealLight, size: 20),
            title: const Text(
              'Optional: Extra Compliance Checks',
              style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
            ),
            trailing: Icon(
              _expanded ? Icons.expand_less : Icons.expand_more,
              color: AppColors.textMuted,
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
                      labelText: 'Actual Charged Sale Price (₹)',
                      labelStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                      prefixIcon: const Icon(Icons.currency_rupee_rounded, color: AppColors.textMuted, size: 18),
                      filled: true,
                      fillColor: AppColors.surfaceSubtle,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide(color: AppColors.borderSubtle),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: const BorderSide(color: AppColors.brandTeal),
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                  ),
                  const SizedBox(height: 14),
                  const Text(
                    'Label Font Type',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12, fontWeight: FontWeight.w500),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      _FontTypeChip(
                        label: 'Printed (Standard)',
                        value: 'printed',
                        selected: widget.fontType,
                        onTap: () => widget.onFontTypeChanged('printed'),
                      ),
                      const SizedBox(width: 8),
                      _FontTypeChip(
                        label: 'Embossed / Moulded',
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
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.brandBlue.withValues(alpha: 0.25)
              : AppColors.surfaceSubtle,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? AppColors.brandBlueLight : AppColors.borderSubtle,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? Colors.white : AppColors.textSecondary,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}
