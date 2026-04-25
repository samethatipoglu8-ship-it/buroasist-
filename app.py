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
            isim TEXT, vergi_no TEXT, telefon TEXT, tur TEXT,
            belge_durumu TEXT DEFAULT 'Bekleniyor',
            ucret INTEGER DEFAULT 0,
            odeme_durumu TEXT DEFAULT 'Ödenmedi',
            eklenme TEXT)"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS beyannameler (
            id SERIAL PRIMARY KEY,
            kullanici_id INTEGER REFERENCES kullanicilar(id),
            mukellef_id INTEGER REFERENCES mukellefler(id),
            beyanname_turu TEXT,
            son_gun TEXT,
            durum TEXT DEFAULT 'Bekliyor',
            ay TEXT)"""))
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

def mukellef_ekle(kullanici_id, isim, vergi_no, telefon, tur, ucret):
    with engine.connect() as conn:
        conn.execute(text("""INSERT INTO mukellefler 
            (kullanici_id,isim,vergi_no,telefon,tur,belge_durumu,ucret,odeme_durumu,eklenme) 
            VALUES (:ki,:i,:v,:t,:tu,:b,:u,:o,:e)"""),
            {"ki": kullanici_id, "i": isim, "v": vergi_no, "t": telefon,
             "tu": tur, "b": "Bekleniyor", "u": ucret, "o": "Ödenmedi",
             "e": datetime.now().strftime("%d.%m.%Y")})
        conn.commit()

def liste(kullanici_id):
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM mukellefler WHERE kullanici_id=:k"), conn, params={"k": kullanici_id})
    return df

def guncelle(mid, durum):
    with engine.connect() as conn:
        conn.execute(text("UPDATE mukellefler SET belge_durumu=:d WHERE id=:i"), {"d": durum, "i": mid})
        conn.commit()

def odeme_guncelle(mid, durum):
    with engine.connect() as conn:
        conn.execute(text("UPDATE mukellefler SET odeme_durumu=:d WHERE id=:i"), {"d": durum, "i": mid})
        conn.commit()

def beyanname_guncelle(bid, durum):
    with engine.connect() as conn:
        conn.execute(text("UPDATE beyannameler SET durum=:d WHERE id=:i"), {"d": durum, "i": bid})
        conn.commit()

def sil(mid):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM mukellefler WHERE id=:i"), {"i": mid})
        conn.commit()

def beyanname_listesi(kullanici_id):
    bugun = date.today()
    ay = bugun.strftime("%Y-%m")
    with engine.connect() as conn:
        mevcut = conn.execute(text("SELECT COUNT(*) FROM beyannameler WHERE kullanici_id=:k AND ay=:a"),
            {"k": kullanici_id, "a": ay}).fetchone()[0]
        if mevcut == 0:
            for bt in [("KDV", f"{bugun.year}-{bugun.month:02d}-28"),
                       ("Muhtasar", f"{bugun.year}-{bugun.month:02d}-26"),
                       ("SGK", f"{bugun.year}-{bugun.month:02d}-23"),
                       ("Damga Vergisi", f"{bugun.year}-{bugun.month:02d}-26")]:
                conn.execute(text("""INSERT INTO beyannameler 
                    (kullanici_id, beyanname_turu, son_gun, durum, ay)
                    VALUES (:k,:b,:s,'Bekliyor',:a)"""),
                    {"k": kullanici_id, "b": bt[0], "s": bt[1], "a": ay})
            conn.commit()
        df = pd.read_sql(text("SELECT * FROM beyannameler WHERE kullanici_id=:k AND ay=:a"),
            conn, params={"k": kullanici_id, "a": ay})
    return df

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
        st.header("Yeni Mükellef Ekle")
        isim = st.text_input("Ad Soyad")
        vno = st.text_input("Vergi No")
        tel = st.text_input("Telefon")
        tur = st.selectbox("Tür", ["Şahıs", "Limited", "Anonim"])
        ucret = st.number_input("Aylık Ücret (TL)", min_value=0, value=1500)
        if st.button("Ekle") and isim:
            mukellef_ekle(kullanici_id, isim, vno, tel, tur, ucret)
            st.rerun()
        st.divider()
        if st.button("Çıkış Yap"):
            st.session_state.kullanici = None
            st.rerun()

    st.title(f"📋 BuroAsist — {buro_adi}")

    df = liste(kullanici_id)

    # ANA METRİKLER
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Mükellef", len(df))
    c2.metric("⚠️ Belge Bekleyen", len(df[df.belge_durumu=="Bekleniyor"]) if not df.empty else 0)
    c3.metric("✅ Belge Gelen", len(df[df.belge_durumu=="Geldi"]) if not df.empty else 0)
    toplam_gelir = df["ucret"].sum() if not df.empty else 0
    odenen = df[df.odeme_durumu=="Ödendi"]["ucret"].sum() if not df.empty else 0
    c4.metric("💰 Aylık Gelir", f"{toplam_gelir:,} TL")
    c5.metric("❌ Tahsil Edilmedi", f"{toplam_gelir - odenen:,} TL")

    st.divider()

    t1, t2, t3, t4, t5 = st.tabs(["📊 Mükellefler", "💰 Ücret Takibi", "📅 Beyanname", "📱 WhatsApp", "🤖 AI Asistan"])

    with t1:
        if not df.empty:
            for _, r in df.iterrows():
                a, b, c, d, e, f = st.columns([3,1,2,2,2,1])
                a.write(f"**{r.isim}**")
                b.write(r.tur)
                c.write(r.telefon)
                with d:
                    sec = st.selectbox("Belge", ["Bekleniyor","Geldi"],
                        index=0 if r.belge_durumu=="Bekleniyor" else 1, key=f"d{r.id}")
                    if sec != r.belge_durumu:
                        guncelle(r.id, sec)
                        st.rerun()
                with e:
                    ode = st.selectbox("Ödeme", ["Ödenmedi","Ödendi"],
                        index=0 if r.odeme_durumu=="Ödenmedi" else 1, key=f"o{r.id}")
                    if ode != r.odeme_durumu:
                        odeme_guncelle(r.id, ode)
                        st.rerun()
                with f:
                    if st.button("🗑️", key=f"s{r.id}"):
                        sil(r.id)
                        st.rerun()
        else:
            st.info("Henüz mükellef eklenmedi.")

    with t2:
        st.subheader("💰 Ücret Takibi")
        if not df.empty:
            odenmemis = df[df.odeme_durumu=="Ödenmedi"]
            odenmis = df[df.odeme_durumu=="Ödendi"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.error(f"❌ Ödenmemiş: {len(odenmemis)} mükellef — {odenmemis['ucret'].sum():,} TL")
                for _, r in odenmemis.iterrows():
                    st.write(f"• **{r.isim}** — {r.ucret:,} TL — {r.telefon}")
            with col2:
                st.success(f"✅ Ödendi: {len(odenmis)} mükellef — {odenmis['ucret'].sum():,} TL")
                for _, r in odenmis.iterrows():
                    st.write(f"• **{r.isim}** — {r.ucret:,} TL")
        else:
            st.info("Mükellef yok")

    with t3:
        st.subheader("📅 Beyanname Takvimi")
        bdf = beyanname_listesi(kullanici_id)
        bugun = date.today()
        if not bdf.empty:
            for _, r in bdf.iterrows():
                son_gun = date.fromisoformat(r.son_gun)
                kalan = (son_gun - bugun).days
                a, b, c, d = st.columns([3,2,2,2])
                a.write(f"**{r.beyanname_turu}**")
                b.write(son_gun.strftime("%d.%m.%Y"))
                with c:
                    if kalan < 0:
                        st.error("⛔ Geçti")
                    elif kalan <= 3:
                        st.warning(f"⚠️ {kalan} gün kaldı")
                    else:
                        st.success(f"✅ {kalan} gün var")
                with d:
                    yeni = st.selectbox("", ["Bekliyor","Gönderildi"],
                        index=0 if r.durum=="Bekliyor" else 1, key=f"b{r.id}")
                    if yeni != r.durum:
                        beyanname_guncelle(r.id, yeni)
                        st.rerun()
                st.divider()

    with t4:
        st.subheader("📱 Belge Hatırlatma Mesajları")
        if not df.empty:
            bek = df[df.belge_durumu=="Bekleniyor"]
            if not bek.empty:
                for _, r in bek.iterrows():
                    st.warning(f"📞 {r.isim} — {r.telefon}")
                    st.code(f"Sayın {r.isim}, bu ayki belgelerinizi henüz almadık. Lütfen en kısa sürede iletiniz. Teşekkürler.")
                    st.divider()
            else:
                st.success("✅ Tüm mükelleflerden belge geldi!")
        else:
            st.info("Mükellef yok")

    with t5:
        st.subheader("🤖 Mevzuat ve Vergi Asistanı")
        if "mesajlar" not in st.session_state:
            st.session_state.mesajlar = []
        for m in st.session_state.mesajlar:
            if m["rol"] == "kullanici":
                st.chat_message("user").write(m["icerik"])
            else:
                st.chat_message("assistant").write(m["icerik"])
        soru = st.chat_input("Sorunuzu yazın...")
        if soru:
            st.session_state.mesajlar.append({"rol": "kullanici", "icerik": soru})
            st.chat_message("user").write(soru)
            with st.spinner("Düşünüyor..."):
                cevap = ai_sor(soru)
            st.session_state.mesajlar.append({"rol": "asistan", "icerik": cevap})
            st.chat_message("assistant").write(cevap)