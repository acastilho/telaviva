[app]

title = TelaViva Recorder
package.name = recorder
package.domain = com.telaviva
version = 0.1.0

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas
source.exclude_dirs = .git,.buildozer,bin

requirements = python3,kivy,pyjnius,android

orientation = portrait
fullscreen = 0

# MediaProjection + microphone recording while the UI is in another app.
android.permissions = android.permission.RECORD_AUDIO,android.permission.WAKE_LOCK,android.permission.FOREGROUND_SERVICE,android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION,android.permission.FOREGROUND_SERVICE_MICROPHONE

# Android 14+ requires the foreground service type before getMediaProjection().
services = recorder:services/recorder.py:foreground:foregroundServiceType=mediaProjection|microphone

android.add_src = %(source.dir)s/android_src
android.api = 35
android.minapi = 29
android.archs = arm64-v8a
android.accept_sdk_license = True

# Keep MediaProjection alive while ChatGPT is in the foreground.
android.wakelock = True

[buildozer]
log_level = 2
warn_on_root = 1
