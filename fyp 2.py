import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from datetime import date, datetime, timedelta

# 1. KONFIGURASI PAGE
st.set_page_config(page_title="Sistem Pinjaman Alat Ukur PUO", layout="wide", page_icon="🏗️")

# NAMA DATABASE (Guna nama baru untuk elak error lama)
DB_FILE = "database_final_v1.db"
LIMIT_JAM = 3 

# KREDENTIAL ADMIN
STAFF_USER = "admin"
STAFF_PASS = "puo123"

# 2. FUNGSI DATABASE (VERSI STABIL)
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Table Alatan
    c.execute('''CREATE TABLE IF NOT EXISTS alatan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alat TEXT UNIQUE,
                    status TEXT,
                    peminjam TEXT,
                    kelas TEXT,
                    tarikh TEXT,
                    masa_tamat TEXT,
                    disahkan INTEGER DEFAULT 0
                )''')
    # Table Sejarah
    c.execute('''CREATE TABLE IF NOT EXISTS sejarah (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alat TEXT,
                    nama TEXT,
                    kelas TEXT,
                    aksi TEXT,
                    waktu TEXT
                )''')
    
    # Masukkan Data Master Jika Kosong
    c.execute("SELECT COUNT(*) FROM alatan")
    if c.fetchone()[0] == 0:
        alatan_master = [
            "TS141", "TS741", "TS140", "TS WAKAF", "PRISM 1", "PRISM 2", "PRISM 3", "PRISM 4", 
            "PRISM 5", "PRISM 6", "PRISM 7", "PRISM 8", "TRIPOD 100", "TRIPOD 84", "TRIPOD 24", 
            "TRIPOD 60", "TRIPOD 67", "TRIPOD 97", "TRIPOD 10", "TRIPOD 38", "TRIPOD 27", 
            "SUN FILTER 1", "SUN FILTER 2", "SUN FILTER 3", "SUN FILTER 4", "STAFF 1", "STAFF 2", "STAFF 3"
        ]
        for alat in alatan_master:
            c.execute("INSERT OR IGNORE INTO alatan (alat, status, peminjam, kelas, tarikh, masa_tamat, disahkan) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (alat, "Tersedia", "-", "-", "-", "-", 0))
    conn.commit()
    conn.close()

def get_data(table="alatan"):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def rekod_sejarah(alat, nama, kelas, aksi):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO sejarah (alat, nama, kelas, aksi, waktu) VALUES (?, ?, ?, ?, ?)",
              (alat, nama, kelas, aksi, waktu))
    conn.commit()
    conn.close()

def hantar_permohonan(alat_list, nama, matrik, kelas):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    tarikh_skrg = date.today().strftime("%d/%m/%Y")
    for alat in alat_list:
        # Letak status Menunggu Pengesahan supaya Admin boleh Tick
        c.execute("UPDATE alatan SET status='Menunggu Pengesahan', peminjam=?, kelas=?, tarikh=?, disahkan=0 WHERE alat=?", 
                  (f"{nama} ({matrik})", kelas, tarikh_skrg, alat))
        rekod_sejarah(alat, nama, kelas, "MOHON PINJAM")
    conn.commit()
    conn.close()

