[app]
title = Kasir Warung POS
package.name = kasirwarungpos
package.domain = org.warung.pos
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# Library murni Python yang kompatibel 100% dengan Android
requirements = python3,kivy==2.3.0,pyjnius

# Orientasi layar HP
orientation = portrait
fullscreen = 0

# Izin Android (Bluetooth, Lokasi untuk Scan BT, dan Penyimpanan PDF)
android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Target SDK Android modern
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1