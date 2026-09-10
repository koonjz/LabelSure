// LabelSure — Scan Detail Screen
// Shows full details for a single scan fetched from the API.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../models/scan.dart';
import '../services/api_service.dart';
import '../widgets/compliance_badge.dart';
import '../widgets/rule_checklist.dart';

class ScanDetailScreen extends StatefulWidget {
  final String scanId;

  const ScanDetailScreen({super.key, required this.scanId});

  @override
  State<ScanDetailScreen> createState() => _ScanDetailScreenState();
}

class _ScanDetailScreenState extends State<ScanDetailScreen> {
  Scan? _scan;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final api = context.read<ApiService>();
      final scan = await api.getScan(widget.scanId);
      setState(() {
        _scan = scan;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1C),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0A0F1C),
        title: const Text(
          'Scan Detail',
          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => context.pop(),
        ),
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6)))
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.error_outline,
                          color: Color(0xFFEF4444), size: 48),
                      const SizedBox(height: 12),
                      Text(
                        _error!,
                        style: const TextStyle(color: Colors.white54),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _load,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Badge
                      ComplianceBadge(verdict: _scan!.verdict ?? 'NEEDS_REVIEW'),
                      const SizedBox(height: 24),

                      // Scan ID
                      Text(
                        'Scan ID: ${_scan!.id.substring(0, 8).toUpperCase()}',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.5),
                          fontSize: 12,
                          letterSpacing: 1,
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Rule checklist
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Compliance Rules',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      RuleChecklist(ruleResults: _scan!.ruleResults),

                      const SizedBox(height: 20),

                      // Extracted fields
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Extracted Label Fields',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(14),
                          border:
                              Border.all(color: Colors.white.withOpacity(0.08)),
                        ),
                        child: ListView.separated(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: _scan!.extractedFields
                              .where((f) => f.fieldValue != null)
                              .length,
                          separatorBuilder: (_, __) =>
                              const Divider(color: Colors.white12, height: 1),
                          itemBuilder: (_, i) {
                            final fields = _scan!.extractedFields
                                .where((f) => f.fieldValue != null)
                                .toList();
                            final f = fields[i];
                            return Padding(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 12),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    flex: 2,
                                    child: Text(
                                      f.displayName,
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.5),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  Expanded(
                                    flex: 3,
                                    child: Text(
                                      f.fieldValue ?? '—',
                                      textAlign: TextAlign.end,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),

                      const SizedBox(height: 40),
                    ],
                  ),
                ),
    );
  }
}
