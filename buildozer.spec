[app]
title = MOSS AI
package.name = mossai
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0
requirements = python3,kivy==2.2.1,requests,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.arch = arm64-v8a
p4a.branch = develop
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1