// LabelSure — Scan History Screen (Officer role only shows full list)
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../models/scan.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/scan_card.dart';

class ScanHistoryScreen extends StatefulWidget {
  const ScanHistoryScreen({super.key});

  @override
  State<ScanHistoryScreen> createState() => _ScanHistoryScreenState();
}

class _ScanHistoryScreenState extends State<ScanHistoryScreen> {
  List<ScanListItem> _scans = [];
  bool _isLoading = true;
  String? _error;
  String? _verdictFilter;
  int _page = 1;
  int _total = 0;
  static const _pageSize = 20;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool reset = false}) async {
    if (reset) {
      setState(() {
        _page = 1;
        _scans = [];
      });
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final api = context.read<ApiService>();
      final data = await api.listScans(
        verdict: _verdictFilter,
        page: _page,
        pageSize: _pageSize,
      );
      final items = (data['items'] as List<dynamic>)
          .map((e) => ScanListItem.fromJson(e as Map<String, dynamic>))
          .toList();
      setState(() {
        if (reset || _page == 1) {
          _scans = items;
        } else {
          _scans.addAll(items);
        }
        _total = data['total'] as int? ?? 0;
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
    final auth = context.watch<AuthService>();
    final isOfficer = auth.isOfficer;

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1C),
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Scan History',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 26,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          '$_total scan${_total != 1 ? 's' : ''} found',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.45),
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (isOfficer)
                    IconButton(
                      icon: const Icon(Icons.download_rounded, color: Color(0xFF60A5FA)),
                      tooltip: 'Export CSV',
                      onPressed: _exportCsv,
                    ),
                  IconButton(
                    icon: const Icon(Icons.refresh_rounded, color: Colors.white54),
                    onPressed: () => _load(reset: true),
                  ),
                ],
              ),
            ),
            // Filter chips
            if (isOfficer)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _FilterChip(
                        label: 'All',
                        selected: _verdictFilter == null,
                        onTap: () {
                          setState(() => _verdictFilter = null);
                          _load(reset: true);
                        },
                      ),
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: 'Compliant',
                        selected: _verdictFilter == 'COMPLIANT',
                        color: const Color(0xFF22C55E),
                        onTap: () {
                          setState(() => _verdictFilter = 'COMPLIANT');
                          _load(reset: true);
                        },
                      ),
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: 'Non-Compliant',
                        selected: _verdictFilter == 'NON_COMPLIANT',
                        color: const Color(0xFFEF4444),
                        onTap: () {
                          setState(() => _verdictFilter = 'NON_COMPLIANT');
                          _load(reset: true);
                        },
                      ),
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: 'Needs Review',
                        selected: _verdictFilter == 'NEEDS_REVIEW',
                        color: const Color(0xFFF59E0B),
                        onTap: () {
                          setState(() => _verdictFilter = 'NEEDS_REVIEW');
                          _load(reset: true);
                        },
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            // List
            Expanded(
              child: _isLoading && _scans.isEmpty
                  ? const Center(
                      child: CircularProgressIndicator(color: Color(0xFF3B82F6)))
                  : _error != null && _scans.isEmpty
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
                                onPressed: () => _load(reset: true),
                                child: const Text('Retry'),
                              ),
                            ],
                          ),
                        )
                      : _scans.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.document_scanner_outlined,
                                    color: Colors.white.withOpacity(0.2),
                                    size: 64,
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    'No scans yet',
                                    style: TextStyle(
                                        color: Colors.white.withOpacity(0.4),
                                        fontSize: 16),
                                  ),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              color: const Color(0xFF3B82F6),
                              onRefresh: () => _load(reset: true),
                              child: ListView.builder(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 16),
                                itemCount:
                                    _scans.length + (_total > _scans.length ? 1 : 0),
                                itemBuilder: (_, i) {
                                  if (i == _scans.length) {
                                    return _LoadMoreButton(onTap: () {
                                      setState(() => _page++);
                                      _load();
                                    });
                                  }
                                  return ScanCard(
                                    scan: _scans[i],
                                    onTap: () =>
                                        context.push('/scan-detail/${_scans[i].id}'),
                                  ).animate(delay: Duration(milliseconds: 50 * i))
                                      .fadeIn()
                                      .slideY(begin: 0.1, end: 0);
                                },
                              ),
                            ),
            ),
          ],
        ),
      ),
    );
  }

  void _exportCsv() {
    final api = context.read<ApiService>();
    final url = api.exportReportUrl(verdict: _verdictFilter);
    // In a real app, launch the URL with url_launcher
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Export URL: $url'),
        action: SnackBarAction(label: 'Copy', onPressed: () {}),
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final Color? color;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.selected,
    this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? const Color(0xFF3B82F6);
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: 200.ms,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? c.withOpacity(0.2) : const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? c : Colors.white.withOpacity(0.1),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? c : Colors.white54,
            fontSize: 12,
            fontWeight: selected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }
}

class _LoadMoreButton extends StatelessWidget {
  final VoidCallback onTap;
  const _LoadMoreButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Center(
        child: OutlinedButton(
          onPressed: onTap,
          style: OutlinedButton.styleFrom(
            foregroundColor: const Color(0xFF60A5FA),
            side: const BorderSide(color: Color(0xFF60A5FA)),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          ),
          child: const Text('Load More'),
        ),
      ),
    );
  }
}
