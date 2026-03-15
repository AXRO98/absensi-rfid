"""
=========================================================
 FirebaseArrayDB Library (Auto Initialize)
 --------------------------------------------------------
 Library ini otomatis melakukan koneksi Firebase saat 
 file di-import. Tidak perlu inisialisasi manual lagi.

 CARA PAKAI DI FLASK:
 --------------------------------------------------------
 from firebase_array_db import firebase

 firebase.create_user(...)
 firebase.add_absen(...)
 firebase.get_all()
 =========================================================
"""

import firebase_admin
from datetime import datetime
from pathlib import Path
from firebase_admin import credentials, db


class FirebaseArrayDB:
    def __init__(self, cred_path, db_url):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                "databaseURL": db_url
            })

        self.ref = db.reference("users")

    # 🟢 CREATE USER (FIELD BARU: nama)
    def create_user(self, nama, gender, kelas, UID):
        users = self.ref.get() or []

        new_user = {
            "ABSEN": {},
            "UID": UID,
            "kelas": kelas,
            "gender": gender,
            "nama": nama     # <<< DIUBAH DI SINI
        }

        users.append(new_user)
        self.ref.set(users)
        return True

    # 🟡 UPDATE USER
    def update_user(self, uid_lama, nama=None, gender=None, kelas=None, uid_baru=None):
        users = self.ref.get() or []
        updated = False

        for u in users:
            if u["UID"] == uid_lama:

                if nama is not None:
                    u["nama"] = nama   # <<< DIUBAH DI SINI

                if gender is not None:
                    u["gender"] = gender

                if kelas is not None:
                    u["kelas"] = kelas

                if uid_baru is not None:
                    u["UID"] = uid_baru

                updated = True
                break

        if not updated:
            return False

        self.ref.set(users)
        return True

    # 🔴 DELETE USER
    def delete_user(self, UID):
        users = self.ref.get() or []
        users = [u for u in users if u["UID"] != UID]
        self.ref.set(users)
        return True

    # 🟢 TAMBAH ABSEN
    def add_absen(self, uid, tanggal, status):
        users = self.ref.get() or []
        tanggal_key = tanggal.replace("/", "-")

        for user in users:
            if user["UID"] == uid:

                if "ABSEN" not in user:
                    user["ABSEN"] = {}

                user["ABSEN"][tanggal_key] = status
                self.ref.set(users)
                return True

        return False

    # ✏️ EDIT ABSEN - Versi baru yang support jam masuk & keluar
    def edit_absen(self, UID, tanggal, status_baru=None, jam_masuk_baru=None, jam_keluar_baru=None):
        users = self.ref.get() or []
        tanggal_key = tanggal.replace("/", "-")

        for user in users:
            if user["UID"] == UID:
                if "ABSEN" not in user:
                    user["ABSEN"] = {}

                # Jika tanggal absen belum ada, buat entry baru
                if tanggal_key not in user["ABSEN"]:
                    user["ABSEN"][tanggal_key] = {
                        "status": status_baru or "Hadir",
                        "jam_masuk": jam_masuk_baru or "",
                        "jam_keluar": jam_keluar_baru or ""
                    }
                else:
                    # Jika sudah ada, update field yang diberikan
                    absen_data = user["ABSEN"][tanggal_key]
                    
                    # Handle jika data lama masih string (format lama)
                    if isinstance(absen_data, str):
                        # Convert dari format lama ke format baru
                        user["ABSEN"][tanggal_key] = {
                            "status": status_baru or absen_data,
                            "jam_masuk": jam_masuk_baru or "",
                            "jam_keluar": jam_keluar_baru or ""
                        }
                    else:
                        # Format baru, update field yang diberikan
                        if status_baru is not None:
                            absen_data["status"] = status_baru
                        if jam_masuk_baru is not None:
                            absen_data["jam_masuk"] = jam_masuk_baru
                        if jam_keluar_baru is not None:
                            absen_data["jam_keluar"] = jam_keluar_baru

                self.ref.set(users)
                
                # Print log yang informatif
                log_message = f"📝 Absen {tanggal} diupdate untuk UID {UID}"
                if status_baru:
                    log_message += f" | Status: {status_baru}"
                if jam_masuk_baru:
                    log_message += f" | Jam Masuk: {jam_masuk_baru}"
                if jam_keluar_baru:
                    log_message += f" | Jam Keluar: {jam_keluar_baru}"
                print(log_message)
                
                return

        print("❌ UID tidak ditemukan.")


    # 🔍 FILTER BERDASARKAN UID
    def filter_by_uid(self, UID):
        users = self.ref.get() or []
        return [u for u in users if u["UID"] == UID]

    # 🔍 FILTER BERDASARKAN KELAS
    def filter_by_kelas(self, kelas):
        users = self.ref.get() or []
        return [u for u in users if u["kelas"] == kelas]

    # 🔍 GET ALL DATA
    def get_all(self):
        return self.ref.get() or []

    # 🔍 HITUNG ABSEN HARI INI BERDASARKAN KELAS
    def absen_today_by_kelas(self, kelas):
        users = self.ref.get() or []
        
        # tanggal otomatis
        tanggal = datetime.now().strftime("%d-%m-%Y")

        count = 0
        for u in users:
            if u["kelas"] == kelas:
                if "ABSEN" in u and tanggal in u["ABSEN"]:
                    count += 1

        return count

    # 🔍 HITUNG TOTAL ABSEN HARI INI (SEMUA KELAS)
    def absen_today_all(self):
        users = self.ref.get() or []
        
        # tanggal otomatis
        tanggal = datetime.now().strftime("%d-%m-%Y")

        count = 0
        for u in users:
            if "ABSEN" in u and tanggal in u["ABSEN"]:
                count += 1

        return count
    
    # 🔍 LIST SISWA YANG BELUM ABSEN HARI INI PER KELAS
    def not_absen_today_by_kelas(self, kelas):
        users = self.ref.get() or []
        tanggal = datetime.now().strftime("%d-%m-%Y")

        count = 0
        for u in users:
            if u["kelas"] == kelas:
                if "ABSEN" not in u or tanggal not in u["ABSEN"]:
                    count += 1

        return count

    # 🔍 LIST SISWA YANG BELUM ABSEN HARI INI (SEMUA KELAS)
    def not_absen_today_all(self):
        users = self.ref.get() or []
        tanggal = datetime.now().strftime("%d-%m-%Y")

        count = 0
        for u in users:
            if "ABSEN" not in u or tanggal not in u["ABSEN"]:
                count += 1

        return count

    def class_list(self):
        users = self.ref.get() or []

        kelas_list = set()  # pakai set untuk hilangkan duplikat

        for u in users:
            if "kelas" in u:
                kelas_list.add(u["kelas"])

        return list(kelas_list)

    # 🕐 METHOD KHUSUS UNTUK ABSEN MASUK
    def absen_masuk(self, uid, tanggal=None, status="Hadir"):
        if tanggal is None:
            tanggal = datetime.now().strftime("%d/%m/%Y")
        
        jam_masuk = datetime.now().strftime("%H:%M:%S")
        self.add_absen(uid, tanggal, status, jam_masuk, None)
        print(f"🟢 Absen masuk berhasil: {jam_masuk}")

    # 🕐 METHOD KHUSUS UNTUK ABSEN KELUAR
    def absen_keluar(self, uid, tanggal=None):
        if tanggal is None:
            tanggal = datetime.now().strftime("%d/%m/%Y")
        
        jam_keluar = datetime.now().strftime("%H:%M:%S")
        self.edit_absen(uid, tanggal, jam_keluar_baru=jam_keluar)
        print(f"🔴 Absen keluar berhasil: {jam_keluar}")



# ======================================================
# ⬇️ AUTO INITIALIZE 
# ======================================================

firebase = FirebaseArrayDB(
    cred_path=str(Path(__file__).resolve().parent.parent / "database" / "credential-database.json"),
    db_url="https://smantu-rfid-absensi-default-rtdb.asia-southeast1.firebasedatabase.app/"
)
