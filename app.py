import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3
import hashlib
from groq import Groq

st.set_page_config(page_title="BuroAsist", page_icon="📋", layout="wide")

client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))

def db():
    conn = sqlite3.connect("buroasist.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS kullanicilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi TEXT UNIQUE,
        sifre TEXT,
        buro_adi TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS mukellefler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER,
        isim TEXT, vergi_no TEXT, telefon TEXT,
        tur TEXT, belge_durumu TEXT DEFAULT 'Bekleniyor', eklenme TEXT)""")
    conn.commit()
    return conn

def sifre_hashle(sifre):
    return hashlib.sha256(sifre.encode()).hexdigest()

def kayit_ol(kullanici_adi, sifre, buro_adi):
    conn = db()
    try:
        conn.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, buro_adi) VALUES (?,?,?)",
            (kullanici_adi, sifre_hashle(sifre), buro_adi))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def giris_yap(kullanici_adi, sifre):
    conn = db()
    cursor = conn.execute("SELECT id, buro_adi FROM kullanicilar WHERE kullanici_adi=? AND sifre=?",
        (kullanici_adi, sifre_hashle(sifre)))
    sonuc = cursor.fetchone()
    conn.close()
    return sonuc

def mukellef_ekle(kullanici_id, isim, vergi_no, telefon, tur):
    conn = db()
    conn.execute("INSERT INTO mukellefler (kullanici_id,isim,vergi_no,telefon,tur,belge_durumu,eklenme) VALUES (?,?,?,?,?,?,?)",
        (kullanici_id, isim, vergi_no, telefon, tur, "Bekleniyor", datetime.now().strftime("%d.%m.%Y")))
    conn.commit()
    conn.close()

def liste(kullanici_id):
    conn = db()
    df = pd.read_sql("SELECT * FROM mukellefler WHERE kullanici_id=?", conn, params=(kullanici_id,))
    conn.close()
    return df

def guncelle(mid, durum):
    conn = db()
    conn.execute("UPDATE mukellefler SET belge_durumu=? WHERE id=?", (durum, mid))
    conn.commit()
    conn.close()

def sil(mid):
    conn = db()
    conn.execute("DELETE FROM mukellefler WHERE id=?", (mid,))
    conn.commit()
    conn.close()

def ai_sor(soru):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sen Türk vergi mevzuatı konusunda uzman bir mali müşavir asistanısın. Kısa ve net cevaplar ver."},
            {"role": "user", "content": soru}
        ]
    )
    return response.choices[0].message.content

# GİRİŞ EKRANI
if "kullanici" not in st.session_state:
    st.session_state.kullanici = None

if st.session_state.kullanici is None:
    st.title("📋 BuroAsist")
    sekme_giris, sekme_kayit = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with sekme_giris:
        st.subheader("Giriş Yap")
        k_adi = st.text_input("Kullanıcı Adı", key="giris_adi")
        k_sifre = st.text_input("Şifre", type="password", key="giris_sifre")
        if st.button("Giriş Yap"):
            sonuc = giris_yap(k_adi, k_sifre)
            if sonuc:
                st.session_state.kullanici = {"id": sonuc[0], "buro_adi": sonuc[1], "adi": k_adi}
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre yanlış!")

    with sekme_kayit:
        st.subheader("Yeni Hesap Oluştur")
        y_buro = st.text_input("Büro Adı")
        y_adi = st.text_input("Kullanıcı Adı", key="kayit_adi")
        y_sifre = st.text_input("Şifre", type="password", key="kayit_sifre")
        if st.button("Kayıt Ol"):
            if kayit_ol(y_adi, y_sifre, y_buro):
                st.success("Hesap oluşturuldu! Giriş yapabilirsiniz.")
            else:
                st.error("Bu kullanıcı adı alınmış!")

else:
    kullanici_id = st.session_state.kullanici["id"]
    buro_adi = st.session_state.kullanici["buro_adi"]

    with st.sidebar:
        st.write(f"👤 {buro_adi}")
        st.divider()
        st.header("Yeni Mukellef")
        isim = st.text_input("Ad")
        vno = st.text_input("Vergi No")
        tel = st.text_input("Telefon")
        tur = st.selectbox("Tur", ["Sahis", "Limited", "Anonim"])
        if st.button("Ekle") and isim:
            mukellef_ekle(kullanici_id, isim, vno, tel, tur)
            st.rerun()
        st.divider()
        if st.button("Çıkış Yap"):
            st.session_state.kullanici = None
            st.rerun()

    st.title(f"📋 BuroAsist — {buro_adi}")

    t1, t2, t3, t4 = st.tabs(["Mukellefler", "Beyanname Takvimi", "WhatsApp", "🤖 AI Asistan"])

    with t1:
        df = liste(kullanici_id)
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam", len(df))
        c2.metric("Bekleyen", len(df[df.belge_durumu=="Bekleniyor"]) if not df.empty else 0)
        c3.metric("Tamam", len(df[df.belge_durumu=="Geldi"]) if not df.empty else 0)
        st.divider()
        if not df.empty:
            for _, r in df.iterrows():
                a, b, c, d, e = st.columns([3,2,2,2,1])
                a.write(f"**{r.isim}**")
                b.write(r.tur)
                c.write(r.telefon)
                with d:
                    sec = st.selectbox("", ["Bekleniyor","Geldi"],
                        index=0 if r.belge_durumu=="Bekleniyor" else 1, key=f"d{r.id}")
                    if sec != r.belge_durumu:
                        guncelle(r.id, sec)
                        st.rerun()
                with e:
                    if st.button("X", key=f"s{r.id}"):
                        sil(r.id)
                        st.rerun()
        else:
            st.info("Mukellef yok")

    with t2:
        bugun = date.today()
        for b in [
            ("KDV", date(bugun.year, bugun.month, 28)),
            ("Muhtasar", date(bugun.year, bugun.month, 26)),
            ("SGK", date(bugun.year, bugun.month, 23)),
        ]:
            kalan = (b[1] - bugun).days
            a, b2, c = st.columns([3,2,2])
            a.write(f"**{b[0]}**")
            b2.write(b[1].strftime("%d.%m.%Y"))
            if kalan < 0:
                c.error("Gecti")
            elif kalan <= 3:
                c.warning(f"{kalan} gun kaldi")
            else:
                c.success(f"{kalan} gun var")
            st.divider()

    with t3:
        df = liste(kullanici_id)
        if not df.empty:
            bek = df[df.belge_durumu=="Bekleniyor"]
            if not bek.empty:
                for _, r in bek.iterrows():
                    st.warning(f"{r.isim} - {r.telefon}")
                    st.code(f"Sayin {r.isim}, belgelerinizi bekliyoruz.")
            else:
                st.success("Hepsinden belge geldi")
        else:
            st.info("Mukellef yok")

    with t4:
        st.subheader("🤖 Mevzuat ve Vergi Asistanı")
        if "mesajlar" not in st.session_state:
            st.session_state.mesajlar = []
        for m in st.session_state.mesajlar:
            if m["rol"] == "kullanici":
                st.chat_message("user").write(m["icerik"])
            else:
                st.chat_message("assistant").write(m["icerik"])
        soru = st.chat_input("Sorunuzu yazin...")
        if soru:
            st.session_state.mesajlar.append({"rol": "kullanici", "icerik": soru})
            st.chat_message("user").write(soru)
            with st.spinner("Dusunuyor..."):
                cevap = ai_sor(soru)
            st.session_state.mesajlar.append({"rol": "asistan", "icerik": cevap})
            st.chat_message("assistant").write(cevap)