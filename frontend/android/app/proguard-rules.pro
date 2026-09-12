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

# Google Play Core (Flutter deferred components) — suppress R8 missing class errors.
# These classes are only needed for Play Store dynamic feature delivery,
# which this app does not use. Safe to ignore.
-dontwarn com.google.android.play.core.**
-keep class com.google.android.play.core.** { *; }

# Google ML Kit Text Recognition
-keep class com.google.mlkit.** { *; }
-keep class com.google.android.gms.vision.** { *; }
-keep class com.google.android.gms.internal.mlkit_vision_text_common.** { *; }
-dontwarn com.google.mlkit.**
-dontwarn com.google.android.gms.**

