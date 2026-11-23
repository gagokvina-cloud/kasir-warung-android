# main.py - Aplikasi Kasir Warung Android (Kivy)
# Pure Python (Requirements: python3,kivy==2.3.0,pyjnius)

import os
import json
import copy
import socket
import urllib.parse
import webbrowser
import datetime

from kivy.app import App
from kivy.utils import platform, get_color_from_hex
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup

# Native Android Bluetooth & Build SDK API
ANDROID_BT_AVAILABLE = False
ANDROID_SDK_INT = 0
if platform == "android":
    try:
        from jnius import autoclass
        from android.permissions import request_permissions, Permission
        BuildVersion = autoclass("android.os.Build$VERSION")
        ANDROID_SDK_INT = int(BuildVersion.SDK_INT)
        BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
        UUID = autoclass("java.util.UUID")
        ANDROID_BT_AVAILABLE = True
    except Exception:
        ANDROID_BT_AVAILABLE = False

# Warna Tema
C_PRIMARY = get_color_from_hex("#2c3e50")
C_AKSEN = get_color_from_hex("#3498db")
C_SUKSES = get_color_from_hex("#27ae60")
C_BATAL = get_color_from_hex("#e74c3c")
C_WARNING = get_color_from_hex("#f39c12")
C_ORANGE = get_color_from_hex("#e67e22")
C_WA = get_color_from_hex("#128C7E")
C_PURPLE = get_color_from_hex("#8e44ad")
C_WHITE = (1, 1, 1, 1)

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

DATA_AWAL = {
    "users": {
        "owner": {"password": "owner", "role": "owner", "nama": "Owner Warung"},
        "coba": {"password": "1234", "role": "kasir", "nama": "Kasir Coba"}
    },
    "menu": {
        "1": {"nama": "Nasi Liwet Solo", "harga": 20000, "hpp": 8000, "stok": 30, "kategori": "Makanan"},
        "2": {"nama": "Pempek Palembang", "harga": 25000, "hpp": 10000, "stok": 25, "kategori": "Makanan"},
        "3": {"nama": "Nasi Pecel", "harga": 15000, "hpp": 6000, "stok": 30, "kategori": "Makanan"},
        "4": {"nama": "Es Teh Manis", "harga": 5000, "hpp": 1500, "stok": 50, "kategori": "Minuman"},
        "5": {"nama": "Es Jeruk", "harga": 7000, "hpp": 2000, "stok": 40, "kategori": "Minuman"}
    },
    "customers": {},
    "kategori_menu": ["Makanan", "Minuman", "Snack", "Cemilan"],
    "posisi_duduk": [
        "Take-Away", "Deretan Depan", "Tengah Depan Bar",
        "Depan Band", "Seberang Tenan", "Belakang", "Lesehan"
    ],
    "riwayat_transaksi": [],
    "riwayat_kasir": [],
    "pesanan_belum_bayar": [],
    "profil_toko": {
        "nama": "NASI LIWET PONDOK JATI",
        "alamat": "Jl. Raya Pondok Jati No. 123",
        "kota": "Sidoarjo",
        "telepon": "0812-3456-7890",
        "footer": "Terima Kasih Atas Kunjungan Anda"
    },
    "biaya_operasional": {
        "sewa": 0, "listrik": 0, "air": 0, "gas": 0,
        "karyawan": 0, "transportasi": 0, "lainnya": 0
    },
    "diskon_karyawan_default": 10,
    "pengaturan_printer": {
        "bluetooth_name": "",
        "bluetooth_mac": "",
        "bluetooth_channel": 1,
        "lebar_struk": 32,
        "cutting_paper": True,
        "cashdrawer": False
    }
}


def get_storage_dir():
    """Mendapatkan direktori penyimpanan internal aplikasi yang aman di semua versi Android"""
    app = App.get_running_app()
    if app and hasattr(app, "user_data_dir") and app.user_data_dir:
        os.makedirs(app.user_data_dir, exist_ok=True)
        return app.user_data_dir
    return os.getcwd()


def simpan_teks_ke_pdf_murni(teks_laporan, path_output):
    """Generator PDF 1.4 standar murni Python tanpa library eksternal"""
    lines = teks_laporan.splitlines()
    per_halaman = 48
    halaman_list = [lines[i:i + per_halaman] for i in range(0, max(1, len(lines)), per_halaman)]

    objects = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    page_obj_nums = []
    next_obj = 4
    page_entries = []

    for hal in halaman_list:
        page_num = next_obj
        content_num = next_obj + 1
        next_obj += 2
        page_obj_nums.append(page_num)

        stream_cmds = ["BT", "/F1 10 Tf", "40 790 Td", "14 TL"]
        for idx, baris in enumerate(hal):
            aman = baris.encode("latin-1", errors="replace").decode("latin-1")
            aman = aman.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if idx == 0:
                stream_cmds.append(f"({aman}) Tj")
            else:
                stream_cmds.append(f"T* ({aman}) Tj")
        stream_cmds.append("ET")
        stream_data = "\n".join(stream_cmds)

        page_entries.append((
            page_num,
            f"{page_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>\nendobj\n",
            content_num,
            f"{content_num} 0 obj\n<< /Length {len(stream_data)} >>\nstream\n{stream_data}\nendstream\nendobj\n"
        ))

    kids_str = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_nums)} >>\nendobj\n")
    objects.append("3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

    for _, p_str, _, c_str in page_entries:
        objects.append(p_str)
        objects.append(c_str)

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_str in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(obj_str.encode("latin-1"))

    xref_pos = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf_bytes.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    pdf_bytes.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )

    with open(path_output, "wb") as f:
        f.write(pdf_bytes)


