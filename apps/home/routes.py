# -*- encoding: utf-8 -*-
import json, time
import wtforms
from datetime import datetime

from flask import render_template, request, redirect, url_for, Response, stream_with_context, jsonify, flash
from flask_login import login_required
from flask_login import login_required, current_user
from flask_wtf import FlaskForm

from apps import db
from apps.tasks import *
from apps.models import *
from apps.home import blueprint
from apps.decorators import role_required
from apps.authentication.models import Users
from apps.database.firebase_database import firebase

@blueprint.route('/')
def index():
    return redirect(url_for('authentication_blueprint.login'))

@blueprint.route('/home')
@login_required
def home():
    return render_template('pages/home.html', segment='home')


@blueprint.route('/dashboard')
@login_required
@role_required('admin', "superadmin")
def dashboard():
    return render_template('pages/dashboard.html', segment='dashboard') 

def convert_to_ddmmyyyy(tanggal_input):
    """
    Mengubah input tanggal menjadi dd-mm-yyyy.
    Bisa handle format yyyy-mm-dd (dari HTML date) atau dd-mm-yyyy (manual)
    """
    try:
        # coba parse sebagai yyyy-mm-dd
        date_obj = datetime.strptime(tanggal_input, "%Y-%m-%d")
        return date_obj.strftime("%d-%m-%Y")
    except ValueError:
        try:
            # coba parse sebagai dd-mm-yyyy
            date_obj = datetime.strptime(tanggal_input, "%d-%m-%Y")
            return date_obj.strftime("%d-%m-%Y")
        except ValueError:
            # default ke hari ini
            return datetime.now().strftime("%d-%m-%Y")


@blueprint.route('/absensi', methods=['GET', 'POST'])
@login_required
@role_required('admin', "superadmin")
def absensi():
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # default tanggal: hari ini
    tanggal_input_raw = datetime.now().strftime("%Y-%m-%d")
    tanggal_fix = datetime.now().strftime("%d-%m-%Y")

    # Ambil kelas, bisa dari form POST atau GET
    kelas = request.form.get("kelas") or request.args.get("kelas")

    # Jika user submit form POST untuk cek tanggal atau edit absen
    if request.method == "POST":
        # Ambil tanggal dari form, jika ada
        form_tanggal = request.form.get("tanggal")
        if form_tanggal:
            tanggal_input_raw = form_tanggal
            tanggal_fix = convert_to_ddmmyyyy(form_tanggal)

        # Jika ada uid dan status, berarti ini edit absen
        UID = request.form.get("uid")
        status_baru = request.form.get("status")
        if UID and status_baru:
            firebase.edit_absen(UID, tanggal_fix, status_baru)

    # Ambil ulang data users untuk tanggal yang sama
    users = firebase.filter_by_kelas(kelas) if kelas else firebase.get_all()
    
    # Process each user to get status, jam_masuk, and jam_keluar
    for u in users:
        absen_data = u.get("ABSEN", {}).get(tanggal_fix)
        
        if isinstance(absen_data, dict):
            # Format baru dengan jam masuk & keluar
            u["status"] = absen_data.get("status")
            u["jam_masuk"] = absen_data.get("jam_masuk")
            u["jam_keluar"] = absen_data.get("jam_keluar")
        elif isinstance(absen_data, str):
            # Format lama (hanya status string)
            u["status"] = absen_data
            u["jam_masuk"] = None
            u["jam_keluar"] = None
        else:
            # Tidak ada absen
            u["status"] = None
            u["jam_masuk"] = None
            u["jam_keluar"] = None

    total_siswa = len(users)
    sudah_absen = sum(1 for u in users if u.get("status"))
    belum_absen = total_siswa - sudah_absen

    return render_template(
        "siswa/absen_class.html",
        users=users,
        kelas=kelas,
        tanggal_input=tanggal_input_raw,  # ini dari form POST
        current_date=datetime.now().strftime("%Y-%m-%d"),
        total_siswa=total_siswa,
        sudah_absen=sudah_absen,
        belum_absen=belum_absen
    )

@blueprint.route('/siswa', methods=['GET', 'POST'])
@login_required
@role_required('admin', "superadmin")
def siswa():
    users = firebase.get_all()
    total_siswa = len(users)
    total_kelas = len(firebase.class_list())
    return render_template('siswa/siswa.html', users=users, total_siswa=total_siswa, total_kelas=total_kelas, segment='siswa_list') 

@blueprint.route('/edit-siswa', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def edit_siswa():
    try:
        uid_lama = request.form.get('uid_lama')
        nama = request.form.get('nama')
        kelas = request.form.get('kelas')
        gender = request.form.get('gender')
        uid_baru = request.form.get('uid_baru')
        
        # Panggil method update dari Firebase
        firebase.update_user(uid_lama, nama, gender, kelas, uid_baru)
        
        flash('Data siswa berhasil diupdate!', 'success')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('home_blueprint.siswa'))

@blueprint.route('/hapus-siswa', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def hapus_siswa():
    try:
        uid_hapus = request.form.get('uid_hapus')
        
        # Panggil method delete dari Firebase
        firebase.delete_user(uid_hapus)
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('home_blueprint.siswa'))

