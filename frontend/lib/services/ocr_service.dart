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

  /// Detect which script the text predominantly contains.
  static String _detectScript(String text) {
    if (text.trim().isEmpty) return 'latin';

    final latinCount = RegExp(r'[a-zA-Z]').allMatches(text).length;

    final indicCounts = <String, int>{
      'devanagari': RegExp(r'[\u0900-\u097F]').allMatches(text).length,
      'tamil': RegExp(r'[\u0B80-\u0BFF]').allMatches(text).length,
      'telugu': RegExp(r'[\u0C00-\u0C7F]').allMatches(text).length,
      'kannada': RegExp(r'[\u0C80-\u0CFF]').allMatches(text).length,
      'malayalam': RegExp(r'[\u0D00-\u0D7F]').allMatches(text).length,
      'gujarati': RegExp(r'[\u0A80-\u0AFF]').allMatches(text).length,
      'gurmukhi': RegExp(r'[\u0A00-\u0A7F]').allMatches(text).length,
      'bengali': RegExp(r'[\u0980-\u09FF]').allMatches(text).length,
    };

    String? topScript;
    int maxIndic = 0;
    for (final entry in indicCounts.entries) {
      if (entry.value > maxIndic) {
        maxIndic = entry.value;
        topScript = entry.key;
      }
    }

    // An Indic script is considered dominant only if:
    // 1. There are at least 15 Indic characters, AND
    // 2. Either Indic characters outnumber Latin, or Indic forms >= 40% of Latin count
    if (topScript != null && maxIndic >= 15 && (maxIndic > latinCount || (maxIndic >= 20 && maxIndic > latinCount * 0.4))) {
      return topScript;
    }

    return 'latin';
  }

  // ── Main OCR entry point ───────────────────────────────────────────────────

  /// Extract text from [imageFile] using on-device ML Kit OCR.
  ///
  /// Runs a **Latin** pass first (catches English + numbers + MRP/weight).
  /// If Indic Unicode is detected or needed, runs an Indic script recognizer
  /// and only merges it if genuine Indic text was detected.
  ///
  /// Returns an [OcrResult] with the full merged text.
  static Future<OcrResult> extractText(File imageFile) async {
    try {
      if (!imageFile.existsSync()) {
        return const OcrResult(fullText: '', script: 'latin', blockCount: 0);
      }

      final inputImage = InputImage.fromFile(imageFile);

      // ── Pass 1: Latin recognizer (always available) ─────────────────────────
      String latinText = '';
      int latinBlocks = 0;
      try {
        final latinRecognizer = TextRecognizer(script: TextRecognitionScript.latin);
        try {
          final result = await latinRecognizer.processImage(inputImage);
          latinText = result.text;
          latinBlocks = result.blocks.length;
        } finally {
          await latinRecognizer.close();
        }
        debugPrint('[OCR] Latin pass: ${latinText.length} chars, $latinBlocks blocks');
      } catch (e) {
        debugPrint('[OCR] Latin pass failed: $e');
      }

      // ── Pass 2: Indic recognizer ───────────────────────────────────────────
      String indicText = '';
      int indicBlocks = 0;

      final indicRecognizers = [
        TextRecognitionScript.devanagiri,  // Hindi, Marathi
      ];

      for (final script in indicRecognizers) {
        try {
          final recognizer = TextRecognizer(script: script);
          try {
            final result = await recognizer.processImage(inputImage);
            final rawText = result.text.trim();
            final indicGlyphCount = RegExp(r'[\u0900-\u097F]').allMatches(rawText).length;

            // Only accept Indic pass if it actually found meaningful Indic glyphs (>= 12)
            // to avoid hallucinated noise on English labels
            if (indicGlyphCount >= 12 && rawText.length > indicText.trim().length) {
              indicText = rawText;
              indicBlocks = result.blocks.length;
              debugPrint('[OCR] ${script.name} pass accepted: ${indicText.length} chars ($indicGlyphCount glyphs)');
            }
          } finally {
            await recognizer.close();
          }
        } catch (e) {
          debugPrint('[OCR] ${script.name} pass skipped or failed: $e');
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
    } catch (topLevelError) {
      debugPrint('[OCR] Top-level on-device OCR error: $topLevelError');
      return const OcrResult(fullText: '', script: 'latin', blockCount: 0);
    }
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
