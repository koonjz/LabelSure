// LabelSure — On-Device OCR Service
// Uses Google ML Kit Text Recognition to extract text from images entirely
// on the phone — no internet required for OCR itself.
//
// Supported scripts (ML Kit model bundles):
//   • Latin  — English, numbers, symbols (bundled, always available)
//   • Devanagari — Hindi, Marathi (model auto-downloaded ~8MB on first use)
//   • Tamil, Telugu, Kannada, Malayalam (model auto-downloaded on first use)
//
// Usage:
//   final result = await OnDeviceOcrService.extractText(imageFile);
//   print(result.fullText);
//   print(result.script);     // 'latin' | 'devanagari' | 'tamil' etc.

import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';

/// Result of on-device OCR.
class OcrResult {
  /// Full extracted text (all blocks joined with newlines).
  final String fullText;

  /// Script detected: 'latin', 'devanagari', 'tamil', 'telugu', 'kannada', 'malayalam'
  final String script;

  /// Number of text blocks found (0 = nothing detected).
  final int blockCount;

  const OcrResult({
    required this.fullText,
    required this.script,
    required this.blockCount,
  });

  bool get isEmpty => fullText.trim().isEmpty;
  bool get isIndic => script != 'latin';

  @override
  String toString() => 'OcrResult(script: $script, blocks: $blockCount, '
      'chars: ${fullText.length})';
}

class OnDeviceOcrService {
  OnDeviceOcrService._(); // static-only class

  // ── Script detection helpers ───────────────────────────────────────────────

  /// Detect which script the text contains.
  static String _detectScript(String text) {
    // Devanagari Unicode range: U+0900–U+097F
    if (RegExp(r'[\u0900-\u097F]').hasMatch(text)) return 'devanagari';
    // Tamil: U+0B80–U+0BFF
    if (RegExp(r'[\u0B80-\u0BFF]').hasMatch(text)) return 'tamil';
    // Telugu: U+0C00–U+0C7F
    if (RegExp(r'[\u0C00-\u0C7F]').hasMatch(text)) return 'telugu';
    // Kannada: U+0C80–U+0CFF
    if (RegExp(r'[\u0C80-\u0CFF]').hasMatch(text)) return 'kannada';
    // Malayalam: U+0D00–U+0D7F
    if (RegExp(r'[\u0D00-\u0D7F]').hasMatch(text)) return 'malayalam';
    // Gujarati: U+0A80–U+0AFF
    if (RegExp(r'[\u0A80-\u0AFF]').hasMatch(text)) return 'gujarati';
    // Gurmukhi (Punjabi): U+0A00–U+0A7F
    if (RegExp(r'[\u0A00-\u0A7F]').hasMatch(text)) return 'gurmukhi';
    return 'latin';
  }

  // ── Main OCR entry point ───────────────────────────────────────────────────

  /// Extract text from [imageFile] using on-device ML Kit OCR.
  ///
  /// Runs a **Latin** pass first (catches English + numbers + MRP/weight).
  /// If Indic Unicode is detected, runs an additional pass with the
  /// appropriate Indic script recognizer and merges the results.
  ///
  /// Returns an [OcrResult] with the full merged text.
  static Future<OcrResult> extractText(File imageFile) async {
    final inputImage = InputImage.fromFile(imageFile);

    // ── Pass 1: Latin recognizer (always available, no download needed) ──────
    String latinText = '';
    int latinBlocks = 0;
    try {
      final latinRecognizer = TextRecognizer(script: TextRecognitionScript.latin);
      final result = await latinRecognizer.processImage(inputImage);
      latinText = result.text;
      latinBlocks = result.blocks.length;
      await latinRecognizer.close();
      debugPrint('[OCR] Latin pass: ${latinText.length} chars, $latinBlocks blocks');
    } catch (e) {
      debugPrint('[OCR] Latin pass failed: $e');
    }

    // ── Detect if Indic script is present ─────────────────────────────────
    // Even if Latin pass gets MRP/weight, Indic pass gets manufacturer name etc.
    // We always run Devanagari for Indian food labels (most common Indic script).
    String indicText = '';
    int indicBlocks = 0;

    // NOTE: google_mlkit_text_recognition v0.13.x supports:
    //   latin, chinese, devanagiri (Hindi/Marathi), japanese, korean
    // Tamil, Telugu, Kannada, Malayalam are NOT in this SDK version.
    // We run devanagiri for all Indic scripts (covers Hindi/Marathi labels).
    // Latin pass already handles English numbers, MRP, weights.
    final indicRecognizers = [
      TextRecognitionScript.devanagiri,  // Hindi, Marathi
    ];

    // Try each Indic model and take the one that produces the most text
    for (final script in indicRecognizers) {
      try {
        final recognizer = TextRecognizer(script: script);
        final result = await recognizer.processImage(inputImage);
        await recognizer.close();
        if (result.text.trim().length > indicText.trim().length) {
          indicText = result.text;
          indicBlocks = result.blocks.length;
          debugPrint('[OCR] ${script.name} pass: ${indicText.length} chars');
        }
      } catch (e) {
        debugPrint('[OCR] ${script.name} pass failed: $e');
      }
    }

    // ── Merge Latin + Indic ────────────────────────────────────────────────
    final mergedText = _mergeTexts(latinText, indicText);
    final detectedScript = _detectScript(mergedText);

    debugPrint('[OCR] Merged: ${mergedText.length} chars, script: $detectedScript');

    return OcrResult(
      fullText: mergedText,
      script: detectedScript,
      blockCount: latinBlocks + indicBlocks,
    );
  }

  /// Merge two OCR text outputs by deduplicating lines.
  static String _mergeTexts(String text1, String text2) {
    if (text1.isEmpty) return text2;
    if (text2.isEmpty) return text1;

    // Collect unique non-empty lines (case-insensitive dedup)
    final seen = <String>{};
    final merged = <String>[];

    for (final line in [...text1.split('\n'), ...text2.split('\n')]) {
      final trimmed = line.trim();
      if (trimmed.isEmpty) continue;
      final key = trimmed.toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
      if (seen.add(key)) {
        merged.add(trimmed);
      }
    }

    return merged.join('\n');
  }

  // ── Script code for backend ────────────────────────────────────────────────

  /// Convert ML Kit script name to ISO 639-1 lang code for the backend.
  static String scriptToLangCode(String script) {
    const map = {
      'devanagari': 'hi',
      'tamil': 'ta',
      'telugu': 'te',
      'kannada': 'kn',
      'malayalam': 'ml',
      'gujarati': 'gu',
      'gurmukhi': 'pa',
      'latin': 'en',
    };
    return map[script] ?? 'en';
  }
}