def sahkan_oleh_admin(alat):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Timer mula bila admin tekan TICK
    tamat = (datetime.now() + timedelta(hours=LIMIT_JAM)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE alatan SET status='Dipinjam', disahkan=1, masa_tamat=? WHERE alat=?", (tamat, alat))
    conn.commit()
    conn.close()
    rekod_sejarah(alat, "-", "-", "DISAHKAN ADMIN")

def pulangkan_alat(alat):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT peminjam, kelas FROM alatan WHERE alat=?", (alat,))
    res = c.fetchone()
    rekod_sejarah(alat, res[0] if res else "-", res[1] if res else "-", "PULANG")
    c.execute("UPDATE alatan SET status='Tersedia', peminjam='-', kelas='-', tarikh='-', masa_tamat='-', disahkan=0 WHERE alat=?", (alat,))
    conn.commit()
    conn.close()

# INITIALIZE
init_db()

# 3. SIDEBAR NAVIGATION
st.sidebar.title("MENU UTAMA")
menu = st.sidebar.selectbox("Pilih Halaman", ["🏠 STATUS ALAT", "📝 BORANG PINJAMAN", "⏳ TIMER & PEMULANGAN", "🔐 AKSES STAF"])

# 4. HALAMAN STATUS
if menu == "🏠 STATUS ALAT":
    st.title("🏗️ Sistem Pinjaman Alat Ukur PUO")
    df = get_data()
    st.subheader("Senarai Inventori & Status Semasa")
    # Papar table yang senang student baca
    st.dataframe(df[['alat', 'status', 'peminjam', 'kelas']], use_container_width=True, hide_index=True)

# 5. HALAMAN BORANG (STUDENT)
elif menu == "📝 BORANG PINJAMAN":
    st.title("📝 Borang Pinjaman Alat")
    df = get_data()
    senarai_tersedia = df[df['status'] == 'Tersedia']['alat'].tolist()
    
    with st.form("form_pinjam", clear_on_submit=True):
        nama = st.text_input("Nama Penuh").upper()
        matrik = st.text_input("No. Matrik").upper()
        kelas = st.text_input("Kelas (Contoh: DGU5A)").upper()
        pilihan = st.multiselect("Pilih Alatan", senarai_tersedia)
        
        if st.form_submit_button("HANTAR PERMOHONAN"):
            if nama and matrik and kelas and pilihan:
                hantar_permohonan(pilihan, nama, matrik, kelas)
                st.success("Permohonan berjaya dihantar! Sila jumpa staf untuk pengesahan alat.")
                time.sleep(1); st.rerun()
            else:
                st.error("Sila isi semua ruangan!")

# 6. HALAMAN TIMER
elif menu == "⏳ TIMER & PEMULANGAN":
    st.title("⏳ Masa Pinjaman Aktif")
    df = get_data()
    # Hanya tunjuk alat yang dah DISAHKAN oleh Admin
    aktif = df[df['disahkan'] == 1]
    
    if aktif.empty:
        st.info("Tiada alatan yang sedang dipinjam buat masa ini.")
    else:
        for _, row in aktif.iterrows():
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.write(f"**{row['alat']}**")
                st.caption(f"👤 {row['peminjam']} | 📍 {row['kelas']}")
            with c2:
                # Kira baki masa
                tamat_dt = datetime.strptime(row['masa_tamat'], "%Y-%m-%d %H:%M:%S")
                baki = tamat_dt - datetime.now()
                if baki.total_seconds() > 0:
                    st.warning(f"Baki: {str(baki).split('.')[0]}")
                else:
                    st.error("MASA TAMAT")
                    pulangkan_alat(row['alat']); st.rerun()
            with c3:
                if st.button("PULANG", key=f"btn_{row['alat']}"):
                    pulangkan_alat(row['alat']); st.rerun()
            st.divider()
    # Auto-refresh setiap 10 saat untuk timer
    time.sleep(10); st.rerun()

# 7. HALAMAN ADMIN (TICK DI SINI)
elif menu == "🔐 AKSES STAF":
    st.title("🔐 Panel Kawalan Staf")
    user = st.text_input("ID Staf")
    pw = st.text_input("Kata Laluan", type="password")
    
    if user == STAFF_USER and pw == STAFF_PASS:
        st.success("Log Masuk Berjaya.")
        tab1, tab2, tab3 = st.tabs(["✅ PENGESAHAN (TICK)", "📜 SEJARAH", "📊 DATA MENTAH"])
        
        with tab1:
            st.subheader("Permohonan Menunggu Pengesahan")
            df = get_data()
            tunggu = df[df['status'] == "Menunggu Pengesahan"]
            if tunggu.empty:
                st.info("Tiada permohonan baru untuk disahkan.")
            else:
                for _, row in tunggu.iterrows():
                    col1, col2, col3 = st.columns([2, 4, 1])
                    col1.write(f"**{row['alat']}**")
                    col2.write(f"Peminjam: {row['peminjam']} ({row['kelas']})")
                    if col3.button("✔️", key=f"tick_{row['alat']}"):
                        sahkan_oleh_admin(row['alat'])
                        st.success(f"{row['alat']} Disahkan!")
                        time.sleep(0.5); st.rerun()
                    st.divider()
        
        with tab2:
            st.subheader("Rekod Pinjaman Lampau")
            st.dataframe(get_data("sejarah").sort_values(by='id', ascending=False), use_container_width=True, hide_index=True)
            
        with tab3:
            st.subheader("Database Inventori")
            st.dataframe(get_data(), use_container_width=True)
            
    elif user or pw:
        st.error("ID atau Kata Laluan Salah!")
