from flask import Blueprint, request, jsonify, flash
from datetime import datetime
import hashlib, requests, time, os
from datetime import datetime


from apps.database.firebase_database import firebase

api_blueprint = Blueprint('api_blueprint', __name__, url_prefix='/api')

# Password untuk encryption
pswd = "14Gr@ce01C4nt1k20B4nget09"
WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_API_TOKEN', '14Gr@ce01C4nt1k20B4nget09T0k3nB0T')

def hash_sha256(text):
    text = pswd + text
    return hashlib.sha256(text.encode()).hexdigest()

def get_status_by_time():
    """Menentukan status berdasarkan waktu sekarang"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    hour_minute = now.strftime("%H:%M")
    
    # Convert ke minutes untuk perbandingan
    current_minutes = int(now.hour) * 60 + int(now.minute)
    
    # Batas waktu
    absen_masuk_end = 7 * 60 + 15  # 07:15 dalam minutes
    absen_pulang_start = 14 * 60 + 15  # 14:15 dalam minutes
    
    if current_minutes <= absen_masuk_end:
        return "Absen"
    elif current_minutes <= absen_pulang_start:
        return "Terlambat"
    else:
        return "Pulang"

@api_blueprint.route('/absen', methods=['POST'])
def absen():
    if request.method == 'GET':
        return jsonify({
            "date": datetime.now().strftime("%d-%m-%Y"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": get_status_by_time()
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Validasi input
            if not data or 'token' not in data or 'uid' not in data:
                return jsonify({
                    "success": False,
                    "message": "Token dan UID diperlukan"
                }), 400
            
            token = data['token']
            uid = data['uid']
            
            # Verifikasi token
            expected_token = hash_sha256(uid)
            if token != expected_token:
                return jsonify({
                    "success": False,
                    "message": "Token tidak valid"
                }), 401
            
            # Cek apakah user ada
            users = firebase.filter_by_uid(uid)
            if not users:
                return jsonify({
                    "success": False,
                    "message": "UID tidak ditemukan"
                }), 404
            
            user = users[0]
            current_date = datetime.now().strftime("%d-%m-%Y")
            current_time = datetime.now().strftime("%H:%M:%S")
            status = get_status_by_time()
            
            # Cek absen hari ini
            absen_hari_ini = user.get("ABSEN", {}).get(current_date, {})
            
            if isinstance(absen_hari_ini, dict):
                # Format baru dengan jam
                sudah_absen_masuk = absen_hari_ini.get("jam_masuk")
                sudah_absen_pulang = absen_hari_ini.get("jam_keluar")
                status_sekarang = absen_hari_ini.get("status")
            else:
                # Format lama
                sudah_absen_masuk = absen_hari_ini if absen_hari_ini else None
                sudah_absen_pulang = None
                status_sekarang = absen_hari_ini
            
            # Logika absensi
            if status == "Absen" or status == "Terlambat":
                # Absen Masuk
                if sudah_absen_masuk:
                    return jsonify({
                        "success": False,
                        "message": f"Sudah absen masuk pada {sudah_absen_masuk}",
                        "data": {
                            "nama": user.get("nama"),
                            "kelas": user.get("kelas"),
                            "jam_masuk": sudah_absen_masuk,
                            "status": status_sekarang
                        }
                    }), 400
                
                # Absen masuk
                final_status = "Terlambat" if status == "Terlambat" else "Hadir"
                firebase.edit_absen(
                    uid, 
                    current_date, 
                    status_baru=final_status,
                    jam_masuk_baru=current_time
                )
                
                return jsonify({
                    "success": True,
                    "message": f"Absen {final_status} berhasil",
                    "data": {
                        "nama": user.get("nama"),
                        "kelas": user.get("kelas"),
                        "jam_masuk": current_time,
                        "status": final_status
                    }
                })
            
            elif status == "Pulang":
                # Absen Pulang
                if sudah_absen_masuk:
                    return jsonify({
                        "success": False,
                        "message": "Belum absen masuk",
                        "data": {
                            "nama": user.get("nama"),
                            "kelas": user.get("kelas")
                        }
                    }), 400
                
                if sudah_absen_pulang:
                    return jsonify({
                        "success": False,
                        "message": f"Sudah absen pulang pada {sudah_absen_pulang}",
                        "data": {
                            "nama": user.get("nama"),
                            "kelas": user.get("kelas"),
                            "jam_masuk": sudah_absen_masuk,
                            "jam_keluar": sudah_absen_pulang
                        }
                    }), 400
                
                # Absen pulang
                firebase.edit_absen(
                    uid, 
                    current_date, 
                    jam_keluar_baru=current_time
                )
                
                return jsonify({
                    "success": True,
                    "message": "Absen pulang berhasil",
                    "data": {
                        "nama": user.get("nama"),
                        "kelas": user.get("kelas"),
                        "jam_masuk": sudah_absen_masuk,
                        "jam_keluar": current_time
                    }
                })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Terjadi kesalahan: {str(e)}"
            }), 500

@api_blueprint.route('/send_whatsapp', methods=['POST'])
def send_whatsapp():
    data = request.get_json()
    
    if not data or 'nomor' not in data or 'pesan' not in data:
        return jsonify({
            "success": False,
            "message": "Nomor dan pesan diperlukan"
        }), 400
    
    nomor = data['nomor']
    pesan = data['pesan']
    
    try:
        url = "http://localhost:3000/send-message"
        payload = {
            "nomor": nomor,
            "pesan": pesan
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer GraceCantik"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Pesan WhatsApp berhasil dikirim",
                "response": response.json()
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Gagal mengirim pesan: {response.text}"
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Terjadi kesalahan: {str(e)}"
        }), 500

# Endpoint untuk generate token (untuk testing)
@api_blueprint.route('/generate_token/<uid>')
def generate_token(uid):
    token = hash_sha256(uid)
    return jsonify({
        "uid": uid,
        "token": token
    })

def get_whatsapp_headers():
    """Generate headers dengan token autentikasi"""
    return {
        'Authorization': f'Bearer {WHATSAPP_API_TOKEN}',
        'Content-Type': 'application/json'
    }

@api_blueprint.route("/whatsapp-status")
def whatsapp_status():
    """Get WhatsApp connection status dengan token"""
    try:
        response = requests.get(
            "http://localhost:3000/api/status", 
            headers=get_whatsapp_headers(),
            timeout=10
        )
        
        if response.status_code == 401:
            return jsonify({
                "status": "error",
                "error": "Token autentikasi tidak valid"
            }), 500
            
        data = response.json()
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error", 
            "error": f"Tidak dapat terhubung ke server bot Whatsapp"
        }), 500

@api_blueprint.route("/whatsapp-logout", methods=["POST"])
def whatsapp_logout():
    """Logout WhatsApp session dengan token"""
    try:
        print("🔄 Attempting WhatsApp logout...")
        
        response = requests.post(
            "http://localhost:3000/api/logout", 
            headers=get_whatsapp_headers(),
            timeout=60
        )
        
        if response.status_code == 401:
            return jsonify({
                "status": "error",
                "error": "Token autentikasi tidak valid"
            }), 500
            
        data = response.json()
        
        print(f"📡 Logout response status: {response.status_code}")
        print(f"📡 Logout response data: {data}")
        
        if response.status_code == 200:
            flash('WhatsApp berhasil logout. Silakan scan QR code baru.', 'success')
            return jsonify(data)
        else:
            error_msg = data.get("error", "Unknown error")
            flash(f'Gagal logout: {error_msg}', 'error')
            return jsonify(data), response.status_code
            
    except requests.exceptions.Timeout:
        error_msg = "Timeout: Server tidak merespons"
        print(f"❌ {error_msg}")
        flash(error_msg, 'error')
        return jsonify({"status": "error", "error": error_msg}), 500
        
    except requests.exceptions.ConnectionError:
        error_msg = "Tidak dapat terhubung ke server WhatsApp"
        print(f"❌ {error_msg}")
        flash(error_msg, 'error')
        return jsonify({"status": "error", "error": error_msg}), 500
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        flash(error_msg, 'error')
        return jsonify({"status": "error", "error": error_msg}), 500

@api_blueprint.route("/send-whatsapp-message", methods=["POST"])
def send_whatsapp_message():
    """Send message via WhatsApp dengan token"""
    try:
        data = request.get_json()
        nomor = data.get('nomor')
        pesan = data.get('pesan')
        
        if not nomor or not pesan:
            return jsonify({
                "status": "error",
                "error": "Nomor dan pesan wajib diisi"
            }), 400
            
        response = requests.post(
            "http://localhost:3000/api/send-message",
            headers=get_whatsapp_headers(),
            json={"nomor": nomor, "pesan": pesan},
            timeout=30
        )
        
        if response.status_code == 401:
            return jsonify({
                "status": "error",
                "error": "Token autentikasi tidak valid"
            }), 500
            
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Gagal mengirim pesan: {str(e)}"
        }), 500