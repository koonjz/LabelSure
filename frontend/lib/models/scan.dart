// LabelSure — Scan Model
class Scan {
  final String id;
  final String? verdict; // 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW'
  final double? overallConfidence;
  final bool needsManualReview;
  final String? reviewReason;
  final String? detectedLanguage;
  final String? imageFilename;
  final DateTime createdAt;
  final DateTime? processedAt;
  final double? enteredSalePrice;
  final String? rawOcrText;   // Full OCR output for debugging
  final String? ocrEngine;    // paddleocr / tesseract / none
  final List<ExtractedField> extractedFields;
  final List<RuleResult> ruleResults;

  const Scan({
    required this.id,
    this.verdict,
    this.overallConfidence,
    required this.needsManualReview,
    this.reviewReason,
    this.detectedLanguage,
    this.imageFilename,
    required this.createdAt,
    this.processedAt,
    this.enteredSalePrice,
    this.rawOcrText,
    this.ocrEngine,
    required this.extractedFields,
    required this.ruleResults,
  });

  factory Scan.fromJson(Map<String, dynamic> json) {
    return Scan(
      id: json['scan_id'] ?? json['id'] ?? '',
      verdict: json['verdict'],
      overallConfidence: (json['overall_confidence'] as num?)?.toDouble(),
      needsManualReview: json['needs_manual_review'] ?? false,
      reviewReason: json['review_reason'],
      detectedLanguage: json['detected_language'],
      imageFilename: json['image_filename'],
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
      processedAt: json['processed_at'] != null ? DateTime.parse(json['processed_at']) : null,
      enteredSalePrice: (json['entered_sale_price'] as num?)?.toDouble(),
      rawOcrText: json['raw_ocr_text'],
      ocrEngine: json['ocr_engine'],
      extractedFields: (json['extracted_fields'] as List<dynamic>? ?? [])
          .map((e) => ExtractedField.fromJson(e))
          .toList(),
      ruleResults: (json['rule_results'] as List<dynamic>? ?? [])
          .map((e) => RuleResult.fromJson(e))
          .toList(),
    );
  }

  bool get isCompliant => verdict == 'COMPLIANT';
  bool get isNonCompliant => verdict == 'NON_COMPLIANT';
  bool get isNeedsReview => verdict == 'NEEDS_REVIEW' || needsManualReview;

  int get passCount => ruleResults.where((r) => r.passed).length;
  int get failCount => ruleResults.where((r) => !r.passed).length;
}

class ScanListItem {
  final String id;
  final String? verdict;
  final bool needsManualReview;
  final String? detectedLanguage;
  final double? overallConfidence;
  final String? imageFilename;
  final DateTime createdAt;

  const ScanListItem({
    required this.id,
    this.verdict,
    required this.needsManualReview,
    this.detectedLanguage,
    this.overallConfidence,
    this.imageFilename,
    required this.createdAt,
  });

  factory ScanListItem.fromJson(Map<String, dynamic> json) {
    return ScanListItem(
      id: json['id'] ?? '',
      verdict: json['verdict'],
      needsManualReview: json['needs_manual_review'] ?? false,
      detectedLanguage: json['detected_language'],
      overallConfidence: (json['overall_confidence'] as num?)?.toDouble(),
      imageFilename: json['image_filename'],
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
    );
  }

  bool get isCompliant => verdict == 'COMPLIANT';
}

class ExtractedField {
  final String fieldName;
  final String? fieldValue;
  final double? confidence;

  const ExtractedField({
    required this.fieldName,
    this.fieldValue,
    this.confidence,
  });

  factory ExtractedField.fromJson(Map<String, dynamic> json) {
    return ExtractedField(
      fieldName: json['field_name'] ?? '',
      fieldValue: json['field_value'],
      confidence: (json['confidence'] as num?)?.toDouble(),
    );
  }

  String get displayName {
    final map = {
      'generic_name': 'Product / Commodity Name',
      'manufacturer_name': 'Manufacturer / Packer',
      'manufacturer_address': 'Manufacturer Address',
      'net_quantity_value': 'Net Quantity',
      'net_quantity_unit': 'Unit',
      'mrp': 'MRP (₹)',
      'manufacture_month': 'Manufacture Month',
      'manufacture_year': 'Manufacture Year',
      'batch_number': 'Batch / Lot No.',
      'expiry_date': 'Best Before / Expiry',
      'fssai_license': 'FSSAI License No.',
      'consumer_care': 'Consumer Care',
      'measured_font_height_mm': 'Font Height (mm)',
    };
    return map[fieldName] ?? fieldName;
  }
}

class RuleResult {
  final String ruleId;
  final String ruleName;
  final bool passed;
  final String? explanation;
  final String? severity;

  const RuleResult({
    required this.ruleId,
    required this.ruleName,
    required this.passed,
    this.explanation,
    this.severity,
  });

  factory RuleResult.fromJson(Map<String, dynamic> json) {
    return RuleResult(
      ruleId: json['rule_id'] ?? '',
      ruleName: json['rule_name'] ?? '',
      passed: json['passed'] ?? false,
      explanation: json['explanation'],
      severity: json['severity'],
    );
  }
}
