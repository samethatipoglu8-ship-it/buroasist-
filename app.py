import streamlit as st
import pandas as pd
from datetime import datetime, date
import hashlib
from groq import Groq
from sqlalchemy import create_engine, text

st.set_page_config(page_title="BuroAsist", page_icon="📋", layout="wide")

client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
engine = create_engine(st.secrets.get("DATABASE_URL", ""))

def db_init():
    with engine.connect() as conn:
        conn.execute(text("""CREATE TABLE IF NOT EXISTS kullanicilar (
            id SERIAL PRIMARY KEY,
            kullanici_adi TEXT UNIQUE NOT NULL,
            sifre TEXT NOT NULL,
            buro_adi TEXT)"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS mukellefler (
            id SERIAL PRIMARY KEY,
            kullanici_id INTEGER REFERENCES kullanicilar(id),
            isim TEXT, vergi_no TEXT, telefon TEXT,
            tur TEXT, belge_durumu TEXT DEFAULT 'Bekleniyor', eklenme TEXT)"""))
        conn.commit()

db_init()

def sifre_hashle(sifre):
    return hashlib.sha256(sifre.encode()).hexdigest()

def kayit_ol(kullanici_adi, sifre, buro_adi):
    try:
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO kullanicilar (kullanici_adi, sifre, buro_adi) VALUES (:k, :s, :b)"),
                {"k": kullanici_adi, "s": sifre_hashle(sifre), "b": buro_adi})
            conn.commit()
        return True
    except:
        return False

def giris_yap(kullanici_adi, sifre):
    with engine.connect() as conn:
        sonuc = conn.execute(text("SELECT id, buro_adi FROM kullanicilar WHERE kullanici_adi=:k AND sifre=:s"),
            {"k": kullanici_adi, "s": sifre_hashle(sifre)}).fetchone()
    return sonuc

def mukellef_ekle(kullanici_id, isim, vergi_no, telefon, tur):
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO mukellefler (kullanici_id,isim,vergi_no,telefon,tur,belge_durumu,eklenme) VALUES (:ki,:i,:v,:t,:tu,:b,:e)"),
            {"ki": kullanici_id, "i": isim, "v": vergi_no, "t": telefon, "tu": tur, "b": "Bekleniyor", "e": datetime.now().strftime("%d.%m.%Y")})
        conn.commit()

def liste(kullanici_id):
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM mukellefler WHERE kullanici_id=:k"), conn, params={"k": kullanici_id})
    return df

def guncelle(mid, durum):
    with engine.connect() as conn:
        conn.execute(text("UPDATE mukellefler SET belge_durumu=:d WHERE id=:i"), {"d": durum, "i": mid})
        conn.commit()

def sil(mid):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM mukellefler WHERE id=:i"), {"i": mid})
        conn.commit()

def ai_sor(soru):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sen Türk vergi mevzuatı konusunda uzman bir mali müşavir asistanısın. Kısa ve net cevaplar ver."},
            {"role": "user", "content": soru}
        ]
    )
    return response.choices[0].message.content

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