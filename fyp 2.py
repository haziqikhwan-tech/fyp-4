import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Pinjaman Alat Ukur PUO", layout="wide", page_icon="🏗️")

DB_FILE = "database_final_v1.db"
LIMIT_JAM = 3 

# KREDENTIAL ADMIN
STAFF_USER = "admin"
STAFF_PASS = "puo123"

# ==========================================
# 2. FUNGSI PANGKALAN DATA (STABIL)
# ==========================================
def get_connection():
    """Membuka sambungan ke database dengan sokongan multi-threading."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    """Membina jadual jika belum wujud."""
    with get_connection() as conn:
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
                "TS141", "TS741", "TS140", "TS WAKAF", "PRISM 1", "PRISM 2", 
                "PRISM 3", "PRISM 4", "PRISM 5", "PRISM 6", "PRISM 7", "PRISM 8", 
                "TRIPOD 100", "TRIPOD 84", "TRIPOD 24", "TRIPOD 60", "TRIPOD 67", 
                "TRIPOD 97", "TRIPOD 10", "TRIPOD 38", "TRIPOD 27", "SUN FILTER 1", 
                "SUN FILTER 2", "SUN FILTER 3", "SUN FILTER 4", "STAFF 1", "STAFF 2", "STAFF 3"
            ]
            for alat in alatan_master:
                c.execute("INSERT OR IGNORE INTO alatan (alat, status, peminjam, kelas, tarikh, masa_tamat, disahkan) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (alat, "Tersedia", "-", "-", "-", "-", 0))
            conn.commit()

def get_data(table="alatan"):
    with get_connection() as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)

def rekod_sejarah(alat, nama, kelas, aksi):
    with get_connection() as conn:
        c = conn.cursor()
        waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.execute("INSERT INTO sejarah (alat, nama, kelas, aksi, waktu) VALUES (?, ?, ?, ?, ?)",
                  (alat, nama, kelas, aksi, waktu))
        conn.commit()

def hantar_permohonan(alat_list, nama, matrik, kelas):
    with get_connection() as conn:
        c = conn.cursor()
        tarikh_skrg = datetime.now().strftime("%d/%m/%Y")
        for alat in alat_list:
            c.execute("UPDATE alatan SET status='Menunggu Pengesahan', peminjam=?, kelas=?, tarikh=?, disahkan=0 WHERE alat=?", 
                      (f"{nama} ({matrik})", kelas, tarikh_skrg, alat))
            # Panggil rekod sejarah dalam satu transaksi
            waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            c.execute("INSERT INTO sejarah (alat, nama, kelas, aksi, waktu) VALUES (?, ?, ?, ?, ?)",
                      (alat, f"{nama} ({matrik})", kelas, "MOHON PINJAM", waktu))
        conn.commit()

def sahkan_oleh_admin(alat):
    with get_connection() as conn:
        c = conn.cursor()
        tamat = (datetime.now() + timedelta(hours=LIMIT_JAM)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE alatan SET status='Dipinjam', disahkan=1, masa_tamat=? WHERE alat=?", (tamat, alat))
        conn.commit()
    rekod_sejarah(alat, "-", "-", "DISAHKAN ADMIN")

def pulangkan_alat(alat):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT peminjam, kelas FROM alatan WHERE alat=?", (alat,))
        res = c.fetchone()
        peminjam = res[0] if res else "-"
        kelas = res[1] if res else "-"
        c.execute("UPDATE alatan SET status='Tersedia', peminjam='-', kelas='-', tarikh='-', masa_tamat='-', disahkan=0 WHERE alat=?", (alat,))
        conn.commit()
    rekod_sejarah(alat, peminjam, kelas, "PULANG")

# Initialize DB pada permulaan
init_db()

# ==========================================
# 3. NAVIGASI SIDEBAR
# ==========================================
st.sidebar.title("🛠️ MENU SISTEM")
menu = st.sidebar.selectbox("Pilih Halaman", ["🏠 STATUS ALAT", "📝 BORANG PINJAMAN", "⏳ TIMER & PEMULANGAN", "🔐 AKSES STAF"])

# ==========================================
# 4. HALAMAN 1: STATUS ALAT
# ==========================================
if menu == "🏠 STATUS ALAT":
    st.title("🏗️ Inventori Alatan Ukur PUO")
    df = get_data()
    
    # Styling table
    st.dataframe(
        df[['alat', 'status', 'peminjam', 'kelas']], 
        use_container_width=True, 
        hide_index=True
    )

# ==========================================
# 5. HALAMAN 2: BORANG PINJAMAN (STUDENT)
# ==========================================
elif menu == "📝 BORANG PINJAMAN":
    st.title("📝 Borang Permohonan Pinjaman")
    df = get_data()
    senarai_tersedia = df[df['status'] == 'Tersedia']['alat'].tolist()
    
    if not senarai_tersedia:
        st.warning("Semua alatan sedang digunakan.")
    else:
        with st.form("form_pinjam"):
            col1, col2 = st.columns(2)
            with col1:
                nama = st.text_input("Nama Penuh (Huruf Besar)").upper()
                matrik = st.text_input("No. Matrik").upper()
            with col2:
                kelas = st.text_input("Kelas (Contoh: DGU5A)").upper()
                pilihan = st.multiselect("Pilih Alatan", senarai_tersedia)
            
            submit = st.form_submit_button("HANTAR PERMOHONAN")
            if submit:
                if nama and matrik and kelas and pilihan:
                    hantar_permohonan(pilihan, nama, matrik, kelas)
                    st.success("Permohonan dihantar! Sila dapatkan pengesahan staf.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Sila isi semua maklumat!")

# ==========================================
# 6. HALAMAN 3: TIMER & PEMULANGAN
# ==========================================
elif menu == "⏳ TIMER & PEMULANGAN":
    st.title("⏳ Masa Pinjaman Aktif")
    df = get_data()
    aktif = df[df['disahkan'] == 1]
    
    if aktif.empty:
        st.info("Tiada pinjaman aktif buat masa ini.")
    else:
        for _, row in aktif.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.subheader(f"🛠️ {row['alat']}")
                    st.write(f"👤 {row['peminjam']}")
                with c2:
                    tamat_dt = datetime.strptime(row['masa_tamat'], "%Y-%m-%d %H:%M:%S")
                    baki = tamat_dt - datetime.now()
                    if baki.total_seconds() > 0:
                        st.metric("Baki Masa", str(baki).split('.')[0])
                    else:
                        st.error("⚠️ MASA TAMAT")
                with c3:
                    if st.button("PULANG", key=f"p_{row['alat']}", use_container_width=True):
                        pulangkan_alat(row['alat'])
                        st.rerun()
        
        # Refresh auto untuk timer
        time.sleep(5)
        st.rerun()

# ==========================================
# 7. HALAMAN 4: AKSES STAF
# ==========================================
elif menu == "🔐 AKSES STAF":
    st.title("🔐 Panel Pengesahan Staf")
    
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False

    if not st.session_state.is_logged_in:
        with st.columns(3)[1]:
            u = st.text_input("ID Staf")
            p = st.text_input("Kata Laluan", type="password")
            if st.button("Masuk", use_container_width=True):
                if u == STAFF_USER and p == STAFF_PASS:
                    st.session_state.is_logged_in = True
                    st.rerun()
                else:
                    st.error("Salah ID/Password")
    else:
        if st.sidebar.button("Log Keluar"):
            st.session_state.is_logged_in = False
            st.rerun()

        tab1, tab2, tab3 = st.tabs(["✅ PENGESAHAN", "📜 SEJARAH", "📊 DATA"])
        
        with tab1:
            st.subheader("Permohonan Menunggu Kelulusan")
            df = get_data()
            tunggu = df[df['status'] == "Menunggu Pengesahan"]
            if tunggu.empty:
                st.info("Tiada permohonan baru.")
            else:
                for _, row in tunggu.iterrows():
                    with st.expander(f"📦 {row['alat']} - {row['peminjam']}"):
                        st.write(f"Kelas: {row['kelas']} | Tarikh: {row['tarikh']}")
                        if st.button("SAHKAN SEKARANG", key=f"s_{row['alat']}"):
                            sahkan_oleh_admin(row['alat'])
                            st.success(f"{row['alat']} telah disahkan!")
                            time.sleep(1)
                            st.rerun()
        
        with tab2:
            st.subheader("Log Aktiviti Keseluruhan")
            st.dataframe(get_data("sejarah").sort_values(by='id', ascending=False), use_container_width=True, hide_index=True)
            
        with tab3:
            st.subheader("Pangkalan Data Mentah")
            st.dataframe(get_data(), use_container_width=True)
