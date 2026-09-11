# LabelSure — ProGuard / R8 rules
# Flutter and most of its plugins already ship with their own consumer rules.
# Add project-specific keep rules here if you encounter ClassNotFoundException
# or similar issues after enabling minifyEnabled.

# Flutter engine — do not obfuscate
-keep class io.flutter.** { *; }
-keep class io.flutter.embedding.** { *; }

# Kotlin standard library
-dontwarn kotlin.**
-keep class kotlin.** { *; }

# Dio / OkHttp networking
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class com.squareup.okhttp3.** { *; }

# Gson / JSON (if used by any dependency)
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn sun.misc.**

# flutter_secure_storage (uses Android KeyStore)
-keep class androidx.security.crypto.** { *; }

# image_picker
-keep class io.flutter.plugins.imagepicker.** { *; }

# Prevent stripping R class (needed for some plugins)
-keepclassmembers class **.R$* {
    public static <fields>;
}
