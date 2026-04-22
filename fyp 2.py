import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from datetime import date, datetime, timedelta

# 1. KONFIGURASI PAGE
st.set_page_config(page_title="Sistem Pinjaman Alat Ukur PUO", layout="wide", page_icon="🏗️")

DB_FILE = "sistem_pinjaman.db"
LIMIT_JAM = 3 

# Kredential Staf/Admin
STAFF_USER = "admin"
STAFF_PASS = "puo123"

# 2. FUNGSI DATABASE
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alatan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alat TEXT UNIQUE,
                    status TEXT,
                    peminjam TEXT,
                    kelas TEXT,
                    tarikh TEXT,
                    masa_tamat TEXT
                )''')
    
    c.execute("SELECT COUNT(*) FROM alatan")
    if c.fetchone()[0] == 0:
        alatan_master = [
            "TS141", "TS741", "TS140", "TS WAKAF", "PRISM 1", "PRISM 2", "PRISM 3", "PRISM 4", 
            "PRISM 5", "PRISM 6", "PRISM 7", "PRISM 8", "TRIPOD 100", "TRIPOD 84", "TRIPOD 24", 
            "TRIPOD 60", "TRIPOD 67", "TRIPOD 97", "TRIPOD 10", "TRIPOD 38", "TRIPOD 27", 
            "SUN FILTER 1", "SUN FILTER 2", "SUN FILTER 3", "SUN FILTER 4", "STAFF 1", "STAFF 2", "STAFF 3"
        ]
        for alat in alatan_master:
            c.execute("INSERT INTO alatan (alat, status, peminjam, kelas, tarikh, masa_tamat) VALUES (?, ?, ?, ?, ?, ?)",
                      (alat, "Tersedia", "-", "-", "-", "-"))
    conn.commit()
    conn.close()

def get_data_from_db():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM alatan", conn)
    conn.close()
    return df

def proses_update_db(alat_list, status, peminjam="-", kelas="-", tarikh="-", masa_tamat="-"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for alat in alat_list:
        c.execute('''UPDATE alatan SET status=?, peminjam=?, kelas=?, tarikh=?, masa_tamat=? 
                     WHERE alat=?''', (status, peminjam, kelas, tarikh, masa_tamat, alat))
    conn.commit()
    conn.close()

init_db()
df = get_data_from_db()

# 3. SIDEBAR NAVIGATION
st.sidebar.header("MENU NAVIGASI")
menu = st.sidebar.selectbox("Pilih Halaman", ["🏠 UTAMA", "📝 BORANG PINJAMAN STUDENT", "⏳ STATUS & TIMER", "🔐 AKSES STAF"])

# 4. HALAMAN UTAMA (TAMBAH DATABASE VIEW)
if menu == "🏠 UTAMA":
    st.title("🏗️ Sistem Pinjaman Alat Ukur PUO")
    st.subheader("Selamat Datang ke Sistem Digital Geomatik")
    
    tersedia = len(df[df['status'] == 'Tersedia'])
    dipinjam = len(df[df['status'] == 'Dipinjam'])
    
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("Alat Tersedia Untuk Dipinjam", f"{tersedia}")
    col_stat2.metric("Sedang Digunakan", f"{dipinjam}")
    
    st.markdown("---")
    # --- JADUAL DATABASE DI HALAMAN UTAMA ---
    st.subheader("📁 Jadual Status Inventori Semasa")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.info("Sila ke menu 'Borang Pinjaman' untuk melakukan urusan pinjaman alat.")

# 5. BORANG PINJAMAN STUDENT
elif menu == "📝 BORANG PINJAMAN STUDENT":
    st.title("📝 Borang Pinjaman Student")
    senarai_tersedia = df[df['status'] == 'Tersedia']['alat'].tolist()
    
    if senarai_tersedia:
        with st.form("form_pinjam", clear_on_submit=True):
            nama = st.text_input("Nama Penuh").upper()
            matrik = st.text_input("No. Matrik")
            kelas = st.text_input("Kelas (e.g. DGU5A)").upper()
            pilihan_alat = st.multiselect("Pilih Alat-alat yang ingin dipinjam", senarai_tersedia)
            
            if st.form_submit_button("SAHKAN PINJAMAN"):
                if nama and matrik and kelas and pilihan_alat:
                    waktu_tamat = datetime.now() + timedelta(hours=LIMIT_JAM)
                    t_str = waktu_tamat.strftime("%Y-%m-%d %H:%M:%S")
                    d_str = date.today().strftime("%d/%m/%Y")
                    
                    proses_update_db(pilihan_alat, "Dipinjam", nama, kelas, d_str, t_str)
                    st.success("Pinjaman Berjaya!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Sila isi semua maklumat!")
    else:
        st.error("Semua alat sedang dipinjam.")

# 6. STATUS & TIMER
elif menu == "⏳ STATUS & TIMER":
    st.title("⏳ Pemantauan Baki Masa")
    waktu_sekarang = datetime.now()
    dipinjam_df = df[df['status'] == "Dipinjam"]
    
    if dipinjam_df.empty:
        st.write("Tiada alat yang sedang dipinjam.")
    else:
        for index, row in dipinjam_df.iterrows():
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                st.write(f"**{row['alat']}**")
                st.caption(f"👤 {row['peminjam']} ({row['kelas']})")
            with col2:
                t_tamat = datetime.strptime(row['masa_tamat'], "%Y-%m-%d %H:%M:%S")
                baki = t_tamat - waktu_sekarang
                if baki.total_seconds() > 0:
                    m, s = divmod(int(baki.total_seconds()), 60)
                    h, m = divmod(m, 60)
                    st.warning(f"⏱️ {h:d}j {m:02d}m {s:02d}s")
                else:
                    proses_update_db([row['alat']], "Tersedia")
                    st.rerun()
            with col3:
                st.button("PULANG", key=f"btn_{row['alat']}", on_click=proses_update_db, args=([row['alat']], "Tersedia"))
            st.divider()
    time.sleep(5)
    st.rerun()

# 7. AKSES STAF (LOGIN UNTUK DOWNLOAD SAHAJA)
elif menu == "🔐 AKSES STAF":
    st.title("🔐 Panel Kawalan Staf")
    
    user_in = st.text_input("Username Admin")
    pass_in = st.text_input("Password Admin", type="password")
    
    if user_in == STAFF_USER and pass_in == STAFF_PASS:
        st.success("Akses Diterima.")
        st.markdown("---")
        
        # Butang Download hanya ada dalam ni
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button(
                    label="📥 Muat Turun Fail Database (.db)",
                    data=f,
                    file_name="sistem_pinjaman_puo.db",
                    mime="application/octet-stream"
                )
        st.info("Gunakan fail .db ini untuk tujuan audit atau backup data.")
            
    elif user_in or pass_in:
        st.error("Username atau Password salah!")
