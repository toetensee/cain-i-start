[app]
title = Can I Start?
package.name = canistart
package.domain = org.larsschmeling
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.1.0

requirements = python3==3.11.17,hostpython3==3.11.17,kivy==2.3.0,plyer,kivy_garden.mapview,requests,openssl

orientation = portrait
fullscreen = 0

# Android / Buildozer
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION
android.api = 35
android.minapi = 28
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