def normalisasi_no_wa(nomor):
    digits = "".join(ch for ch in str(nomor) if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("0"):
        return "62" + digits[1:]
    if digits.startswith("8"):
        return "62" + digits
    return digits


def kirim_struk_whatsapp(no_wa, teks_struk):
    wa_num = normalisasi_no_wa(no_wa)
    if not wa_num:
        tampilkan_pesan("No. WA Kosong", "Masukkan No. WhatsApp customer terlebih dahulu!")
        return
    encoded = urllib.parse.quote(teks_struk)
    url = f"https://wa.me/{wa_num}?text={encoded}"
    try:
        webbrowser.open(url)
    except Exception as e:
        tampilkan_pesan("Gagal Membuka WA", f"Pastikan WhatsApp terinstal di HP Anda:\n{e}")


def catat_audit(role, username, aksi, detail=""):
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    baris = f"[{waktu}] [{role}/{username}] {aksi}: {detail}\n" if detail else f"[{waktu}] [{role}/{username}] {aksi}\n"
    try:
        path_audit = os.path.join(get_storage_dir(), "audit_role.log")
        with open(path_audit, "a", encoding="utf-8") as f:
            f.write(baris)
    except Exception:
        pass


def tampilkan_pesan(judul, pesan):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    scroll = ScrollView(size_hint=(1, 1))
    lbl = Label(
        text=pesan,
        size_hint_y=None,
        halign="left",
        valign="top",
        color=C_WHITE,
        font_size=dp(14)
    )
    lbl.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
    lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
    scroll.add_widget(lbl)
    box.add_widget(scroll)

    btn = Button(text="OK", size_hint_y=None, height=dp(42), background_color=C_AKSEN, bold=True)
    popup = Popup(title=judul, content=box, size_hint=(0.88, 0.55))
    btn.bind(on_release=popup.dismiss)
    box.add_widget(btn)
    popup.open()


class BluetoothPrinterManager:
    def __init__(self):
        self.bt_socket = None
        self.out_stream = None
        self.connected_mac = None

    def minta_izin(self):
        if platform == "android" and ANDROID_BT_AVAILABLE:
            try:
                if ANDROID_SDK_INT >= 31:
                    request_permissions([
                        "android.permission.BLUETOOTH_CONNECT",
                        "android.permission.BLUETOOTH_SCAN",
                        Permission.ACCESS_FINE_LOCATION
                    ])
                else:
                    request_permissions([
                        Permission.BLUETOOTH,
                        Permission.BLUETOOTH_ADMIN,
                        Permission.ACCESS_FINE_LOCATION,
                        Permission.WRITE_EXTERNAL_STORAGE,
                        Permission.READ_EXTERNAL_STORAGE
                    ])
            except Exception:
                pass

    def scan_paired_devices(self):
        devices = []
        if platform == "android" and ANDROID_BT_AVAILABLE:
            try:
                adapter = BluetoothAdapter.getDefaultAdapter()
                if adapter is None or not adapter.isEnabled():
                    return []
                paired = adapter.getBondedDevices().toArray()
                for dev in paired:
                    nama = dev.getName() or "Printer BT"
                    mac = dev.getAddress()
                    devices.append((nama, mac))
            except Exception:
                pass
        return devices

    def is_connected(self):
        if self.bt_socket is not None:
            try:
                if hasattr(self.bt_socket, "isConnected"):
                    return self.bt_socket.isConnected()
                return True
            except Exception:
                return False
        return False

    def disconnect(self):
        try:
            if self.out_stream:
                self.out_stream.close()
            if self.bt_socket:
                self.bt_socket.close()
        except Exception:
            pass
        self.out_stream = None
        self.bt_socket = None
        self.connected_mac = None

    def connect(self, mac, channel=1):
        if not mac:
            return False, "MAC Address printer belum dipilih."
        if self.is_connected() and self.connected_mac == mac:
            return True, "Sudah terhubung"
        self.disconnect()

        if platform == "android" and ANDROID_BT_AVAILABLE:
            try:
                adapter = BluetoothAdapter.getDefaultAdapter()
                if adapter is None:
                    return False, "Perangkat tidak mendukung Bluetooth."
                if not adapter.isEnabled():
                    return False, "Bluetooth HP mati! Nyalakan Bluetooth terlebih dahulu."

                adapter.cancelDiscovery()
                device = adapter.getRemoteDevice(mac)
                uuid_obj = UUID.fromString(SPP_UUID)
                try:
                    sock = device.createRfcommSocketToServiceRecord(uuid_obj)
                    sock.connect()
                except Exception:
                    create_method = device.getClass().getMethod("createRfcommSocket", autoclass("java.lang.Integer").TYPE)
                    sock = create_method.invoke(device, int(channel))
                    sock.connect()

                self.bt_socket = sock
                self.out_stream = sock.getOutputStream()
                self.connected_mac = mac
                return True, f"Terhubung ke {device.getName() or mac}"
            except Exception as e:
                self.disconnect()
                return False, f"Gagal koneksi Bluetooth Android: {e}"

        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.settimeout(8)
            sock.connect((mac, int(channel)))
            self.bt_socket = sock
            self.connected_mac = mac
            return True, f"Terhubung ke {mac}"
        except Exception as e:
            self.disconnect()
            return False, f"Gagal koneksi socket: {e}"

    def kirim_data(self, teks, mac, channel=1, cutting=True, cashdrawer=False):
        ok, msg = self.connect(mac, channel)
        if not ok:
            return False, msg

        try:
            payload = bytearray()
            payload.extend(b"\x1B\x40")
            for line in teks.split("\n"):
                payload.extend((line + "\n").encode("utf-8", errors="replace"))
            if cutting:
                payload.extend(b"\n\n\x1D\x56\x00")
            if cashdrawer:
                payload.extend(b"\x1B\x70\x00\x19\xFA")

            if platform == "android" and self.out_stream is not None:
                self.out_stream.write(bytes(payload))
                self.out_stream.flush()
            else:
                self.bt_socket.send(bytes(payload))
            return True, "Berhasil dicetak!"
        except Exception as e:
            self.disconnect()
            return False, f"Koneksi terputus: {e}"


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))

        header = BoxLayout(orientation="vertical", size_hint_y=0.25)
        self.lbl_nama_warung = Label(text="NASI LIWET PONDOK JATI", font_size=dp(22), bold=True, color=C_WHITE)
        header.add_widget(self.lbl_nama_warung)
        header.add_widget(Label(text="Sistem Kasir Android (Multi-Role)", font_size=dp(14), color=(0.8, 0.8, 0.8, 1)))
        root.add_widget(header)

        form = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=0.6)
        self.inp_user = TextInput(hint_text="Username (cth: owner / coba)", multiline=False, font_size=dp(16), size_hint_y=None, height=dp(46))
        self.inp_pass = TextInput(hint_text="Password", password=True, multiline=False, font_size=dp(16), size_hint_y=None, height=dp(46))
        self.inp_modal = TextInput(hint_text="Modal Awal Kas (Rp)", text="500000", input_filter="int", multiline=False, font_size=dp(16), size_hint_y=None, height=dp(46))

        form.add_widget(Label(text="Username:", size_hint_y=None, height=dp(22), halign="left"))
        form.add_widget(self.inp_user)
        form.add_widget(Label(text="Password:", size_hint_y=None, height=dp(22), halign="left"))
        form.add_widget(self.inp_pass)
        form.add_widget(Label(text="Modal Awal (Shift Baru):", size_hint_y=None, height=dp(22), halign="left"))
        form.add_widget(self.inp_modal)

        btn_login = Button(text="LOGIN MASUK", size_hint_y=None, height=dp(50), background_color=C_SUKSES, bold=True, font_size=dp(16))
        btn_login.bind(on_release=self.proses_login)
        form.add_widget(btn_login)

        btn_ganti_pw = Button(text="Ganti Password", size_hint_y=None, height=dp(40), background_color=C_WARNING, font_size=dp(14))
        btn_ganti_pw.bind(on_release=self.dialog_ganti_password)
        form.add_widget(btn_ganti_pw)

        root.add_widget(form)
        root.add_widget(Label(text="Default -> owner/owner | coba/1234", font_size=dp(12), size_hint_y=0.1, color=(0.7, 0.7, 0.7, 1)))
        self.add_widget(root)

    def on_pre_enter(self):
        app = App.get_running_app()
        if app and hasattr(app, "db"):
            self.lbl_nama_warung.text = app.db["profil_toko"].get("nama", "WARUNG")

    def proses_login(self, *args):
        app = App.get_running_app()
        uname = self.inp_user.text.strip()
        pwd = self.inp_pass.text.strip()

        if not uname or not pwd:
            tampilkan_pesan("Peringatan", "Username dan Password wajib diisi!")
            return

        users = app.db.get("users", {})
        if uname not in users:
            catat_audit("unknown", uname, "LOGIN_FAIL", f"user tidak ditemukan: {uname}")
            tampilkan_pesan("Login Gagal", "Username tidak terdaftar!")
            return

        user_data = users[uname]
        role = user_data.get("role", "kasir")

        if user_data.get("password") != pwd:
            catat_audit(role, uname, "LOGIN_FAIL", f"password salah: {uname}")
            tampilkan_pesan("Login Gagal", "Password salah!")
            return

        try:
            modal = int(self.inp_modal.text.strip() or 0)
        except ValueError:
            modal = 0

        app.user_aktif = uname
        app.role_aktif = role
        app.modal_awal = modal
        app.saldo_kas += modal

        app.db["riwayat_kasir"].append({
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "nama": uname,
            "role": role,
            "modal_awal": modal,
            "saldo_kas": app.saldo_kas,
            "status": "Mulai Shift"
        })
        app.simpan_database()
        catat_audit(role, uname, "LOGIN_OK", f"role={role}")

        mac = app.db["pengaturan_printer"].get("bluetooth_mac", "")
        if mac:
            app.bt_manager.connect(mac, app.db["pengaturan_printer"].get("bluetooth_channel", 1))

        self.inp_pass.text = ""
        app.root.current = "main"
        app.main_screen.on_enter_session()

    def dialog_ganti_password(self, *args):
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        u_in = TextInput(hint_text="Username", multiline=False, size_hint_y=None, height=dp(42))
        old_in = TextInput(hint_text="Password Lama", password=True, multiline=False, size_hint_y=None, height=dp(42))
        new_in = TextInput(hint_text="Password Baru", password=True, multiline=False, size_hint_y=None, height=dp(42))
        box.add_widget(u_in)
        box.add_widget(old_in)
        box.add_widget(new_in)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_ok = Button(text="Simpan", background_color=C_SUKSES, bold=True)
        btn_batal = Button(text="Batal", background_color=C_BATAL)
        btn_row.add_widget(btn_ok)
        btn_row.add_widget(btn_batal)
        box.add_widget(btn_row)

        popup = Popup(title="Ganti Password", content=box, size_hint=(0.88, 0.52))
        btn_batal.bind(on_release=popup.dismiss)

        def simpan(*_):
            u = u_in.text.strip()
            old_p = old_in.text.strip()
            new_p = new_in.text.strip()
            users = app.db.get("users", {})
            if u not in users or users[u]["password"] != old_p:
                tampilkan_pesan("Error", "Username atau password lama salah!")
                return
            if not new_p:
                tampilkan_pesan("Error", "Password baru tidak boleh kosong!")
                return
            users[u]["password"] = new_p
            app.simpan_database()
            catat_audit(users[u]["role"], u, "PASSWORD_CHANGE", f"user={u}")
            popup.dismiss()
            tampilkan_pesan("Sukses", f"Password untuk '{u}' berhasil diperbarui!")

        btn_ok.bind(on_release=simpan)
        popup.open()


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.keranjang = []
        self.meja_val = 0
        self.kategori_aktif = "Semua"
        self.idx_pesanan_ditemukan = -1
        self.paired_map = {}

        self.layout_utama = BoxLayout(orientation="vertical")

        # Banner Nama Warung Real-Time
        self.lbl_banner_warung = Label(
            text="NASI LIWET PONDOK JATI",
            size_hint_y=None,
            height=dp(34),
            bold=True,
            font_size=dp(17),
            color=(1, 0.9, 0.3, 1)
        )
        self.layout_utama.add_widget(self.lbl_banner_warung)

        # Top Bar Info Kasir & Status Bluetooth
        self.topbar = BoxLayout(size_hint_y=None, height=dp(42), padding=[dp(8), dp(2)], spacing=dp(6))
        self.lbl_status = Label(text="Kasir: -", bold=True, font_size=dp(12), halign="left")
        self.lbl_bt_badge = Label(text="BT: Offline", bold=True, font_size=dp(11), color=(1, 0.4, 0.4, 1))
        btn_logout = Button(text="Logout", size_hint_x=None, width=dp(68), background_color=C_BATAL, font_size=dp(12), bold=True)
        btn_logout.bind(on_release=self.logout_user)
        self.topbar.add_widget(self.lbl_status)
        self.topbar.add_widget(self.lbl_bt_badge)
        self.topbar.add_widget(btn_logout)
        self.layout_utama.add_widget(self.topbar)

        # Navigasi Menu Horizontal
        nav_scroll = ScrollView(size_hint_y=None, height=dp(44), do_scroll_y=False)
        self.nav_bar = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(4), padding=[dp(4), dp(2)])
        self.nav_bar.bind(minimum_width=self.nav_bar.setter("width"))
        nav_scroll.add_widget(self.nav_bar)
        self.layout_utama.add_widget(nav_scroll)

        # Area Konten Dinamis
        self.area_konten = BoxLayout(orientation="vertical", padding=dp(6))
        self.layout_utama.add_widget(self.area_konten)

        self.add_widget(self.layout_utama)

    def refresh_nama_warung_display(self):
        app = App.get_running_app()
        nama_baru = app.db["profil_toko"].get("nama", "WARUNG")
        self.lbl_banner_warung.text = nama_baru.upper()
        app.login_screen.lbl_nama_warung.text = nama_baru.upper()
        app.title = nama_baru

    def update_bt_badge(self):
        app = App.get_running_app()
        cfg = app.db["pengaturan_printer"]
        if app.bt_manager.is_connected():
            nama = cfg.get("bluetooth_name") or cfg.get("bluetooth_mac")
            self.lbl_bt_badge.text = f"BT: {nama[:12]}"
            self.lbl_bt_badge.color = (0.3, 1, 0.4, 1)
        elif cfg.get("bluetooth_mac"):
            self.lbl_bt_badge.text = "BT: Siap (Auto)"
            self.lbl_bt_badge.color = (1, 0.85, 0.2, 1)
        else:
            self.lbl_bt_badge.text = "BT: Belum Set"
            self.lbl_bt_badge.color = (1, 0.4, 0.4, 1)

    def on_enter_session(self):
        app = App.get_running_app()
        self.refresh_nama_warung_display()
        self.lbl_status.text = f"{app.user_aktif} ({app.role_aktif.upper()}) | Rp {app.saldo_kas:,}"
        self.update_bt_badge()
        self.bangun_navigasi()
        self.tampilkan_kasir(buka_popup_menu=True)

    def bangun_navigasi(self):
        app = App.get_running_app()
        self.nav_bar.clear_widgets()

        menus = [
            ("Kasir", lambda: self.tampilkan_kasir(buka_popup_menu=True)),
            ("Pelanggan", self.tampilkan_pelanggan),
            ("Printer BT", self.tampilkan_printer)
        ]
        if app.role_aktif == "owner":
            menus.extend([
                ("Profil Warung", self.tampilkan_profil_warung),
                ("Edit Menu", self.tampilkan_edit_menu),
                ("Biaya Ops", self.tampilkan_promosi_ops),
                ("Laporan", lambda: self.tampilkan_laporan(buka_popup_periode=True)),
                ("User & Role", self.tampilkan_manajemen_user)
            ])

        for label, callback in menus:
            btn = Button(text=label, size_hint_x=None, width=dp(110), background_color=C_AKSEN, font_size=dp(13), bold=True)
            btn.bind(on_release=lambda inst, cb=callback: cb())
            self.nav_bar.add_widget(btn)

    def logout_user(self, *args):
        app = App.get_running_app()
        app.bt_manager.disconnect()
        catat_audit(app.role_aktif, app.user_aktif, "LOGOUT", f"saldo_akhir={app.saldo_kas}")
        app.db["riwayat_kasir"].append({
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "nama": app.user_aktif,
            "role": app.role_aktif,
            "saldo_akhir": app.saldo_kas,
            "status": "Logout"
        })
        app.user_aktif = None
        app.role_aktif = None
        app.simpan_database()
        app.root.current = "login"

    # ===================== 1. HALAMAN KASIR & POP-UP MENU =====================
    def tampilkan_kasir(self, buka_popup_menu=False):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        main_scroll = ScrollView()
        container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7), padding=dp(4))
        container.bind(minimum_height=container.setter("height"))

        # Data Customer (Nama & No WA) + Pilih dari DB
        row_cust = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        self.inp_cust_nama = TextInput(hint_text="Nama Customer (opsional)", multiline=False, font_size=dp(13))
        self.inp_cust_wa = TextInput(hint_text="No. WA (08xx)", input_filter="int", multiline=False, font_size=dp(13))
        btn_pilih_cust = Button(text="DB WA", size_hint_x=None, width=dp(62), background_color=C_WA, bold=True, font_size=dp(12))
        btn_pilih_cust.bind(on_release=self.dialog_pilih_customer)
        row_cust.add_widget(self.inp_cust_nama)
        row_cust.add_widget(self.inp_cust_wa)
        row_cust.add_widget(btn_pilih_cust)
        container.add_widget(row_cust)

        # Pesanan Belum Bayar
        row_psn = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        self.inp_cari_psn = TextInput(hint_text="Cari nama pesanan pending...", multiline=False, font_size=dp(13))
        btn_cari_psn = Button(text="Muat", size_hint_x=None, width=dp(58), background_color=C_AKSEN, font_size=dp(12))
        btn_cari_psn.bind(on_release=self.muat_pesanan_pending)
        btn_list_psn = Button(text=f"Pending ({len(app.db['pesanan_belum_bayar'])})", size_hint_x=None, width=dp(92), background_color=C_ORANGE, font_size=dp(12))
        btn_list_psn.bind(on_release=self.lihat_semua_pending)
        row_psn.add_widget(self.inp_cari_psn)
        row_psn.add_widget(btn_cari_psn)
        row_psn.add_widget(btn_list_psn)
        container.add_widget(row_psn)

        # Meja & Posisi
        row_meja = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        btn_min_meja = Button(text="-", size_hint_x=None, width=dp(36), background_color=C_WARNING, bold=True)
        self.lbl_meja = Label(text=f"Meja: {self.meja_val}", size_hint_x=None, width=dp(72), bold=True)
        btn_plus_meja = Button(text="+", size_hint_x=None, width=dp(36), background_color=C_SUKSES, bold=True)
        btn_min_meja.bind(on_release=lambda *_: self.ubah_meja(-1))
        btn_plus_meja.bind(on_release=lambda *_: self.ubah_meja(1))

        self.spn_posisi = Spinner(text=app.db["posisi_duduk"][0], values=app.db["posisi_duduk"], font_size=dp(13))
        row_meja.add_widget(btn_min_meja)
        row_meja.add_widget(self.lbl_meja)
        row_meja.add_widget(btn_plus_meja)
        row_meja.add_widget(self.spn_posisi)
        container.add_widget(row_meja)

        # Tombol Buka Pop-Up Daftar Menu
        btn_buka_menu = Button(
            text="+ PILIH MENU / TAMBAH ITEM (POP-UP MENU)",
            size_hint_y=None,
            height=dp(46),
            background_color=C_PRIMARY,
            bold=True,
            font_size=dp(14)
        )
        btn_buka_menu.bind(on_release=lambda *_: self.popup_pilih_menu())
        container.add_widget(btn_buka_menu)

        # Keranjang
        container.add_widget(Label(text="KERANJANG BELANJA", bold=True, size_hint_y=None, height=dp(26), font_size=dp(14)))
        self.box_keranjang = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.box_keranjang.bind(minimum_height=self.box_keranjang.setter("height"))
        container.add_widget(self.box_keranjang)

        # Diskon
        row_disk = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.inp_diskon = TextInput(hint_text="Diskon Manual (Rp)", text="0", input_filter="int", multiline=False, font_size=dp(13))
        self.inp_diskon.bind(text=lambda *_: self.hitung_total())
        self.chk_karyawan = CheckBox(size_hint_x=None, width=dp(36))
        self.chk_karyawan.bind(active=lambda *_: self.hitung_total())
        row_disk.add_widget(self.inp_diskon)
        row_disk.add_widget(self.chk_karyawan)
        row_disk.add_widget(Label(text=f"Karyawan ({app.db['diskon_karyawan_default']}%)", size_hint_x=None, width=dp(120), font_size=dp(12)))
        container.add_widget(row_disk)

        # Display Total
        self.lbl_total = Label(text="TOTAL: Rp 0", font_size=dp(19), bold=True, color=(0.2, 0.9, 0.4, 1), size_hint_y=None, height=dp(38))
        container.add_widget(self.lbl_total)

        # Tombol Aksi Utama (BAYAR memunculkan pop-up pilihan Tunai / QRIS)
        row_aksi = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        btn_bayar = Button(text="BAYAR", background_color=C_SUKSES, bold=True, font_size=dp(14))
        btn_bayar.bind(on_release=self.buka_popup_pembayaran)
        btn_prev = Button(text="PREVIEW", size_hint_x=None, width=dp(76), background_color=C_AKSEN, bold=True, font_size=dp(12))
        btn_prev.bind(on_release=self.preview_keranjang_sekarang)
        btn_simpan_psn = Button(text="PENDING", size_hint_x=None, width=dp(76), background_color=C_ORANGE, bold=True, font_size=dp(12))
        btn_simpan_psn.bind(on_release=self.simpan_pending)
        btn_reset = Button(text="RESET", size_hint_x=None, width=dp(62), background_color=C_BATAL, font_size=dp(12))
        btn_reset.bind(on_release=lambda *_: self.reset_transaksi())

        row_aksi.add_widget(btn_bayar)
        row_aksi.add_widget(btn_prev)
        row_aksi.add_widget(btn_simpan_psn)
        row_aksi.add_widget(btn_reset)
        container.add_widget(row_aksi)

        main_scroll.add_widget(container)
        self.area_konten.add_widget(main_scroll)
        self.refresh_keranjang()

        if buka_popup_menu:
            self.popup_pilih_menu()

    def popup_pilih_menu(self):
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        lbl_info_cart = Label(
            text=self._ringkasan_keranjang_teks(),
            size_hint_y=None,
            height=dp(28),
            bold=True,
            font_size=dp(13),
            color=(0.3, 1, 0.5, 1)
        )
        box.add_widget(lbl_info_cart)

        row_kat = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        row_kat.add_widget(Label(text="Kategori:", size_hint_x=None, width=dp(72), font_size=dp(13)))
        kat_list = ["Semua"] + app.db.get("kategori_menu", ["Makanan", "Minuman"])
        if self.kategori_aktif not in kat_list:
            self.kategori_aktif = "Semua"
        spn_kat_pop = Spinner(text=self.kategori_aktif, values=kat_list, font_size=dp(13))
        row_kat.add_widget(spn_kat_pop)
        box.add_widget(row_kat)

        scroll_menu = ScrollView()
        grid_pop = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        grid_pop.bind(minimum_height=grid_pop.setter("height"))
        scroll_menu.add_widget(grid_pop)
        box.add_widget(scroll_menu)

        def render_menu_pop(kat_filter):
            grid_pop.clear_widgets()
            for kode, item in app.db["menu"].items():
                if kat_filter != "Semua" and item.get("kategori") != kat_filter:
                    continue
                stok = int(item.get("stok", 0))
                qty_pilih = sum(i["jumlah"] for i in self.keranjang if i.get("kode") == kode or i["nama"] == item["nama"])
                warna_btn = C_PRIMARY if stok > 0 else C_BATAL
                tanda_qty = f" [+{qty_pilih}]" if qty_pilih > 0 else ""
                btn = Button(
                    text=f"{item['nama']}{tanda_qty}\nRp {item['harga']:,} | Stok: {stok}",
                    size_hint_y=None,
                    height=dp(62),
                    background_color=warna_btn,
                    font_size=dp(12),
                    halign="center"
                )
                def klik_item(inst, k=kode):
                    self.tambah_item(k)
                    lbl_info_cart.text = self._ringkasan_keranjang_teks()
                    render_menu_pop(spn_kat_pop.text)

                btn.bind(on_release=klik_item)
                grid_pop.add_widget(btn)

        def ubah_kat_pop(spinner, text):
            self.kategori_aktif = text
            render_menu_pop(text)

        spn_kat_pop.bind(text=ubah_kat_pop)
        render_menu_pop(self.kategori_aktif)

        popup = Popup(title="Daftar Menu Warung", content=box, size_hint=(0.94, 0.85))
        btn_selesai = Button(text="SELESAI PILIH MENU", size_hint_y=None, height=dp(44), background_color=C_SUKSES, bold=True, font_size=dp(14))
        btn_selesai.bind(on_release=popup.dismiss)
        box.add_widget(btn_selesai)
        popup.open()

    def _ringkasan_keranjang_teks(self):
        tot_qty = sum(i["jumlah"] for i in self.keranjang)
        tot_rp = sum(i["subtotal"] for i in self.keranjang)
        return f"Dipilih: {tot_qty} item | Subtotal: Rp {tot_rp:,}"

    # ===================== POP-UP PEMBAYARAN (TUNAI & QRIS) =====================
    def buka_popup_pembayaran(self, *args):
        if not self.keranjang:
            tampilkan_pesan("Peringatan", "Keranjang belanja masih kosong! Silakan pilih menu terlebih dahulu.")
            return

        app = App.get_running_app()
        for item in self.keranjang:
            kode = item.get("kode")
            if kode and kode in app.db["menu"]:
                stok_kini = int(app.db["menu"][kode].get("stok", 0))
                if item["jumlah"] > stok_kini:
                    tampilkan_pesan("Stok Tidak Cukup", f"Stok '{item['nama']}' tersisa {stok_kini}, tidak cukup untuk {item['jumlah']} porsi.")
                    return

        _, _, total_akhir = self.hitung_total()

        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
        box.add_widget(Label(
            text=f"TOTAL TAGIHAN\nRp {total_akhir:,}",
            font_size=dp(22),
            bold=True,
            color=(0.2, 0.95, 0.45, 1),
            halign="center",
            size_hint_y=None,
            height=dp(70)
        ))
        box.add_widget(Label(
            text="Pilih Metode Pembayaran:",
            font_size=dp(15),
            size_hint_y=None,
            height=dp(28)
        ))

        row_pilihan = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(10))
        btn_tunai = Button(text="TUNAI (CASH)", background_color=C_SUKSES, bold=True, font_size=dp(16))
        btn_qris = Button(text="QRIS", background_color=C_AKSEN, bold=True, font_size=dp(16))
        row_pilihan.add_widget(btn_tunai)
        row_pilihan.add_widget(btn_qris)
        box.add_widget(row_pilihan)

        btn_batal = Button(text="Batal", size_hint_y=None, height=dp(42), background_color=C_BATAL, font_size=dp(14))
        box.add_widget(btn_batal)

        popup_pilih = Popup(title="Metode Pembayaran", content=box, size_hint=(0.88, 0.48))
        btn_batal.bind(on_release=popup_pilih.dismiss)

        def pilih_tunai(*_):
            popup_pilih.dismiss()
            self.buka_popup_tunai(total_akhir)

        def pilih_qris(*_):
            popup_pilih.dismiss()
            self.buka_popup_qris(total_akhir)

        btn_tunai.bind(on_release=pilih_tunai)
        btn_qris.bind(on_release=pilih_qris)
        popup_pilih.open()

    def buka_popup_tunai(self, total_akhir):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))

        lbl_tagihan = Label(
            text=f"HARUS DIBAYAR:\nRp {total_akhir:,}",
            font_size=dp(21),
            bold=True,
            color=(1, 0.9, 0.3, 1),
            halign="center",
            size_hint_y=None,
            height=dp(64)
        )
        box.add_widget(lbl_tagihan)

        box.add_widget(Label(text="Masukkan Uang Dibayarkan Customer (Rp):", size_hint_y=None, height=dp(24), font_size=dp(13)))
        inp_bayar = TextInput(
            hint_text="Contoh: 50000",
            input_filter="int",
            multiline=False,
            font_size=dp(20),
            size_hint_y=None,
            height=dp(50)
        )
        box.add_widget(inp_bayar)

        row_quick = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(5))
        for nom_label, nom_val in [("Uang Pas", total_akhir), ("50.000", 50000), ("100.000", 100000)]:
            b_q = Button(text=nom_label, background_color=C_PRIMARY, font_size=dp(12), bold=True)
            b_q.bind(on_release=lambda inst, v=nom_val: setattr(inp_bayar, "text", str(v)))
            row_quick.add_widget(b_q)
        box.add_widget(row_quick)

        lbl_status_bayar = Label(
            text=f"KURANG BAYAR: Rp {total_akhir:,}",
            font_size=dp(18),
            bold=True,
            color=(1, 0.4, 0.4, 1),
            size_hint_y=None,
            height=dp(44)
        )
        box.add_widget(lbl_status_bayar)

        row_btn = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_cetak = Button(text="PROSES & CETAK STRUK", background_color=C_SUKSES, bold=True, font_size=dp(13), disabled=True)
        btn_batal = Button(text="Batal", size_hint_x=None, width=dp(80), background_color=C_BATAL, font_size=dp(13))
        row_btn.add_widget(btn_cetak)
        row_btn.add_widget(btn_batal)
        box.add_widget(row_btn)

        popup_tunai = Popup(title="Pembayaran Tunai (Cash)", content=box, size_hint=(0.92, 0.65))
        btn_batal.bind(on_release=popup_tunai.dismiss)

        def cek_nominal(instance, text):
            try:
                uang = int(text.strip() or 0)
            except ValueError:
                uang = 0
            selisih = uang - total_akhir
            if selisih >= 0:
                lbl_status_bayar.text = f"KEMBALIAN: Rp {selisih:,}"
                lbl_status_bayar.color = (0.2, 0.95, 0.45, 1)
                btn_cetak.disabled = False
            else:
                lbl_status_bayar.text = f"KURANG BAYAR: Rp {abs(selisih):,}"
                lbl_status_bayar.color = (1, 0.4, 0.4, 1)
                btn_cetak.disabled = True

        inp_bayar.bind(text=cek_nominal)

        def konfirmasi_tunai(*_):
            try:
                uang = int(inp_bayar.text.strip() or 0)
            except ValueError:
                uang = 0
            if uang < total_akhir:
                tampilkan_pesan("Kurang Bayar", f"Uang masih kurang Rp {total_akhir - uang:,}")
                return
            popup_tunai.dismiss()
            self.selesaikan_transaksi(metode="Tunai", bayar=uang)

        btn_cetak.bind(on_release=konfirmasi_tunai)
        popup_tunai.open()

    def buka_popup_qris(self, total_akhir):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))

        lbl_qris = Label(
            text=f"PEMBAYARAN QRIS\n\nNominal yang Harus Dibayar:\nRp {total_akhir:,}",
            font_size=dp(20),
            bold=True,
            color=(0.3, 0.9, 1, 1),
            halign="center",
            size_hint_y=None,
            height=dp(120)
        )
        box.add_widget(lbl_qris)

        lbl_note = Label(
            text="Pastikan customer sudah melakukan scan & pembayaran QRIS sesuai nominal di atas.",
            font_size=dp(13),
            halign="center",
            size_hint_y=None,
            height=dp(44)
        )
        lbl_note.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        box.add_widget(lbl_note)

        row_btn = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        btn_cetak = Button(text="CETAK STRUK QRIS", background_color=C_SUKSES, bold=True, font_size=dp(14))
        btn_batal = Button(text="Batal", size_hint_x=None, width=dp(80), background_color=C_BATAL, font_size=dp(14))
        row_btn.add_widget(btn_cetak)
        row_btn.add_widget(btn_batal)
        box.add_widget(row_btn)

        popup_qris = Popup(title="Pembayaran QRIS", content=box, size_hint=(0.90, 0.55))
        btn_batal.bind(on_release=popup_qris.dismiss)

        def konfirmasi_qris(*_):
            popup_qris.dismiss()
            self.selesaikan_transaksi(metode="QRIS", bayar=total_akhir)

        btn_cetak.bind(on_release=konfirmasi_qris)
        popup_qris.open()

    def selesaikan_transaksi(self, metode, bayar):
        app = App.get_running_app()
        sub, disk, total_akhir = self.hitung_total()
        kembalian = max(0, bayar - total_akhir)

        for item in self.keranjang:
            kode = item.get("kode")
            if kode and kode in app.db["menu"]:
                app.db["menu"][kode]["stok"] = max(0, int(app.db["menu"][kode].get("stok", 0)) - item["jumlah"])

        cust_nama = self.inp_cust_nama.text.strip()
        cust_wa = self.inp_cust_wa.text.strip()
        self.simpan_customer_ke_db(cust_nama, cust_wa)

        if 0 <= self.idx_pesanan_ditemukan < len(app.db["pesanan_belum_bayar"]):
            app.db["pesanan_belum_bayar"].pop(self.idx_pesanan_ditemukan)
            self.idx_pesanan_ditemukan = -1

        data_nota = {
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "meja": str(self.meja_val),
            "posisi": self.spn_posisi.text,
            "customer_nama": cust_nama,
            "customer_wa": cust_wa,
            "keranjang": copy.deepcopy(self.keranjang),
            "total": total_akhir,
            "total_awal": sub,
            "diskon": disk,
            "metode": metode,
            "dibayar": bayar,
            "kembalian": kembalian,
            "kasir": app.user_aktif
        }
        app.db["riwayat_transaksi"].append(data_nota)
        app.saldo_kas += total_akhir
        app.simpan_database()

        self.lbl_status.text = f"{app.user_aktif} ({app.role_aktif.upper()}) | Rp {app.saldo_kas:,}"
        struk = self.format_struk(data_nota)

        cfg = app.db["pengaturan_printer"]
        if cfg.get("bluetooth_mac"):
            self.kirim_bluetooth(struk, silent_success=True)

        self.preview_dan_cetak_struk(struk, no_wa=cust_wa, judul=f"Struk Lunas ({metode})")
        self.reset_transaksi()

    def dialog_pilih_customer(self, *args):
        app = App.get_running_app()
        custs = app.db.get("customers", {})
        if not custs:
            tampilkan_pesan("Database Pelanggan", "Belum ada data pelanggan tersimpan.\nIsi Nama & No. WA saat transaksi untuk menyimpan otomatis.")
            return

        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        scroll = ScrollView()
        lst = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        lst.bind(minimum_height=lst.setter("height"))

        popup = Popup(title="Pilih Customer Tersimpan", content=box, size_hint=(0.88, 0.7))

        for wa_key, info in custs.items():
            btn = Button(
                text=f"{info['nama']} - {info['no_wa']}",
                size_hint_y=None,
                height=dp(42),
                background_color=C_PRIMARY,
                font_size=dp(13)
            )
            def pilih(inst, n=info["nama"], w=info["no_wa"]):
                self.inp_cust_nama.text = n
                self.inp_cust_wa.text = w
                popup.dismiss()
            btn.bind(on_release=pilih)
            lst.add_widget(btn)

        scroll.add_widget(lst)
        box.add_widget(scroll)
        btn_tutup = Button(text="Tutup", size_hint_y=None, height=dp(40), background_color=C_BATAL)
        btn_tutup.bind(on_release=popup.dismiss)
        box.add_widget(btn_tutup)
        popup.open()

    def preview_keranjang_sekarang(self, *args):
        if not self.keranjang:
            tampilkan_pesan("Peringatan", "Keranjang masih kosong!")
            return
        app = App.get_running_app()
        sub, disk, total_akhir = self.hitung_total()
        data_nota = {
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "meja": str(self.meja_val),
            "posisi": self.spn_posisi.text,
            "customer_nama": self.inp_cust_nama.text.strip(),
            "customer_wa": self.inp_cust_wa.text.strip(),
            "keranjang": copy.deepcopy(self.keranjang),
            "total": total_akhir,
            "total_awal": sub,
            "diskon": disk,
            "metode": "Preview",
            "dibayar": total_akhir,
            "kembalian": 0,
            "kasir": app.user_aktif
        }
        self.preview_dan_cetak_struk(self.format_struk(data_nota), no_wa=data_nota["customer_wa"], judul="Preview Struk Transaksi")

    def ubah_meja(self, delta):
        self.meja_val = max(0, min(999, self.meja_val + delta))
        self.lbl_meja.text = f"Meja: {self.meja_val}"

    def tambah_item(self, kode):
        app = App.get_running_app()
        m = app.db["menu"][kode]
        stok_tersedia = int(m.get("stok", 0))

        qty_di_keranjang = 0
        for item in self.keranjang:
            if item.get("kode") == kode or item["nama"] == m["nama"]:
                qty_di_keranjang = item["jumlah"]
                break

        if qty_di_keranjang + 1 > stok_tersedia:
            tampilkan_pesan("Stok Habis / Kurang", f"Stok '{m['nama']}' hanya tersisa {stok_tersedia} porsi.")
            return

        for item in self.keranjang:
            if item.get("kode") == kode or item["nama"] == m["nama"]:
                item["jumlah"] += 1
                item["subtotal"] = item["harga"] * item["jumlah"]
                self.refresh_keranjang()
                return

        self.keranjang.append({
            "kode": kode,
            "nama": m["nama"],
            "harga": m["harga"],
            "hpp": m.get("hpp", 0),
            "jumlah": 1,
            "subtotal": m["harga"],
            "kategori": m.get("kategori", "Makanan")
        })
        self.refresh_keranjang()

    def refresh_keranjang(self):
        self.box_keranjang.clear_widgets()
        if not self.keranjang:
            self.box_keranjang.add_widget(Label(text="Keranjang masih kosong (Klik tombol Pilih Menu di atas)", size_hint_y=None, height=dp(30), font_size=dp(12), color=(0.7, 0.7, 0.7, 1)))
        else:
            for idx, item in enumerate(self.keranjang):
                row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
                row.add_widget(Label(text=f"{item['nama']} x{item['jumlah']}", halign="left", font_size=dp(13)))
                row.add_widget(Label(text=f"Rp {item['subtotal']:,}", size_hint_x=None, width=dp(95), font_size=dp(13)))

                b_min = Button(text="-", size_hint_x=None, width=dp(34), background_color=C_WARNING)
                b_plus = Button(text="+", size_hint_x=None, width=dp(34), background_color=C_SUKSES)
                b_del = Button(text="X", size_hint_x=None, width=dp(34), background_color=C_BATAL)

                b_min.bind(on_release=lambda inst, i=idx: self.ubah_qty(i, -1))
                b_plus.bind(on_release=lambda inst, i=idx: self.ubah_qty(i, 1))
                b_del.bind(on_release=lambda inst, i=idx: self.hapus_item(i))

                row.add_widget(b_min)
                row.add_widget(b_plus)
                row.add_widget(b_del)
                self.box_keranjang.add_widget(row)
        self.hitung_total()

    def ubah_qty(self, idx, delta):
        app = App.get_running_app()
        item = self.keranjang[idx]
        if delta > 0:
            kode = item.get("kode")
            if kode and kode in app.db["menu"]:
                stok_tersedia = int(app.db["menu"][kode].get("stok", 0))
                if item["jumlah"] + 1 > stok_tersedia:
                    tampilkan_pesan("Stok Kurang", f"Stok maksimal untuk '{item['nama']}' adalah {stok_tersedia}.")
                    return

        item["jumlah"] += delta
        if item["jumlah"] <= 0:
            self.keranjang.pop(idx)
        else:
            item["subtotal"] = item["harga"] * item["jumlah"]
        self.refresh_keranjang()

    def hapus_item(self, idx):
        self.keranjang.pop(idx)
        self.refresh_keranjang()

    def hitung_total(self):
        app = App.get_running_app()
        subtotal = sum(i["subtotal"] for i in self.keranjang)
        try:
            disk_manual = int(self.inp_diskon.text.strip() or 0)
        except ValueError:
            disk_manual = 0

        disk_karyawan = 0
        if self.chk_karyawan.active:
            disk_karyawan = int(subtotal * (app.db["diskon_karyawan_default"] / 100))

        total_diskon = min(subtotal, disk_manual + disk_karyawan)
        total_akhir = max(0, subtotal - total_diskon)
        self.lbl_total.text = f"TOTAL: Rp {total_akhir:,} (Diskon: Rp {total_diskon:,})"
        return subtotal, total_diskon, total_akhir

    def reset_transaksi(self):
        self.keranjang = []
        self.meja_val = 0
        self.lbl_meja.text = "Meja: 0"
        self.inp_diskon.text = "0"
        self.inp_cust_nama.text = ""
        self.inp_cust_wa.text = ""
        self.chk_karyawan.active = False
        self.idx_pesanan_ditemukan = -1
        self.refresh_keranjang()

    def simpan_customer_ke_db(self, nama, no_wa):
        app = App.get_running_app()
        wa_norm = normalisasi_no_wa(no_wa)
        if not wa_norm and not nama:
            return
        key = wa_norm if wa_norm else nama.lower()
        existing = app.db["customers"].get(key, {})
        app.db["customers"][key] = {
            "nama": nama if nama else existing.get("nama", "Pelanggan"),
            "no_wa": no_wa.strip() if no_wa.strip() else existing.get("no_wa", ""),
            "total_kunjungan": existing.get("total_kunjungan", 0) + 1,
            "terakhir_belanja": datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        }

    def simpan_pending(self):
        if not self.keranjang:
            tampilkan_pesan("Peringatan", "Keranjang masih kosong!")
            return
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        inp_nama = TextInput(text=self.inp_cust_nama.text.strip(), hint_text="Masukkan Nama Pemesan", multiline=False, size_hint_y=None, height=dp(44))
        box.add_widget(inp_nama)
        btn_ok = Button(text="Simpan Pesanan", size_hint_y=None, height=dp(44), background_color=C_SUKSES, bold=True)
        box.add_widget(btn_ok)
        popup = Popup(title="Simpan Pesanan Belum Bayar", content=box, size_hint=(0.85, 0.35))

        def do_save(*_):
            nama = inp_nama.text.strip()
            if not nama:
                tampilkan_pesan("Error", "Nama pemesan wajib diisi!")
                return
            sub, disk, tot = self.hitung_total()
            app.db["pesanan_belum_bayar"].append({
                "nama_pemesan": nama,
                "customer_wa": self.inp_cust_wa.text.strip(),
                "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
                "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                "meja": str(self.meja_val),
                "posisi": self.spn_posisi.text,
                "keranjang": copy.deepcopy(self.keranjang),
                "total": tot,
                "total_awal": sub,
                "diskon": disk,
                "kasir": app.user_aktif
            })
            app.simpan_database()
            popup.dismiss()
            self.reset_transaksi()
            self.tampilkan_kasir(buka_popup_menu=False)
            tampilkan_pesan("Sukses", f"Pesanan '{nama}' disimpan!")

        btn_ok.bind(on_release=do_save)
        popup.open()

    def muat_pesanan_pending(self, *args):
        app = App.get_running_app()
        cari = self.inp_cari_psn.text.strip().lower()
        if not cari:
            tampilkan_pesan("Peringatan", "Masukkan nama pemesan!")
            return
        for idx, psn in enumerate(app.db["pesanan_belum_bayar"]):
            if psn["nama_pemesan"].lower() == cari:
                self.keranjang = copy.deepcopy(psn["keranjang"])
                self.inp_cust_nama.text = psn["nama_pemesan"]
                self.inp_cust_wa.text = psn.get("customer_wa", "")
                self.meja_val = int(psn.get("meja", 0))
                self.lbl_meja.text = f"Meja: {self.meja_val}"
                self.spn_posisi.text = psn.get("posisi", "Take-Away")
                self.inp_diskon.text = str(psn.get("diskon", 0))
                self.idx_pesanan_ditemukan = idx
                self.refresh_keranjang()
                tampilkan_pesan("Ditemukan", f"Pesanan '{psn['nama_pemesan']}' dimuat.")
                return
        tampilkan_pesan("Info", f"Pesanan '{cari}' tidak ditemukan.")

    def lihat_semua_pending(self, *args):
        app = App.get_running_app()
        psn_list = app.db["pesanan_belum_bayar"]
        if not psn_list:
            tampilkan_pesan("Info", "Tidak ada pesanan pending.")
            return
        teks = "\n".join([f"{i}. {p['nama_pemesan']} | Meja {p['meja']} | Rp {p['total']:,}" for i, p in enumerate(psn_list, 1)])
        tampilkan_pesan("Daftar Pesanan Pending", teks)

    def format_struk(self, nota):
        app = App.get_running_app()
        lebar = int(app.db["pengaturan_printer"].get("lebar_struk", 32))
        profil = app.db["profil_toko"]
        garis = "=" * lebar
        tipis = "-" * lebar

        nama_toko = profil.get("nama", "WARUNG").upper()
        alamat_toko = profil.get("alamat", "")
        kota_toko = profil.get("kota", "")
        telp_toko = profil.get("telepon", "")
        footer_toko = profil.get("footer", "Terima Kasih")

        teks = f"{nama_toko:^{lebar}}\n"
        if alamat_toko:
            teks += f"{alamat_toko:^{lebar}}\n"
        if kota_toko:
            teks += f"{kota_toko:^{lebar}}\n"
        if telp_toko:
            teks += f"{'Telp: ' + telp_toko:^{lebar}}\n"
        teks += garis + "\n"
        teks += f"Tgl  : {nota['tanggal']} {nota['waktu'][:5]}\n"
        teks += f"Kasir: {nota['kasir']} | Meja: {nota['meja']}\n"
        if nota.get("customer_nama"):
            teks += f"Cust : {nota['customer_nama']}\n"
        teks += tipis + "\n"

        for item in nota["keranjang"]:
            teks += f"{item['nama'][:lebar]}\n"
            teks += f"  {item['jumlah']} x {item['harga']:,} = Rp {item['subtotal']:,}\n"

        teks += tipis + "\n"
        teks += f"SUBTOTAL : Rp {nota['total_awal']:,}\n"
        if nota["diskon"] > 0:
            teks += f"DISKON   : Rp ({nota['diskon']:,})\n"
        teks += f"TOTAL    : Rp {nota['total']:,}\n"
        teks += f"METODE   : {nota['metode']}\n"
        if nota["metode"] == "Tunai":
            teks += f"TUNAI    : Rp {nota['dibayar']:,}\n"
            teks += f"KEMBALI  : Rp {nota['kembalian']:,}\n"
        teks += garis + "\n"
        teks += f"{footer_toko:^{lebar}}\n"
        return teks

    def preview_dan_cetak_struk(self, teks_struk, no_wa="", judul="Preview Struk"):
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        scroll = ScrollView()
        lbl = Label(text=teks_struk, font_size=dp(13), size_hint_y=None, halign="left", valign="top")
        lbl.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        scroll.add_widget(lbl)
        box.add_widget(scroll)

        row_wa = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        inp_wa_popup = TextInput(text=no_wa, hint_text="No. WA Customer (08xxx)", input_filter="int", multiline=False, font_size=dp(13))
        row_wa.add_widget(inp_wa_popup)
        box.add_widget(row_wa)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        btn_cetak = Button(text="Cetak BT", background_color=C_SUKSES, bold=True, font_size=dp(13))
        btn_wa = Button(text="Kirim WA", background_color=C_WA, bold=True, font_size=dp(13))
        btn_tutup = Button(text="Tutup", size_hint_x=None, width=dp(70), background_color=C_BATAL, font_size=dp(13))
        btn_row.add_widget(btn_cetak)
        btn_row.add_widget(btn_wa)
        btn_row.add_widget(btn_tutup)
        box.add_widget(btn_row)

        popup = Popup(title=judul, content=box, size_hint=(0.92, 0.82))
        btn_cetak.bind(on_release=lambda *_: self.kirim_bluetooth(teks_struk))
        btn_wa.bind(on_release=lambda *_: kirim_struk_whatsapp(inp_wa_popup.text.strip(), teks_struk))
        btn_tutup.bind(on_release=popup.dismiss)
        popup.open()

    def kirim_bluetooth(self, teks, silent_success=False):
        app = App.get_running_app()
        cfg = app.db["pengaturan_printer"]
        mac = cfg.get("bluetooth_mac", "").strip()
        channel = int(cfg.get("bluetooth_channel", 1))
        cutting = cfg.get("cutting_paper", True)
        cashdrawer = cfg.get("cashdrawer", False)

        if not mac:
            if not silent_success:
                tampilkan_pesan("Printer Belum Dipilih", "Buka menu 'Printer BT' lalu pilih perangkat Bluetooth yang sudah ter-pair.")
            return

        sukses, pesan = app.bt_manager.kirim_data(teks, mac, channel, cutting, cashdrawer)
        self.update_bt_badge()
        if sukses:
            if not silent_success:
                tampilkan_pesan("Sukses", pesan)
        else:
            tampilkan_pesan("Info Printer", pesan)

    # ===================== 2. DATABASE PELANGGAN (TAMBAH, EDIT, HAPUS, CHAT WA) =====================
    def dialog_edit_pelanggan(self, cust_key, on_done_callback=None):
        app = App.get_running_app()
        custs = app.db.get("customers", {})
        if cust_key not in custs:
            return
        info = custs[cust_key]

        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        box.add_widget(Label(text="Edit Data Pelanggan:", bold=True, font_size=dp(15), size_hint_y=None, height=dp(28)))

        inp_nama_edit = TextInput(text=info.get("nama", ""), hint_text="Nama Pelanggan", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_wa_edit = TextInput(text=info.get("no_wa", ""), hint_text="No. WhatsApp (08xxx)", input_filter="int", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))

        box.add_widget(Label(text="Nama Customer:", size_hint_y=None, height=dp(20), halign="left", font_size=dp(12)))
        box.add_widget(inp_nama_edit)
        box.add_widget(Label(text="Nomor WhatsApp:", size_hint_y=None, height=dp(20), halign="left", font_size=dp(12)))
        box.add_widget(inp_wa_edit)

        row_btn = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_simpan = Button(text="Simpan Perubahan", background_color=C_SUKSES, bold=True, font_size=dp(13))
        btn_batal = Button(text="Batal", size_hint_x=None, width=dp(80), background_color=C_BATAL, font_size=dp(13))
        row_btn.add_widget(btn_simpan)
        row_btn.add_widget(btn_batal)
        box.add_widget(row_btn)

        popup = Popup(title="Edit Data Pelanggan", content=box, size_hint=(0.88, 0.52))
        btn_batal.bind(on_release=popup.dismiss)

        def simpan_perubahan(*_):
            nama_baru = inp_nama_edit.text.strip()
            wa_baru = inp_wa_edit.text.strip()
            if not nama_baru and not wa_baru:
                tampilkan_pesan("Peringatan", "Nama atau No. WA wajib diisi!")
                return

            wa_norm = normalisasi_no_wa(wa_baru)
            new_key = wa_norm if wa_norm else nama_baru.lower()

            updated_data = {
                "nama": nama_baru if nama_baru else "Pelanggan",
                "no_wa": wa_baru,
                "total_kunjungan": info.get("total_kunjungan", 1),
                "terakhir_belanja": info.get("terakhir_belanja", datetime.datetime.now().strftime("%d-%m-%Y %H:%M"))
            }

            if new_key != cust_key:
                del custs[cust_key]
            custs[new_key] = updated_data
            app.simpan_database()
            catat_audit(app.role_aktif or "user", app.user_aktif or "-", "CUSTOMER_EDIT", f"{nama_baru} ({wa_baru})")
            popup.dismiss()
            tampilkan_pesan("Sukses", f"Data pelanggan '{updated_data['nama']}' berhasil diperbarui!")
            if on_done_callback:
                on_done_callback()

        btn_simpan.bind(on_release=simpan_perubahan)
        popup.open()

    def tampilkan_pelanggan(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(8))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="DATABASE PELANGGAN & WHATSAPP", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_nama = TextInput(hint_text="Nama Customer Baru", multiline=False, size_hint_y=None, height=dp(42))
        inp_wa = TextInput(hint_text="No. WhatsApp (cth: 08123456789)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        box.add_widget(inp_nama)
        box.add_widget(inp_wa)

        def tambah_cust(*_):
            n = inp_nama.text.strip()
            w = inp_wa.text.strip()
            if not n or not w:
                tampilkan_pesan("Error", "Nama dan No. WA wajib diisi!")
                return
            self.simpan_customer_ke_db(n, w)
            app.simpan_database()
            tampilkan_pesan("Sukses", f"Pelanggan '{n}' ({w}) tersimpan!")
            self.tampilkan_pelanggan()

        btn_save = Button(text="SIMPAN DATA PELANGGAN BARU", size_hint_y=None, height=dp(44), background_color=C_SUKSES, bold=True)
        btn_save.bind(on_release=tambah_cust)
        box.add_widget(btn_save)

        custs = app.db.get("customers", {})
        box.add_widget(Label(text=f"DAFTAR PELANGGAN ({len(custs)}):", bold=True, size_hint_y=None, height=dp(28)))
        for k, info in list(custs.items()):
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
            row.add_widget(Label(
                text=f"{info['nama']}\nWA: {info['no_wa']} ({info.get('total_kunjungan', 1)}x)",
                font_size=dp(11.5), halign="left"
            ))
            btn_edit = Button(text="Edit", size_hint_x=None, width=dp(48), background_color=C_AKSEN, font_size=dp(11), bold=True)
            btn_chat = Button(text="WA", size_hint_x=None, width=dp(44), background_color=C_WA, font_size=dp(11), bold=True)
            btn_del = Button(text="X", size_hint_x=None, width=dp(36), background_color=C_BATAL, font_size=dp(11), bold=True)

            def hapus_cust(key_del=k, nama_del=info["nama"]):
                if key_del in app.db["customers"]:
                    del app.db["customers"][key_del]
                    app.simpan_database()
                    tampilkan_pesan("Terhapus", f"Pelanggan '{nama_del}' dihapus.")
                    self.tampilkan_pelanggan()

            btn_edit.bind(on_release=lambda inst, ck=k: self.dialog_edit_pelanggan(ck, on_done_callback=self.tampilkan_pelanggan))
            btn_chat.bind(on_release=lambda inst, w=info["no_wa"]: kirim_struk_whatsapp(w, f"Halo kak, salam dari {app.db['profil_toko']['nama']}!"))
            btn_del.bind(on_release=lambda inst, kd=k, nd=info["nama"]: hapus_cust(kd, nd))

            row.add_widget(btn_edit)
            row.add_widget(btn_chat)
            row.add_widget(btn_del)
            box.add_widget(row)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 3. PROFIL WARUNG & PREVIEW STRUK (OWNER) =====================
    def tampilkan_profil_warung(self):
        app = App.get_running_app()
        profil = app.db["profil_toko"]
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(8))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="PENGATURAN NAMA WARUNG & STRUK", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_nama = TextInput(text=profil.get("nama", ""), hint_text="Nama Warung (Display & Header Struk)", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_alamat = TextInput(text=profil.get("alamat", ""), hint_text="Alamat Warung", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_kota = TextInput(text=profil.get("kota", ""), hint_text="Kota / Kabupaten", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_telp = TextInput(text=profil.get("telepon", ""), hint_text="No. Telepon / WA", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_footer = TextInput(text=profil.get("footer", ""), hint_text="Pesan Footer Bawah Struk", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))

        for lbl_txt, widget in [
            ("Nama Warung:", inp_nama),
            ("Alamat:", inp_alamat),
            ("Kota:", inp_kota),
            ("Telepon / WA:", inp_telp),
            ("Footer Struk:", inp_footer)
        ]:
            box.add_widget(Label(text=lbl_txt, size_hint_y=None, height=dp(20), halign="left", font_size=dp(12)))
            box.add_widget(widget)

        def terapkan_form_ke_db():
            nama_baru = inp_nama.text.strip()
            if not nama_baru:
                tampilkan_pesan("Peringatan", "Nama Warung tidak boleh kosong!")
                return False
            profil["nama"] = nama_baru
            profil["alamat"] = inp_alamat.text.strip()
            profil["kota"] = inp_kota.text.strip()
            profil["telepon"] = inp_telp.text.strip()
            profil["footer"] = inp_footer.text.strip()
            app.simpan_database()
            self.refresh_nama_warung_display()
            return True

        def simpan_profil(*_):
            if terapkan_form_ke_db():
                catat_audit(app.role_aktif, app.user_aktif, "PROFIL_UPDATE", f"nama={profil['nama']}")
                tampilkan_pesan("Sukses", f"Nama warung diubah menjadi:\n{profil['nama'].upper()}\n\nLayar utama dan struk otomatis diperbarui.")

        def preview_profil_struk(*_):
            if not terapkan_form_ke_db():
                return
            contoh_nota = {
                "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
                "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                "meja": "3",
                "posisi": "Lesehan",
                "customer_nama": "Budi",
                "keranjang": [
                    {"nama": "Nasi Liwet Solo", "harga": 20000, "jumlah": 2, "subtotal": 40000},
                    {"nama": "Es Teh Manis", "harga": 5000, "jumlah": 2, "subtotal": 10000}
                ],
                "total": 50000,
                "total_awal": 50000,
                "diskon": 0,
                "metode": "QRIS",
                "dibayar": 50000,
                "kembalian": 0,
                "kasir": app.user_aktif or "owner"
            }
            teks = self.format_struk(contoh_nota)
            self.preview_dan_cetak_struk(teks, judul=f"Preview Struk - {profil['nama'].upper()}")

        row_btn = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_simpan = Button(text="SIMPAN NAMA WARUNG", background_color=C_SUKSES, bold=True, font_size=dp(12))
        btn_simpan.bind(on_release=simpan_profil)

        btn_preview = Button(text="PREVIEW & CETAK STRUK", background_color=C_AKSEN, bold=True, font_size=dp(12))
        btn_preview.bind(on_release=preview_profil_struk)

        row_btn.add_widget(btn_simpan)
        row_btn.add_widget(btn_preview)
        box.add_widget(row_btn)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 4. SETTING PRINTER BT =====================
    def tampilkan_printer(self):
        app = App.get_running_app()
        cfg = app.db["pengaturan_printer"]
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(8))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="INSTALASI PRINTER BLUETOOTH", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        lbl_step1 = Label(
            text="1. Pastikan Printer sudah di-Pair di Pengaturan Bluetooth HP.\n2. Tekan Scan lalu pilih nama printer:",
            font_size=dp(12), size_hint_y=None, height=dp(38), halign="left"
        )
        lbl_step1.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        box.add_widget(lbl_step1)

        row_scan = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        default_label = f"{cfg['bluetooth_name']} ({cfg['bluetooth_mac']})" if cfg.get("bluetooth_mac") else "Pilih Printer Bluetooth..."
        self.spn_bt_devices = Spinner(text=default_label, values=[], font_size=dp(13))
        btn_scan = Button(text="Scan BT", size_hint_x=None, width=dp(85), background_color=C_AKSEN, bold=True)
        row_scan.add_widget(self.spn_bt_devices)
        row_scan.add_widget(btn_scan)
        box.add_widget(row_scan)

        inp_mac = TextInput(text=cfg.get("bluetooth_mac", ""), hint_text="MAC Address (otomatis terisi saat pilih di atas)", multiline=False, size_hint_y=None, height=dp(42))
        spn_lebar = Spinner(text=str(cfg.get("lebar_struk", 32)), values=["32", "42", "48"], size_hint_y=None, height=dp(42))

        def jalankan_scan(*_):
            app.bt_manager.minta_izin()
            devices = app.bt_manager.scan_paired_devices()
            self.paired_map = {}
            if not devices:
                tampilkan_pesan(
                    "Perangkat Tidak Ditemukan",
                    "Tidak ada perangkat Bluetooth ter-pair yang terbaca.\n\nPastikan:\n1. Bluetooth HP menyala\n2. Printer sudah di-Pair di Pengaturan HP\n3. Izin Perangkat Terdekat diizinkan."
                )
                return
            pilihan = []
            for nama, mac in devices:
                label = f"{nama} ({mac})"
                self.paired_map[label] = (nama, mac)
                pilihan.append(label)
            self.spn_bt_devices.values = pilihan
            self.spn_bt_devices.text = pilihan[0]

        def saat_printer_dipilih(spinner, text):
            if text in self.paired_map:
                nama, mac = self.paired_map[text]
                inp_mac.text = mac
                cfg["bluetooth_name"] = nama
                cfg["bluetooth_mac"] = mac
                app.simpan_database()
                ok, msg = app.bt_manager.connect(mac, cfg.get("bluetooth_channel", 1))
                self.update_bt_badge()
                tampilkan_pesan("Status Koneksi", msg)

        btn_scan.bind(on_release=jalankan_scan)
        self.spn_bt_devices.bind(text=saat_printer_dipilih)

        box.add_widget(Label(text="MAC Address Aktif:", size_hint_y=None, height=dp(22)))
        box.add_widget(inp_mac)
        box.add_widget(Label(text="Lebar Kertas (58mm = 32 | 80mm = 42):", size_hint_y=None, height=dp(22)))
        box.add_widget(spn_lebar)

        def simpan_dan_sambungkan(*_):
            mac_val = inp_mac.text.strip().upper()
            cfg["bluetooth_mac"] = mac_val
            if not cfg.get("bluetooth_name"):
                cfg["bluetooth_name"] = "Printer Thermal"
            cfg["lebar_struk"] = int(spn_lebar.text)
            app.simpan_database()
            ok, msg = app.bt_manager.connect(mac_val, cfg.get("bluetooth_channel", 1))
            self.update_bt_badge()
            tampilkan_pesan("Simpan & Koneksi", f"Pengaturan disimpan.\nStatus: {msg}")

        btn_save = Button(text="SIMPAN & SAMBUNGKAN SEKARANG", size_hint_y=None, height=dp(48), background_color=C_SUKSES, bold=True)
        btn_save.bind(on_release=simpan_dan_sambungkan)

        btn_test = Button(text="TEST CETAK STRUK", size_hint_y=None, height=dp(48), background_color=C_WARNING, bold=True)
        btn_test.bind(on_release=lambda *_: self.kirim_bluetooth(f"=== {app.db['profil_toko']['nama'].upper()} ===\nKoneksi Bluetooth Berhasil!\n\n"))

        box.add_widget(btn_save)
        box.add_widget(btn_test)
        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)
        jalankan_scan()

    # ===================== 5. EDIT MENU, STOK & EDIT KATEGORI (OWNER) =====================
    def dialog_kelola_kategori(self):
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        box.add_widget(Label(text="KELOLA & EDIT KATEGORI MENU", bold=True, font_size=dp(15), size_hint_y=None, height=dp(28)))

        # Form Tambah Kategori Baru
        row_add = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        inp_kat_baru = TextInput(hint_text="Nama Kategori Baru (cth: Paket Hemat)", multiline=False, font_size=dp(13))
        btn_add_kat = Button(text="Tambah", size_hint_x=None, width=dp(80), background_color=C_SUKSES, bold=True, font_size=dp(13))
        row_add.add_widget(inp_kat_baru)
        row_add.add_widget(btn_add_kat)
        box.add_widget(row_add)

        scroll_kat = ScrollView()
        list_kat = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        list_kat.bind(minimum_height=list_kat.setter("height"))
        scroll_kat.add_widget(list_kat)
        box.add_widget(scroll_kat)

        popup_kat = Popup(title="Edit Kategori Menu", content=box, size_hint=(0.90, 0.75))

        def render_daftar_kategori():
            list_kat.clear_widgets()
            kat_list = app.db.get("kategori_menu", [])
            for idx_k, nama_k in enumerate(kat_list):
                row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
                row.add_widget(Label(text=f"{idx_k + 1}. {nama_k}", halign="left", font_size=dp(13), bold=True))

                btn_ubah = Button(text="Edit Nama", size_hint_x=None, width=dp(82), background_color=C_AKSEN, font_size=dp(12))
                btn_hapus = Button(text="Hapus", size_hint_x=None, width=dp(64), background_color=C_BATAL, font_size=dp(12))

                def buka_ubah_nama(inst, index_k=idx_k, lama_k=nama_k):
                    b_edit = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
                    ti_edit = TextInput(text=lama_k, multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
                    b_edit.add_widget(Label(text=f"Ubah nama kategori '{lama_k}':", size_hint_y=None, height=dp(24)))
                    b_edit.add_widget(ti_edit)
                    r_b = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
                    b_ok = Button(text="Simpan", background_color=C_SUKSES, bold=True)
                    b_cn = Button(text="Batal", background_color=C_BATAL)
                    r_b.add_widget(b_ok)
                    r_b.add_widget(b_cn)
                    b_edit.add_widget(r_b)
                    pop_e = Popup(title="Ubah Nama Kategori", content=b_edit, size_hint=(0.84, 0.4))
                    b_cn.bind(on_release=pop_e.dismiss)

                    def simpan_nama_kat(*_):
                        baru_k = ti_edit.text.strip()
                        if not baru_k:
                            tampilkan_pesan("Error", "Nama kategori tidak boleh kosong!")
                            return
                        app.db["kategori_menu"][index_k] = baru_k
                        # Update semua menu yang memakai kategori lama
                        for m_item in app.db["menu"].values():
                            if m_item.get("kategori") == lama_k:
                                m_item["kategori"] = baru_k
                        app.simpan_database()
                        pop_e.dismiss()
                        render_daftar_kategori()
                        self.tampilkan_edit_menu()

                    b_ok.bind(on_release=simpan_nama_kat)
                    pop_e.open()

                def hapus_kat(inst, index_k=idx_k, nama_hapus=nama_k):
                    if len(app.db["kategori_menu"]) <= 1:
                        tampilkan_pesan("Peringatan", "Minimal harus ada 1 kategori menu!")
                        return
                    app.db["kategori_menu"].pop(index_k)
                    app.simpan_database()
                    render_daftar_kategori()
                    self.tampilkan_edit_menu()

                btn_ubah.bind(on_release=buka_ubah_nama)
                btn_hapus.bind(on_release=hapus_kat)
                row.add_widget(btn_ubah)
                row.add_widget(btn_hapus)
                list_kat.add_widget(row)

        def tambah_kat_baru(*_):
            nk = inp_kat_baru.text.strip()
            if not nk:
                tampilkan_pesan("Peringatan", "Masukkan nama kategori baru!")
                return
            if nk in app.db["kategori_menu"]:
                tampilkan_pesan("Info", f"Kategori '{nk}' sudah ada.")
                return
            app.db["kategori_menu"].append(nk)
            app.simpan_database()
            inp_kat_baru.text = ""
            render_daftar_kategori()
            self.tampilkan_edit_menu()

        btn_add_kat.bind(on_release=tambah_kat_baru)
        render_daftar_kategori()

        btn_tutup = Button(text="Selesai & Tutup", size_hint_y=None, height=dp(44), background_color=C_PRIMARY, bold=True)
        btn_tutup.bind(on_release=popup_kat.dismiss)
        box.add_widget(btn_tutup)
        popup_kat.open()

    def tampilkan_edit_menu(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(6))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="KELOLA MENU, KATEGORI, HPP & STOK", bold=True, font_size=dp(15), size_hint_y=None, height=dp(30)))

        # Tombol Khusus Kelola / Edit Kategori
        btn_kelola_kat = Button(
            text="EDIT / TAMBAH KATEGORI MENU",
            size_hint_y=None,
            height=dp(42),
            background_color=C_PURPLE,
            bold=True,
            font_size=dp(13)
        )
        btn_kelola_kat.bind(on_release=lambda *_: self.dialog_kelola_kategori())
        box.add_widget(btn_kelola_kat)

        inp_kode = TextInput(hint_text="Kode Menu (cth: 6)", multiline=False, size_hint_y=None, height=dp(42))
        inp_nama = TextInput(hint_text="Nama Menu", multiline=False, size_hint_y=None, height=dp(42))
        inp_harga = TextInput(hint_text="Harga Jual (Rp)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        inp_hpp = TextInput(hint_text="HPP / Modal (Rp)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        inp_stok = TextInput(hint_text="Jumlah Stok Tersedia (Porsi)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))

        kat_values = app.db.get("kategori_menu", ["Makanan", "Minuman"])
        spn_kat = Spinner(text=kat_values[0], values=kat_values, size_hint_y=None, height=dp(42))

        for w in [inp_kode, inp_nama, inp_harga, inp_hpp, inp_stok, spn_kat]:
            box.add_widget(w)

        def simpan_menu(*_):
            k = inp_kode.text.strip()
            n = inp_nama.text.strip()
            if not k or not n:
                tampilkan_pesan("Error", "Kode dan Nama menu wajib diisi!")
                return
            try:
                h = int(inp_harga.text.strip() or 0)
                hpp = int(inp_hpp.text.strip() or 0)
                stok = int(inp_stok.text.strip() or 0)
            except ValueError:
                tampilkan_pesan("Error", "Harga, HPP, dan Stok harus berupa angka!")
                return
            app.db["menu"][k] = {"nama": n, "harga": h, "hpp": hpp, "stok": stok, "kategori": spn_kat.text}
            app.simpan_database()
            tampilkan_pesan("Sukses", f"Menu '{n}' [{spn_kat.text}] (Stok: {stok}) tersimpan!")
            self.tampilkan_edit_menu()

        btn_simpan = Button(text="SIMPAN / UPDATE MENU & STOK", size_hint_y=None, height=dp(46), background_color=C_SUKSES, bold=True)
        btn_simpan.bind(on_release=simpan_menu)
        box.add_widget(btn_simpan)

        box.add_widget(Label(text="DAFTAR MENU & KATEGORI SAAT INI:", bold=True, size_hint_y=None, height=dp(30)))
        for k, v in app.db["menu"].items():
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            row.add_widget(Label(
                text=f"[{k}] {v['nama']} ({v.get('kategori', '-')})\nJual: {v['harga']:,} | HPP: {v.get('hpp', 0):,} | Stok: {v.get('stok', 0)}",
                font_size=dp(11), halign="left"
            ))
            btn_edit = Button(text="Edit", size_hint_x=None, width=dp(48), background_color=C_AKSEN, font_size=dp(11))
            btn_hapus = Button(text="Hapus", size_hint_x=None, width=dp(55), background_color=C_BATAL, font_size=dp(11))

            def isi_form(kode_e=k, data_e=v):
                inp_kode.text = kode_e
                inp_nama.text = data_e["nama"]
                inp_harga.text = str(data_e["harga"])
                inp_hpp.text = str(data_e.get("hpp", 0))
                inp_stok.text = str(data_e.get("stok", 0))
                kat_e = data_e.get("kategori", kat_values[0])
                if kat_e not in spn_kat.values:
                    spn_kat.values = list(spn_kat.values) + [kat_e]
                spn_kat.text = kat_e

            def hapus(kode_del=k):
                del app.db["menu"][kode_del]
                app.simpan_database()
                self.tampilkan_edit_menu()

            btn_edit.bind(on_release=lambda inst, ke=k, de=v: isi_form(ke, de))
            btn_hapus.bind(on_release=lambda inst, kd=k: hapus(kd))
            row.add_widget(btn_edit)
            row.add_widget(btn_hapus)
            box.add_widget(row)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 6. BIAYA OPERASIONAL (OWNER) =====================
    def tampilkan_promosi_ops(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(6))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="BIAYA OPERASIONAL BULANAN", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))
        ops = app.db["biaya_operasional"]
        fields = {}
        for key in ["sewa", "listrik", "air", "gas", "karyawan", "transportasi", "lainnya"]:
            row = BoxLayout(size_hint_y=None, height=dp(40))
            row.add_widget(Label(text=key.capitalize(), size_hint_x=0.4))
            ti = TextInput(text=str(ops.get(key, 0)), input_filter="int", multiline=False)
            fields[key] = ti
            row.add_widget(ti)
            box.add_widget(row)

        def simpan_ops(*_):
            for k, ti in fields.items():
                try:
                    ops[k] = int(ti.text.strip() or 0)
                except ValueError:
                    ops[k] = 0
            app.simpan_database()
            total_ops = sum(ops.values())
            tampilkan_pesan("Sukses", f"Biaya Operasional tersimpan!\nTotal: Rp {total_ops:,} / bulan")

        btn_ops = Button(text="SIMPAN BIAYA OPERASIONAL", size_hint_y=None, height=dp(46), background_color=C_SUKSES, bold=True)
        btn_ops.bind(on_release=simpan_ops)
        box.add_widget(btn_ops)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 7. LAPORAN BERTINGKAT + MENU PELANGGAN =====================
    def tampilkan_laporan(self, buka_popup_periode=False, mode_awal="Laporan Hari Ini", sub_jenis_awal="SEMUA"):
        app = App.get_running_app()
        self.area_konten.clear_widgets()
        self.sub_laporan_aktif = sub_jenis_awal
        self.filter_pelanggan_laporan = ""

        root_lap = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))

        # Baris Kontrol Atas: Tombol Pop-Up Periode, Tombol Pop-Up Jenis Laporan, dan Input Tanggal/Bulan/Tahun
        row_ctrl1 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        btn_pilih_periode = Button(text="1. Periode", size_hint_x=0.32, background_color=C_ORANGE, bold=True, font_size=dp(12))
        btn_pilih_sub = Button(text="2. Jenis Laporan", size_hint_x=0.38, background_color=C_PURPLE, bold=True, font_size=dp(12))

        now = datetime.datetime.now()
        default_kunci = now.strftime("%d-%m-%Y") if mode_awal == "Laporan Hari Ini" else (
            now.strftime("%m-%Y") if mode_awal == "Laporan Bulanan" else now.strftime("%Y")
        )
        self.inp_filter_lap = TextInput(text=default_kunci, hint_text="DD-MM-YYYY / MM-YYYY / YYYY", multiline=False, size_hint_x=0.30, font_size=dp(12))

        row_ctrl1.add_widget(btn_pilih_periode)
        row_ctrl1.add_widget(btn_pilih_sub)
        row_ctrl1.add_widget(self.inp_filter_lap)
        root_lap.add_widget(row_ctrl1)

        # Label Indikator Aktif + Tombol Refresh
        row_ctrl2 = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self.spn_periode_lap = Spinner(
            text=mode_awal,
            values=["Laporan Hari Ini", "Laporan Bulanan", "Laporan Tahunan"],
            size_hint_x=0.58,
            font_size=dp(12)
        )
        btn_hitung = Button(text="Tampilkan", size_hint_x=0.42, background_color=C_AKSEN, bold=True, font_size=dp(12))
        row_ctrl2.add_widget(self.spn_periode_lap)
        row_ctrl2.add_widget(btn_hitung)
        root_lap.add_widget(row_ctrl2)

        scroll = ScrollView()
        lbl_laporan = Label(text="", font_size=dp(12.5), size_hint_y=None, halign="left", valign="top")
        lbl_laporan.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        lbl_laporan.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        scroll.add_widget(lbl_laporan)
        root_lap.add_widget(scroll)

        btn_pdf = Button(text="SIMPAN LAPORAN INI KE PDF", size_hint_y=None, height=dp(46), background_color=C_BATAL, bold=True, font_size=dp(13))
        root_lap.add_widget(btn_pdf)

        self.data_laporan_terakhir = {}

        def saat_ganti_jenis(spinner, val, buka_sub_pop=False):
            sekarang = datetime.datetime.now()
            if val == "Laporan Hari Ini":
                self.inp_filter_lap.text = sekarang.strftime("%d-%m-%Y")
            elif val == "Laporan Bulanan":
                self.inp_filter_lap.text = sekarang.strftime("%m-%Y")
            else:
                self.inp_filter_lap.text = sekarang.strftime("%Y")
            hitung_dan_tampilkan()
            if buka_sub_pop:
                popup_pilih_sub_laporan()

        def hitung_dan_tampilkan(*_):
            jenis_periode = self.spn_periode_lap.text
            kunci_waktu = self.inp_filter_lap.text.strip()
            trx_semua = app.db["riwayat_transaksi"]

            if jenis_periode == "Laporan Hari Ini":
                trx_filtered = [t for t in trx_semua if t.get("tanggal", "") == kunci_waktu]
                pengali_ops = 0
                judul_periode = f"HARIAN ({kunci_waktu})"
            elif jenis_periode == "Laporan Bulanan":
                trx_filtered = [t for t in trx_semua if t.get("tanggal", "").endswith(kunci_waktu)]
                pengali_ops = 1
                judul_periode = f"BULANAN ({kunci_waktu})"
            else:
                trx_filtered = [t for t in trx_semua if t.get("tanggal", "").endswith(kunci_waktu)]
                pengali_ops = 12
                judul_periode = f"TAHUNAN ({kunci_waktu})"

            total_omset = sum(t.get("total", 0) for t in trx_filtered)
            total_hpp = 0
            total_item = 0

            sub_tunai = {"trx": 0, "omset": 0}
            sub_qris = {"trx": 0, "omset": 0}
            sub_lain = {"trx": 0, "omset": 0}

            rekap_menu = {}
            terjual_per_kode = {}
            terjual_per_nama = {}
            sales_per_jam = {}

            for t in trx_filtered:
                m = t.get("metode", "Tunai").upper()
                nom = t.get("total", 0)
                if m == "TUNAI":
                    sub_tunai["trx"] += 1
                    sub_tunai["omset"] += nom
                elif m == "QRIS":
                    sub_qris["trx"] += 1
                    sub_qris["omset"] += nom
                else:
                    sub_lain["trx"] += 1
                    sub_lain["omset"] += nom

                wkt_trx = t.get("waktu", "00:00:00")
                jam_str = wkt_trx[:2] if len(wkt_trx) >= 2 else "00"
                slot_jam = f"{jam_str}:00 - {jam_str}:59"
                if slot_jam not in sales_per_jam:
                    sales_per_jam[slot_jam] = {"trx": 0, "omset": 0}
                sales_per_jam[slot_jam]["trx"] += 1
                sales_per_jam[slot_jam]["omset"] += nom

                for it in t.get("keranjang", []):
                    qty = int(it.get("jumlah", 0))
                    sub_it = int(it.get("subtotal", 0))
                    nama_mn = it.get("nama", "Menu")
                    kode_mn = it.get("kode", "")
                    total_hpp += int(it.get("hpp", 0)) * qty
                    total_item += qty

                    if nama_mn not in rekap_menu:
                        rekap_menu[nama_mn] = {"qty": 0, "omset": 0}
                    rekap_menu[nama_mn]["qty"] += qty
                    rekap_menu[nama_mn]["omset"] += sub_it

                    if kode_mn:
                        terjual_per_kode[kode_mn] = terjual_per_kode.get(kode_mn, 0) + qty
                    terjual_per_nama[nama_mn] = terjual_per_nama.get(nama_mn, 0) + qty

            gross_profit = total_omset - total_hpp
            biaya_ops_bulanan = sum(app.db["biaya_operasional"].values())
            total_biaya_ops = biaya_ops_bulanan * pengali_ops
            net_profit = gross_profit - total_biaya_ops
            status_rl = "LABA BERSIH" if net_profit >= 0 else "RUGI BERSIH"

            atv = (total_omset / len(trx_filtered)) if trx_filtered else 0
            gm_persen = (gross_profit / total_omset * 100) if total_omset > 0 else 0
            nm_persen = (net_profit / total_omset * 100) if total_omset > 0 else 0

            # Bagian 1: Rekap per Metode Bayar
            sec_metode = (
                f"[REKAP PER METODE BAYAR]\n"
                f"  - TUNAI : {sub_tunai['trx']} transaksi | Rp {sub_tunai['omset']:,}\n"
                f"  - QRIS  : {sub_qris['trx']} transaksi | Rp {sub_qris['omset']:,}\n"
            )
            if sub_lain["trx"] > 0:
                sec_metode += f"  - Lain  : {sub_lain['trx']} transaksi | Rp {sub_lain['omset']:,}\n"
            sec_metode += (
                f"  ----------------------------------------\n"
                f"  TOTAL   : {len(trx_filtered)} transaksi ({total_item} porsi) | Rp {total_omset:,}\n\n"
            )

            # Bagian 2: Best Seller
            sec_bestseller = "[MENU BEST SELLER (TERLARIS)]\n"
            if not rekap_menu:
                sec_bestseller += "  (Belum ada penjualan pada periode ini)\n\n"
            else:
                sorted_menu = sorted(rekap_menu.items(), key=lambda x: x[1]["qty"], reverse=True)
                for rank, (nama_m, stat_m) in enumerate(sorted_menu, 1):
                    sec_bestseller += f"  #{rank} {nama_m}: {stat_m['qty']} porsi | Rp {stat_m['omset']:,}\n"
                sec_bestseller += "\n"

            # Bagian 3: Laporan Sales & Jam Transaksi
            sec_sales_jam = "[LAPORAN SALES & JAM TRANSAKSI]\n"
            if not trx_filtered:
                sec_sales_jam += "  (Belum ada transaksi pada periode ini)\n\n"
            else:
                sec_sales_jam += "  >> Ringkasan Per Jam:\n"
                for slot_j in sorted(sales_per_jam.keys()):
                    info_j = sales_per_jam[slot_j]
                    sec_sales_jam += f"     • Jam {slot_j} : {info_j['trx']} nota | Rp {info_j['omset']:,}\n"
                sec_sales_jam += "\n  >> Detail Transaksi (Tanggal & Jam):\n"
                for idx_t, t in enumerate(trx_filtered, 1):
                    tgl_t = t.get("tanggal", "-")
                    jam_t = t.get("waktu", "-")
                    meja_t = t.get("meja", "0")
                    met_t = t.get("metode", "Tunai")
                    tot_t = t.get("total", 0)
                    cust_t = f" ({t['customer_nama']})" if t.get("customer_nama") else ""
                    sec_sales_jam += f"     {idx_t}. [{tgl_t} {jam_t}] Meja {meja_t}{cust_t} | {met_t} | Rp {tot_t:,}\n"
                sec_sales_jam += "\n"

            # Bagian 4: Rugi Laba
            sec_rugilaba = (
                f"[LAPORAN RUGI / LABA]\n"
                f"  Pendapatan / Omset : Rp {total_omset:,}\n"
                f"  Harga Pokok (HPP)  : Rp ({total_hpp:,})\n"
                f"  ----------------------------------------\n"
                f"  LABA KOTOR (Gross) : Rp {gross_profit:,} ({gm_persen:.1f}%)\n"
            )
            if pengali_ops > 0:
                sec_rugilaba += (
                    f"  Biaya Operasional  : Rp ({total_biaya_ops:,}) ({pengali_ops} bln)\n"
                    f"  ========================================\n"
                    f"  {status_rl:<18} : Rp {net_profit:,} ({nm_persen:.1f}%)\n"
                )
            else:
                sec_rugilaba += f"  (Catatan: Biaya operasional bulanan dihitung pada Laporan Bulanan/Tahunan)\n"
            sec_rugilaba += f"  Rata-rata / Nota   : Rp {atv:,.0f}\n\n"

            # Bagian 5: Perhitungan Stok Menu
            sec_stok = "[PERHITUNGAN STOK MENU: STOK AWAL - TERJUAL = SISA STOK]\n"
            for kd, mn in app.db["menu"].items():
                nama_mn = mn["nama"]
                sisa_stok = int(mn.get("stok", 0))
                terjual = terjual_per_kode.get(kd, terjual_per_nama.get(nama_mn, 0))
                stok_awal = sisa_stok + terjual
                sec_stok += (
                    f"  - {nama_mn}\n"
                    f"    Stok Awal: {stok_awal} | Terjual: {terjual} | Sisa Stok: {sisa_stok} porsi\n"
                )
            sec_stok += "\n"

            # Bagian 6: Daftar Pelanggan & No WA
            custs = app.db.get("customers", {})
            sec_cust_list = f"[DAFTAR PELANGGAN & NO. WHATSAPP ({len(custs)} Pelanggan)]\n"
            if not custs:
                sec_cust_list += "  (Belum ada data pelanggan tersimpan)\n\n"
            else:
                for idx_c, (ckey, cinfo) in enumerate(custs.items(), 1):
                    sec_cust_list += (
                        f"  {idx_c}. {cinfo.get('nama', '-')} | WA: {cinfo.get('no_wa', '-')} "
                        f"| Kunjungan: {cinfo.get('total_kunjungan', 1)}x | Terakhir: {cinfo.get('terakhir_belanja', '-')}\n"
                    )
                sec_cust_list += "\n"

            # Bagian 7: Daftar Transaksi Pelanggan
            filter_cust = self.filter_pelanggan_laporan.strip().lower()
            trx_pelanggan = [
                t for t in trx_filtered
                if (t.get("customer_nama", "").strip() or t.get("customer_wa", "").strip())
            ]
            if filter_cust:
                trx_pelanggan = [
                    t for t in trx_pelanggan
                    if filter_cust in t.get("customer_nama", "").lower() or filter_cust in t.get("customer_wa", "").lower()
                ]

            judul_filter_c = f" (Filter: {self.filter_pelanggan_laporan})" if filter_cust else ""
            sec_cust_trx = f"[DAFTAR TRANSAKSI PELANGGAN{judul_filter_c}]\n"
            if not trx_pelanggan:
                sec_cust_trx += "  (Belum ada transaksi dengan data pelanggan pada periode ini)\n\n"
            else:
                tot_belanja_cust = sum(t.get("total", 0) for t in trx_pelanggan)
                for idx_tp, tp in enumerate(trx_pelanggan, 1):
                    cn = tp.get("customer_nama") or "Pelanggan"
                    cw = tp.get("customer_wa") or "-"
                    items_str = ", ".join(f"{it['nama']} x{it['jumlah']}" for it in tp.get("keranjang", []))
                    sec_cust_trx += (
                        f"  {idx_tp}. {cn} (WA: {cw})\n"
                        f"     Waktu: {tp.get('tanggal')} {tp.get('waktu')} | {tp.get('metode')} | Rp {tp.get('total', 0):,}\n"
                        f"     Item : {items_str}\n"
                    )
                sec_cust_trx += f"  ----------------------------------------\n"
                sec_cust_trx += f"  Total Transaksi Pelanggan: {len(trx_pelanggan)} nota | Rp {tot_belanja_cust:,}\n\n"

            nama_warung = app.db["profil_toko"]["nama"].upper()
            label_sub_map = {
                "METODE": "REKAP PER METODE BAYAR",
                "BEST_SELLER": "MENU BEST SELLER",
                "SALES_JAM": "LAPORAN SALES & JAM TRANSAKSI",
                "RUGI_LABA": "LAPORAN RUGI / LABA",
                "STOK_MENU": "PERHITUNGAN STOK MENU",
                "CUST_DAFTAR": "DAFTAR PELANGGAN & NO. WA",
                "CUST_TRX": "DAFTAR TRANSAKSI PELANGGAN",
                "SEMUA": "LAPORAN LENGKAP"
            }
            judul_sub = label_sub_map.get(self.sub_laporan_aktif, "LAPORAN LENGKAP")

            header = (
                f"{nama_warung}\n"
                f"{judul_sub} - {judul_periode}\n"
                f"==========================================\n\n"
            )

            if self.sub_laporan_aktif == "METODE":
                isi_laporan = header + sec_metode
            elif self.sub_laporan_aktif == "BEST_SELLER":
                isi_laporan = header + sec_bestseller
            elif self.sub_laporan_aktif == "SALES_JAM":
                isi_laporan = header + sec_sales_jam
            elif self.sub_laporan_aktif == "RUGI_LABA":
                isi_laporan = header + sec_rugilaba
            elif self.sub_laporan_aktif == "STOK_MENU":
                isi_laporan = header + sec_stok
            elif self.sub_laporan_aktif == "CUST_DAFTAR":
                isi_laporan = header + sec_cust_list
            elif self.sub_laporan_aktif == "CUST_TRX":
                isi_laporan = header + sec_cust_trx
            else:
                isi_laporan = header + sec_metode + sec_bestseller + sec_sales_jam + sec_rugilaba + sec_stok + sec_cust_list + sec_cust_trx

            lbl_laporan.text = isi_laporan
            self.data_laporan_terakhir = {
                "judul_periode": judul_periode,
                "sub_jenis": self.sub_laporan_aktif,
                "kunci_waktu": kunci_waktu.replace("-", "_"),
                "teks": isi_laporan
            }

        def ekspor_ke_pdf(*_):
            if not self.data_laporan_terakhir:
                hitung_dan_tampilkan()
            sub_tag = self.data_laporan_terakhir.get("sub_jenis", "LENGKAP")
            nama_file = f"Laporan_{sub_tag}_{self.data_laporan_terakhir['kunci_waktu']}.pdf"
            path_output = ""
            if platform == "android":
                try:
                    folder_dl = "/storage/emulated/0/Download"
                    os.makedirs(folder_dl, exist_ok=True)
                    path_output = os.path.join(folder_dl, nama_file)
                    simpan_teks_ke_pdf_murni(self.data_laporan_terakhir["teks"], path_output)
                except Exception:
                    path_output = os.path.join(get_storage_dir(), nama_file)
                    simpan_teks_ke_pdf_murni(self.data_laporan_terakhir["teks"], path_output)
            else:
                path_output = os.path.abspath(nama_file)
                simpan_teks_ke_pdf_murni(self.data_laporan_terakhir["teks"], path_output)

            tampilkan_pesan("PDF Berhasil Disimpan", f"Laporan berhasil disimpan dalam format PDF:\n\n{path_output}")

        # POP-UP KHUSUS MENU PELANGGAN DI DALAM LAPORAN
        def popup_menu_pelanggan_laporan():
            box_c = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
            box_c.add_widget(Label(
                text="MENU PELANGGAN & RIWAYAT TRANSAKSI",
                font_size=dp(14),
                bold=True,
                size_hint_y=None,
                height=dp(30)
            ))

            popup_c = Popup(title="Laporan & Kelola Pelanggan", content=box_c, size_hint=(0.92, 0.78))

            btn_daftar_wa = Button(
                text="1. Daftar Pelanggan dengan No. WA",
                size_hint_y=None,
                height=dp(44),
                background_color=C_WA,
                bold=True,
                font_size=dp(13)
            )
            btn_trx_all = Button(
                text="2. Daftar Semua Transaksi Pelanggan",
                size_hint_y=None,
                height=dp(44),
                background_color=C_AKSEN,
                bold=True,
                font_size=dp(13)
            )

            def tampil_daftar_wa(*_):
                popup_c.dismiss()
                self.filter_pelanggan_laporan = ""
                self.sub_laporan_aktif = "CUST_DAFTAR"
                hitung_dan_tampilkan()

            def tampil_trx_semua(*_):
                popup_c.dismiss()
                self.filter_pelanggan_laporan = ""
                self.sub_laporan_aktif = "CUST_TRX"
                hitung_dan_tampilkan()

            btn_daftar_wa.bind(on_release=tampil_daftar_wa)
            btn_trx_all.bind(on_release=tampil_trx_semua)
            box_c.add_widget(btn_daftar_wa)
            box_c.add_widget(btn_trx_all)

            box_c.add_widget(Label(
                text="Pilih Pelanggan (Lihat Transaksi / Edit Data / Chat WA):",
                font_size=dp(12),
                size_hint_y=None,
                height=dp(24)
            ))

            scroll_c = ScrollView()
            list_c = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
            list_c.bind(minimum_height=list_c.setter("height"))
            scroll_c.add_widget(list_c)
            box_c.add_widget(scroll_c)

            custs = app.db.get("customers", {})
            if not custs:
                list_c.add_widget(Label(text="Belum ada data pelanggan tersimpan.", size_hint_y=None, height=dp(36)))
            else:
                for ck, cinfo in list(custs.items()):
                    r_item = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
                    btn_pilih_c = Button(
                        text=f"{cinfo.get('nama', '-')} ({cinfo.get('no_wa', '-')})",
                        background_color=C_PRIMARY,
                        font_size=dp(12),
                        halign="left"
                    )
                    btn_edit_c = Button(text="Edit", size_hint_x=None, width=dp(50), background_color=C_WARNING, font_size=dp(11), bold=True)
                    btn_wa_c = Button(text="WA", size_hint_x=None, width=dp(44), background_color=C_WA, font_size=dp(11), bold=True)

                    def pilih_cust_trx(inst, nama_c=cinfo.get("nama", ""), wa_c=cinfo.get("no_wa", "")):
                        popup_c.dismiss()
                        self.filter_pelanggan_laporan = nama_c if nama_c else wa_c
                        self.sub_laporan_aktif = "CUST_TRX"
                        hitung_dan_tampilkan()

                    def edit_dari_lap(inst, key_c=ck):
                        popup_c.dismiss()
                        self.dialog_edit_pelanggan(key_c, on_done_callback=popup_menu_pelanggan_laporan)

                    btn_pilih_c.bind(on_release=pilih_cust_trx)
                    btn_edit_c.bind(on_release=edit_dari_lap)
                    btn_wa_c.bind(on_release=lambda inst, w=cinfo.get("no_wa", ""): kirim_struk_whatsapp(w, f"Halo kak, salam dari {app.db['profil_toko']['nama']}!"))

                    r_item.add_widget(btn_pilih_c)
                    r_item.add_widget(btn_edit_c)
                    r_item.add_widget(btn_wa_c)
                    list_c.add_widget(r_item)

            btn_tutup_c = Button(text="Tutup", size_hint_y=None, height=dp(40), background_color=C_BATAL, font_size=dp(13))
            btn_tutup_c.bind(on_release=popup_c.dismiss)
            box_c.add_widget(btn_tutup_c)
            popup_c.open()

        # POP-UP 2: PILIH JENIS LAPORAN SETELAH PILIH HARI / BULAN / TAHUN
        def popup_pilih_sub_laporan(*_):
            periode_aktif = self.spn_periode_lap.text
            box_sub = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(7))
            box_sub.add_widget(Label(
                text=f"Periode: {periode_aktif}\nPilih Jenis Laporan yang Ingin Ditampilkan:",
                font_size=dp(14),
                bold=True,
                halign="center",
                size_hint_y=None,
                height=dp(44)
            ))

            popup_sub = Popup(title=f"Detail {periode_aktif}", content=box_sub, size_hint=(0.90, 0.78))

            def pilih_sub(kode_sub):
                popup_sub.dismiss()
                if kode_sub == "MENU_PELANGGAN":
                    popup_menu_pelanggan_laporan()
                    return
                self.filter_pelanggan_laporan = ""
                self.sub_laporan_aktif = kode_sub
                hitung_dan_tampilkan()

            daftar_pilihan = [
                ("1. Rekap per Metode Bayar", "METODE", C_SUKSES),
                ("2. Menu Best Seller", "BEST_SELLER", C_AKSEN),
                ("3. Laporan Sales & Jam Transaksi", "SALES_JAM", C_ORANGE),
                ("4. Laporan Rugi / Laba", "RUGI_LABA", C_PURPLE),
                ("5. Stok Awal - Terjual = Sisa Stok", "STOK_MENU", C_PRIMARY),
                ("6. Menu Pelanggan (WA, Transaksi & Edit)", "MENU_PELANGGAN", C_WA),
                ("Tampilkan Semua Laporan Lengkap", "SEMUA", C_WARNING)
            ]

            for label_btn, kode_s, warna_b in daftar_pilihan:
                b = Button(text=label_btn, background_color=warna_b, bold=True, font_size=dp(12.5))
                b.bind(on_release=lambda inst, ks=kode_s: pilih_sub(ks))
                box_sub.add_widget(b)

            btn_batal_sub = Button(text="Tutup", size_hint_y=None, height=dp(38), background_color=C_BATAL, font_size=dp(13))
            btn_batal_sub.bind(on_release=popup_sub.dismiss)
            box_sub.add_widget(btn_batal_sub)
            popup_sub.open()

        # POP-UP 1: PILIH PERIODE (HARI INI / BULANAN / TAHUNAN)
        def popup_pilih_jenis_laporan(*_):
            box_p = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
            box_p.add_widget(Label(text="Langkah 1: Pilih Periode Laporan", font_size=dp(15), bold=True, size_hint_y=None, height=dp(32)))

            popup_lap = Popup(title="Pilih Periode Laporan", content=box_p, size_hint=(0.86, 0.48))

            def pilih_mode(mode_str):
                popup_lap.dismiss()
                self.spn_periode_lap.text = mode_str
                saat_ganti_jenis(self.spn_periode_lap, mode_str, buka_sub_pop=True)

            btn_harian = Button(text="LAPORAN HARI INI", background_color=C_SUKSES, bold=True, font_size=dp(14))
            btn_bulanan = Button(text="LAPORAN BULANAN", background_color=C_AKSEN, bold=True, font_size=dp(14))
            btn_tahunan = Button(text="LAPORAN TAHUNAN", background_color=C_ORANGE, bold=True, font_size=dp(14))
            btn_tutup = Button(text="Tutup", size_hint_y=None, height=dp(38), background_color=C_BATAL, font_size=dp(13))

            btn_harian.bind(on_release=lambda *_: pilih_mode("Laporan Hari Ini"))
            btn_bulanan.bind(on_release=lambda *_: pilih_mode("Laporan Bulanan"))
            btn_tahunan.bind(on_release=lambda *_: pilih_mode("Laporan Tahunan"))
            btn_tutup.bind(on_release=popup_lap.dismiss)

            box_p.add_widget(btn_harian)
            box_p.add_widget(btn_bulanan)
            box_p.add_widget(btn_tahunan)
            box_p.add_widget(btn_tutup)
            popup_lap.open()

        btn_pilih_periode.bind(on_release=popup_pilih_jenis_laporan)
        btn_pilih_sub.bind(on_release=popup_pilih_sub_laporan)
        self.spn_periode_lap.bind(text=lambda sp, val: saat_ganti_jenis(sp, val, buka_sub_pop=False))
        btn_hitung.bind(on_release=hitung_dan_tampilkan)
        btn_pdf.bind(on_release=ekspor_ke_pdf)

        self.area_konten.add_widget(root_lap)
        hitung_dan_tampilkan()

        if buka_popup_periode:
            popup_pilih_jenis_laporan()

    # ===================== 8. MANAJEMEN USER & ROLE (OWNER) =====================
    def tampilkan_manajemen_user(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(6))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="MANAJEMEN USER & ROLE", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_u = TextInput(hint_text="Username Baru", multiline=False, size_hint_y=None, height=dp(42))
        inp_p = TextInput(hint_text="Password", multiline=False, size_hint_y=None, height=dp(42))
        spn_r = Spinner(text="kasir", values=["kasir", "owner"], size_hint_y=None, height=dp(42))

        box.add_widget(inp_u)
        box.add_widget(inp_p)
        box.add_widget(spn_r)

        def tambah_user(*_):
            u = inp_u.text.strip()
            p = inp_p.text.strip()
            r = spn_r.text
            if not u or not p:
                tampilkan_pesan("Error", "Username dan Password wajib diisi!")
                return
            app.db["users"][u] = {"password": p, "role": r, "nama": u}
            app.simpan_database()
            catat_audit(app.role_aktif, app.user_aktif, "USER_CREATE", f"user={u}, role={r}")
            tampilkan_pesan("Sukses", f"User '{u}' ({r}) berhasil dibuat!")
            self.tampilkan_manajemen_user()

        btn_add = Button(text="TAMBAH USER", size_hint_y=None, height=dp(46), background_color=C_SUKSES, bold=True)
        btn_add.bind(on_release=tambah_user)
        box.add_widget(btn_add)

        box.add_widget(Label(text="DAFTAR USER TERDAFTAR:", bold=True, size_hint_y=None, height=dp(28)))
        for u, info in app.db["users"].items():
            row = BoxLayout(size_hint_y=None, height=dp(38))
            row.add_widget(Label(text=f"User: {u} | Role: {info['role'].upper()}", halign="left"))
            if u != "owner":
                btn_del = Button(text="Hapus", size_hint_x=None, width=dp(65), background_color=C_BATAL)
                btn_del.bind(on_release=lambda inst, usr=u: self.hapus_user(usr))
                row.add_widget(btn_del)
            box.add_widget(row)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    def hapus_user(self, uname):
        app = App.get_running_app()
        if uname in app.db["users"]:
            del app.db["users"][uname]
            app.simpan_database()
            catat_audit(app.role_aktif, app.user_aktif, "USER_DELETE", f"user={uname}")
            self.tampilkan_manajemen_user()