@blueprint.route('/siswa/add', methods=['POST'])
@login_required
@role_required('admin', "superadmin")
def add_siswa():
    nama = request.form.get("nama")
    kelas = request.form.get("kelas")
    gender = request.form.get("gender")
    uid = request.form.get("uid")

    firebase.create_user(nama, gender, kelas, uid)

    return redirect(url_for('home_blueprint.siswa'))

@blueprint.route('/siswa-rekap', methods=['GET'])
@login_required
@role_required('admin', "superadmin")
def siswa_rekap():
    return render_template('siswa/siswa_rekap.html', segment='siswa_list') 


@blueprint.route('/stream-absen')
def stream_absen():
    def event_stream():
        last_signature = None
        
        while True:
            try:
                # Ambil data terbaru dari Firebase
                current_users = firebase.get_all()
                
                # Buat signature yang lebih detail untuk deteksi perubahan
                signature_data = []
                for user in current_users:
                    user_absen = user.get('ABSEN', {})
                    # Gabungkan UID dan data absen terbaru
                    user_signature = f"{user.get('UID')}:{str(user_absen)}"
                    signature_data.append(user_signature)
                
                # Buat signature unik dari semua data
                current_signature = hash(tuple(signature_data))
                
                print(f"SSE Check - Last: {last_signature}, Current: {current_signature}")
                
                # Kirim update jika ada perubahan atau pertama kali
                if last_signature is None or current_signature != last_signature:
                    print("SSE: Data changed, sending update")
                    yield f"data: {json.dumps({'type': 'update', 'timestamp': datetime.now().isoformat()})}\n\n"
                    last_signature = current_signature
                else:
                    # Kirim heartbeat untuk maintain connection
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                
                time.sleep(1)  # Check setiap 3 detik
                
            except Exception as e:
                print(f"SSE Error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )

@blueprint.route('/api/absen-data')
def get_absen_data():
    try:
        tanggal_input_raw = request.args.get('tanggal', datetime.now().strftime("%Y-%m-%d"))
        tanggal_fix = convert_to_ddmmyyyy(tanggal_input_raw)
        kelas = request.args.get('kelas')
        
        # Ambil data terbaru
        users = firebase.filter_by_kelas(kelas) if kelas else firebase.get_all()
        
        # Process data
        processed_users = []
        for u in users:
            user_data = {
                'nama': u.get('nama', ''),
                'UID': u.get('UID', ''),
                'gender': u.get('gender', ''),
                'kelas': u.get('kelas', ''),
                'status': None,
                'jam_masuk': None,
                'jam_keluar': None
            }
            
            absen_data = u.get("ABSEN", {}).get(tanggal_fix)
            
            if isinstance(absen_data, dict):
                user_data["status"] = absen_data.get("status")
                user_data["jam_masuk"] = absen_data.get("jam_masuk")
                user_data["jam_keluar"] = absen_data.get("jam_keluar")
            elif isinstance(absen_data, str):
                user_data["status"] = absen_data
            else:
                user_data["status"] = None
            
            processed_users.append(user_data)

        total_siswa = len(processed_users)
        sudah_absen = sum(1 for u in processed_users if u.get("status"))
        belum_absen = total_siswa - sudah_absen

        return jsonify({
            'success': True,
            'users': processed_users,
            'total_siswa': total_siswa,
            'sudah_absen': sudah_absen,
            'belum_absen': belum_absen,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def getField(column): 
    if isinstance(column.type, db.Text):
        return wtforms.TextAreaField(column.name.title())
    if isinstance(column.type, db.String):
        return wtforms.StringField(column.name.title())
    if isinstance(column.type, db.Boolean):
        return wtforms.BooleanField(column.name.title())
    if isinstance(column.type, db.Integer):
        return wtforms.IntegerField(column.name.title())
    if isinstance(column.type, db.Float):
        return wtforms.DecimalField(column.name.title())
    if isinstance(column.type, db.LargeBinary):
        return wtforms.HiddenField(column.name.title())
    return wtforms.StringField(column.name.title()) 


@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    class ProfileForm(FlaskForm):
        pass

    readonly_fields = Users.readonly_fields
    full_width_fields = {"bio"}

    for column in Users.__table__.columns:
        if column.name == "id":
            continue

        field_name = column.name
        if field_name in full_width_fields:
            continue

        field = getField(column)
        setattr(ProfileForm, field_name, field)

    for field_name in full_width_fields:
        if field_name in Users.__table__.columns:
            column = Users.__table__.columns[field_name]
            field = getField(column)
            setattr(ProfileForm, field_name, field)

    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        readonly_fields.append("password")
        excluded_fields = readonly_fields
        for field_name, field_value in form.data.items():
            if field_name not in excluded_fields:
                setattr(current_user, field_name, field_value)

        db.session.commit()
        return redirect(url_for('home_blueprint.profile'))
    
    context = {
        'segment': 'profile',
        'form': form,
        'readonly_fields': readonly_fields,
        'full_width_fields': full_width_fields,
    }
    return render_template('pages/profile.html', **context)


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None

# Celery (to be refactored)
@blueprint.route('/tasks-test')
def tasks_test():
    
    input_dict = { "data1": "04", "data2": "99" }
    input_json = json.dumps(input_dict)

    task = celery_test.delay( input_json )

    return f"TASK_ID: {task.id}, output: { task.get() }"


# Custom template filter

@blueprint.app_template_filter("replace_value")
def replace_value(value, arg):
    return value.replace(arg, " ").title()
