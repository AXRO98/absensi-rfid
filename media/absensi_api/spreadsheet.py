from datetime import datetime
import gspread

# Connect to Google Spreadsheets
gc = gspread.service_account(filename='apps/absensi_api/rfid-config.json')
sheets = gc.open_by_key('17wSfA2LuFGINSTH4h9fl2NAd1iLdputJXoB7jhkRIBw')
tabel = sheets.worksheet("ABSENSI")

uid_list = tabel.col_values(4)[3:50]
tanggal_list = tabel.row_values(3)[4:]

def sinkron_data_db_server():
    return {
        'uid': uid_list,
        'name': tabel.col_values(2)[3:50]
    }

def cek_uid(uid):
    return uid in uid_list

def cek_nama(baris_uid):
    return tabel.cell(baris_uid, 2).value

def cek_uid_and_absen_posisi(uid):
    baris_uid = 4
    for uid_ in uid_list:
        if uid_ == uid:
            column_absen = len(tanggal_list) + 4
            return baris_uid, column_absen
        baris_uid += 1
    return None, None  # If UID is not found

def mark_absen_x():
    last_column = len(tanggal_list) + 4
    updates = []
    for row in range(4, len(uid_list) + 4):
        if not tabel.cell(row, last_column).value:
            updates.append({
                'range': f'{gspread.utils.rowcol_to_a1(row, last_column)}',
                'values': [['✘']]
            })
    
    if updates:
        tabel.batch_update(updates)
        print(f"Menandai absen yang kosong di kolom {last_column} dengan '✘'.")
    else:
        print(f"Tidak ada absen yang kosong di kolom {last_column}.")

def cek_tanggal():
    today = datetime.now().strftime('%d/%m/%y')
    return today in tanggal_list

def create_tanggal():
    global tanggal_list  # Declare tanggal_list as global first
    mark_absen_x()  # Fill yesterday's absence with '✘'
    next_column = len(tanggal_list) + 5
    today = datetime.now().strftime('%d/%m/%y')
    tabel.update_cell(3, next_column, today)
    tanggal_list.append(today)  # Append the new date
    print(f"Menambahkan tanggal {today} di kolom {next_column}")
    return today

from apps.db_json import update_status

def add_absen(uid):
    if not cek_uid(uid):
        return {
            'status': 'failed',
            'result': 'UID Tidak Terdaftar'
        }
    
    if not cek_tanggal():
        create_tanggal()

    baris_uid, kolom_absen = cek_uid_and_absen_posisi(uid)
    if not baris_uid or not kolom_absen:
        return {
            'status': 'failed',
            'result': 'Posisi absensi tidak ditemukan'
        }
    
    if tabel.cell(baris_uid, kolom_absen).value == '✅':
        return {
            'status': 'failed',
            'result': 'Absen sudah ada'
        }

    tabel.update_cell(baris_uid, kolom_absen, '✅')

    # 🔥 Update database.json juga
    update_status(uid, "hadir")

    return {
        'status': 'success',
        'result': f'UID {uid} berhasil absen dan status di DB diperbarui'
    }