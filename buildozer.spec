[app]
title = MOSS AI
package.name = mossai
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0
requirements = python3,kivy,requests,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 34
android.minapi = 21
android.ndk = 25b
android.sdk = 34
android.build_tools = 34.0.0
android.arch = arm64-v8a
p4a.accept_sdk_license = True
p4a.branch = develop
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
