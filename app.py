import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3
from groq import Groq

st.set_page_config(page_title="BuroAsist", page_icon="📋", layout="wide")

client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))

def db():
    conn = sqlite3.connect("buroasist.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS mukellefler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT, vergi_no TEXT, telefon TEXT,
        tur TEXT, belge_durumu TEXT DEFAULT 'Bekleniyor', eklenme TEXT)""")
    conn.commit()
    return conn

def ekle(isim, vergi_no, telefon, tur):
    conn = db()
    conn.execute("INSERT INTO mukellefler (isim,vergi_no,telefon,tur,belge_durumu,eklenme) VALUES (?,?,?,?,?,?)",
        (isim, vergi_no, telefon, tur, "Bekleniyor", datetime.now().strftime("%d.%m.%Y")))
    conn.commit()
    conn.close()

def liste():
    conn = db()
    df = pd.read_sql("SELECT * FROM mukellefler", conn)
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

st.title("📋 BuroAsist")

with st.sidebar:
    st.header("Yeni Mukellef")
    isim = st.text_input("Ad")
    vno = st.text_input("Vergi No")
    tel = st.text_input("Telefon")
    tur = st.selectbox("Tur", ["Sahis", "Limited", "Anonim"])
    if st.button("Ekle") and isim:
        ekle(isim, vno, tel, tur)
        st.rerun()

t1, t2, t3, t4 = st.tabs(["Mukellefler", "Beyanname Takvimi", "WhatsApp", "🤖 AI Asistan"])

with t1:
    df = liste()
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
    df = liste()
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
    st.info("Vergi, beyanname, mevzuat hakkında her şeyi sorabilirsiniz.")

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