class KasirAndroidApp(App):
    def build(self):
        self.db = self.muat_database()
        self.title = self.db["profil_toko"].get("nama", "Kasir Warung")
        self.user_aktif = None
        self.role_aktif = None
        self.modal_awal = 0
        self.saldo_kas = 0
        self.bt_manager = BluetoothPrinterManager()
        self.bt_manager.minta_izin()

        sm = ScreenManager()
        self.login_screen = LoginScreen(name="login")
        self.main_screen = MainScreen(name="main")
        sm.add_widget(self.login_screen)
        sm.add_widget(self.main_screen)
        return sm

    def get_db_path(self):
        return os.path.join(get_storage_dir(), "database_warung.json")

    def muat_database(self):
        db_path = self.get_db_path()
        if not os.path.exists(db_path):
            db = copy.deepcopy(DATA_AWAL)
            try:
                with open(db_path, "w", encoding="utf-8") as f:
                    json.dump(db, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
            return db
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DATA_AWAL.items():
                if k not in data:
                    data[k] = copy.deepcopy(v)
            for m in data.get("menu", {}).values():
                if "stok" not in m:
                    m["stok"] = 20
            return data
        except Exception:
            return copy.deepcopy(DATA_AWAL)

    def simpan_database(self):
        try:
            with open(self.get_db_path(), "w", encoding="utf-8") as f:
                json.dump(self.db, f, indent=4, ensure_ascii=False)
        except Exception as e:
            tampilkan_pesan("Error Database", f"Gagal menyimpan data: {e}")


if __name__ == "__main__":
    KasirAndroidApp().run()