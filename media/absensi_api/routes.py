from flask import Blueprint, request
from flask_login import login_required
from apps import db
from apps.decorators import role_required
from apps.authentication.models import Users
from threading import Timer
from apps.absensi_api.spreadsheet import add_absen
from apps.db_json import cek_nama_db, cek_sinkron_db_spreadsheets
from datetime import datetime, timedelta
import requests

# === Konfigurasi ===
api_blueprint = Blueprint('api_blueprint', __name__, url_prefix='/api')

TOKEN = "robotik"
API_KEY = "KX7#-LA8V-R4S0-D0K3"
url_whatsapp = "http://localhost:3000/api/send-message"

# Queue absensi
pending_absen = []
max_absen = 150   # Max absen per interval
check_interval = 1  # Cek setiap 1 detik
wait_interval = 10  # Delay saat penuh
start_time = datetime.now()  # Waktu mulai


# === Helper Functions ===
def send_notification(uid: str):
    """Kirim notifikasi ke WhatsApp bot"""
    waktu_absen = datetime.now  ().strftime('%d/%m/%Y Pukul %H:%M WITA')
    pesan = f"""*[ Notifikasi Kehadiran Siswa SMAN 7 MANADO ]*
Dengan hormat,
Kami informasikan bahwa siswa/siswi dengan rincian sebagai berikut:
Nama : {cek_nama_db(uid)}
UID : {uid}
Kelas : [Kelas]
Waktu Absensi : {waktu_absen}
Telah berhasil melakukan absensi pada sistem sekolah."""

    payload = {
        "nomor": "62882021224181",  # Ganti dengan nomor tujuan
        "pesan": pesan
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.post(url_whatsapp, json=payload, headers=headers)

    print("=== Notifikasi WhatsApp ===")
    print("Payload:", payload)
    print("Status:", response.status_code, response.text)


def process_absen():
    """Proses antrian absensi tiap interval"""
    global pending_absen, start_time

    if datetime.now() - start_time >= timedelta(seconds=wait_interval):
        start_time = datetime.now()  # reset waktu

        if pending_absen:
            to_process = pending_absen[:max_absen]
            pending_absen = pending_absen[max_absen:]

            print(f"Memproses UID: {to_process}")

            for uid in to_process:
                result = add_absen(uid)
                print(f"Result UID {uid}: {result}")

        # Jadwalkan ulang
        Timer(check_interval, process_absen).start()
    else:
        Timer(check_interval, process_absen).start()


# === Routes ===
@api_blueprint.route('/')
@login_required
def api_home():
    return "Welcome to the Absensi API"


@api_blueprint.route('/rfid', methods=["POST"])
def rfid():
    """Endpoint absen via RFID"""
    api_key = request.form.get('apikey')
    uid = request.form.get('uid')
    waktu = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Validasi API key
    if api_key != TOKEN:
        return {
            "status": "failed",
            "message": "Invalid API key"
        }, 403

    print(f"""
{'='*30}
 STATUS: Process Absen
 UID   : {uid}
 NAMA  : {cek_nama_db(uid)}
 WAKTU : {waktu}
{'='*30}
""")
    
    # Tambahkan langsung ke spreadsheet (opsional)
    add_absen(uid)

    # Kirim notifikasi WhatsApp
    send_notification(uid)

    return {
        "nama": cek_nama_db(uid),
        "uid": uid,
        "status": "success"
    }


@api_blueprint.route('/sinkron_data', methods=['GET', 'POST'])
def sinkron():
    """Sinkronisasi database dengan spreadsheet"""
    return cek_sinkron_db_spreadsheets()
