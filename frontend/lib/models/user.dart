// LabelSure — User Model
class User {
  final String id;
  final String email;
  final String? fullName;
  final String role; // 'officer' | 'admin' | 'consumer' | 'seller'
  final String? region;
  final bool isActive;

  const User({
    required this.id,
    required this.email,
    this.fullName,
    required this.role,
    this.region,
    required this.isActive,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] ?? '',
      email: json['email'] ?? '',
      fullName: json['full_name'],
      role: json['role'] ?? 'consumer',
      region: json['region'],
      isActive: json['is_active'] ?? true,
    );
  }

  bool get isOfficer => role == 'officer' || role == 'admin';
  bool get isConsumerOrSeller => role == 'consumer' || role == 'seller';

  String get displayName => fullName ?? email.split('@').first;
  String get roleLabel {
    switch (role) {
      case 'officer': return 'Enforcement Officer';
      case 'admin': return 'Administrator';
      case 'seller': return 'Seller';
      default: return 'Consumer';
    }
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'full_name': fullName,
    'role': role,
    'region': region,
    'is_active': isActive,
  };
}
