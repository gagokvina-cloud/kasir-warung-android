[app]
title = Kasir Warung POS
package.name = kasirwarungpos
package.domain = org.warung.pos
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# Tambahkan 'android' agar modul android.permissions ter-compile tanpa error
requirements = python3,kivy==2.3.0,pyjnius,android

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.archs = arm64-v8a

# Gunakan versi python-for-android yang stabil untuk Kivy 2.3.0
p4a.branch = release-2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
