[app]

# Judul dan Identitas Aplikasi
title = Kasir Warung POS
package.name = kasirwarungpos
package.domain = org.warung.pos

# Direktori dan Ekstensi File
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# Library murni Python (tanpa duplikasi resep 'android')
requirements = python3,kivy==2.3.0,pyjnius

# Orientasi Layar
orientation = portrait
fullscreen = 0

# Izin Android (Bluetooth Thermal, Lokasi Scan BT, dan Penyimpanan PDF)
android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Konfigurasi SDK & NDK Stabil
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True

# Arsitektur ARM64 (kompatibel untuk semua HP Android modern & build lebih cepat)
android.archs = arm64-v8a

# Gunakan branch master python-for-android agar bebas error patch/URL
p4a.branch = master

# Izinkan backup data aplikasi
android.allow_backup = True

[buildozer]

# Tingkat detail log saat build (2 = lengkap untuk diagnosa)
log_level = 2
warn_on_root = 1
