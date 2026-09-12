import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../config/app_theme.dart';
import '../models/scan.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/profile_button.dart';
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
      backgroundColor: AppColors.background,
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
                            letterSpacing: -0.5,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '$_total scan${_total != 1 ? 's' : ''} recorded',
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (isOfficer)
                    IconButton(
                      icon: const Icon(Icons.download_rounded, color: AppColors.brandTealLight),
                      tooltip: 'Export CSV',
                      onPressed: _exportCsv,
                    ),
                  IconButton(
                    icon: const Icon(Icons.refresh_rounded, color: AppColors.textMuted),
                    onPressed: () => _load(reset: true),
                  ),
                  const SizedBox(width: 4),
                  const ProfileButton(),
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
                        color: AppColors.brandTealLight,
                        onTap: () {
                          setState(() => _verdictFilter = null);
                          _load(reset: true);
                        },
                      ),
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: 'Compliant',
                        selected: _verdictFilter == 'COMPLIANT',
                        color: AppColors.statusCompliant,
                        onTap: () {
                          setState(() => _verdictFilter = 'COMPLIANT');
                          _load(reset: true);
                        },
                      ),
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: 'Non-Compliant',
                        selected: _verdictFilter == 'NON_COMPLIANT',
                        color: AppColors.statusNonCompliant,
                        onTap: () {
                          setState(() => _verdictFilter = 'NON_COMPLIANT');
                          _load(reset: true);
                        },
                      ),
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: 'Needs Review',
                        selected: _verdictFilter == 'NEEDS_REVIEW',
                        color: AppColors.statusReview,
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
                      child: CircularProgressIndicator(color: AppColors.brandTealLight))
                  : _error != null && _scans.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.error_outline_rounded,
                                  color: AppColors.statusNonCompliantLight, size: 48),
                              const SizedBox(height: 12),
                              Text(
                                _error!,
                                style: const TextStyle(color: AppColors.textSecondary),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 16),
                              ElevatedButton(
                                onPressed: () => _load(reset: true),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.brandBlue,
                                  foregroundColor: Colors.white,
                                ),
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
                                    color: AppColors.textMuted.withValues(alpha: 0.5),
                                    size: 64,
                                  ),
                                  const SizedBox(height: 16),
                                  const Text(
                                    'No scans recorded yet',
                                    style: TextStyle(
                                        color: AppColors.textSecondary,
                                        fontSize: 16),
                                  ),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              color: AppColors.brandTealLight,
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
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: AppColors.surfaceElevated,
        content: Text('Export URL: $url', style: const TextStyle(color: Colors.white)),
        action: SnackBarAction(
          label: 'Copy',
          textColor: AppColors.brandTealLight,
          onPressed: () {},
        ),
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
    final c = color ?? AppColors.brandTealLight;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: 200.ms,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? c.withValues(alpha: 0.2) : AppColors.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? c : AppColors.borderSubtle,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? c : AppColors.textSecondary,
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
            foregroundColor: AppColors.brandTealLight,
            side: const BorderSide(color: AppColors.brandTealLight),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          ),
          child: const Text('Load More'),
        ),
      ),
    );
  }
}
