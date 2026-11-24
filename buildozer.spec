[app]

title = Kasir Warung POS
package.name = kasirwarungpos
package.domain = org.warung.pos

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# Kunci python3 dan hostpython3 ke versi yang sama persis (3.11.5)
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
