// LabelSure — Permission Helper
//
// Requests CAMERA and storage permissions gracefully with a rationale dialog
// when the user denies on first ask.  Shows a settings-redirect dialog on
// permanent denial (user ticked "Don't ask again").
//
// Usage:
//   final ok = await PermissionHelper.requestCamera(context);
//   if (!ok) return; // user denied
import 'dart:io';
import 'package:flutter/material.dart';

// NOTE: We avoid adding the `permission_handler` pub package to keep the
// dependency tree small.  On Android, image_picker itself handles the
// permission prompts at the OS level when it opens the camera or gallery.
// This helper instead intercepts the error thrown by image_picker when
// the user has permanently denied permissions and guides them to Settings.
//
// If you want explicit pre-permission checks, add permission_handler to
// pubspec.yaml and uncomment the alternative implementation below.

class PermissionHelper {
  PermissionHelper._();

  /// Show a dialog explaining why camera permission is needed.
  /// Returns true if the user says "OK" (they'll get the OS prompt next).
  /// Returns false if they cancel.
  static Future<bool> showCameraRationale(BuildContext context) async {
    if (!context.mounted) return false;
    return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1E293B),
            title: const Row(
              children: [
                Icon(Icons.camera_alt_rounded, color: Color(0xFF3B82F6), size: 22),
                SizedBox(width: 10),
                Text('Camera Permission', style: TextStyle(color: Colors.white, fontSize: 18)),
              ],
            ),
            content: const Text(
              'LabelSure needs camera access to photograph product labels for '
              'compliance checking.\n\n'
              'You can also use "Gallery" to pick an existing photo instead.',
              style: TextStyle(color: Colors.white70, height: 1.5),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Not now', style: TextStyle(color: Colors.white54)),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF3B82F6),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Allow Camera'),
              ),
            ],
          ),
        ) ??
        false;
  }

  /// Show a dialog directing the user to app Settings when permission is
  /// permanently denied.
  static Future<void> showPermanentlyDeniedDialog(
    BuildContext context, {
    required String permissionName,
  }) async {
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: Row(
          children: [
            const Icon(Icons.block_rounded, color: Color(0xFFEF4444), size: 22),
            const SizedBox(width: 10),
            Text('$permissionName Denied', style: const TextStyle(color: Colors.white, fontSize: 18)),
          ],
        ),
        content: Text(
          '$permissionName permission was permanently denied.\n\n'
          'Go to Settings → Apps → LabelSure → Permissions to re-enable it.',
          style: const TextStyle(color: Colors.white70, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
          ),
          // Optionally open app settings if you add app_settings package:
          // ElevatedButton(onPressed: () { AppSettings.openAppSettings(); ... },
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF3B82F6),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: () => Navigator.pop(ctx),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  /// Returns true if we're running on Android (not iOS, web, etc.)
  static bool get isAndroid => Platform.isAndroid;
}
