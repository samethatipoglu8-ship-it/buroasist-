import streamlit as st
import pandas as pd
from datetime import datetime, date
import hashlib
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="BuroAsist", page_icon="📋", layout="wide")

groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
sb = create_client(st.secrets.get("SUPABASE_URL", ""), st.secrets.get("SUPABASE_KEY", ""))

def hashle(s):
    return hashlib.sha256(s.encode()).hexdigest()

def kayit_ol(adi, sifre, buro):
    sb.table("kullanicilar").insert({
        "kullanici_adi": adi,
        "sifre": hashle(sifre),
        "buro_adi": buro
    }).execute()
    return True

def giris(adi, sifre):
    r = sb.table("kullanicilar").select("*").eq("kullanici_adi", adi).eq("sifre", hashle(sifre)).execute()
    return r.data[0] if r.data else None

def m_ekle(kid, isim, vno, tel, tur, ucret, email):
    sb.table("mukellefler").insert({
        "kullanici_id": kid, "isim": isim, "vergi_no": vno,
        "telefon": tel, "tur": tur, "ucret": ucret, "email": email,
        "belge_durumu": "Bekleniyor", "odeme_durumu": "Ödenmedi",
        "eklenme": datetime.now().strftime("%d.%m.%Y")
    }).execute()

def m_liste(kid):
    r = sb.table("mukellefler").select("*").eq("kullanici_id", kid).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame(columns=["id","kullanici_id","isim","vergi_no","telefon","tur","belge_durumu","ucret","odeme_durumu","email","eklenme"])

def m_belge(mid, durum):
    sb.table("mukellefler").update({"belge_durumu": durum}).eq("id", mid).execute()

def m_odeme(mid, durum):
    sb.table("mukellefler").update({"odeme_durumu": durum}).eq("id", mid).execute()

def m_sil(mid):
    sb.table("mukellefler").delete().eq("id", mid).execute()

def b_liste(kid):
    bugun = date.today()
    ay = bugun.strftime("%Y-%m")
    r = sb.table("beyannameler").select("*").eq("kullanici_id", kid).eq("ay", ay).execute()
    if not r.data:
        for ad, gun in [("KDV", 28), ("Muhtasar", 26), ("SGK", 23), ("Damga Vergisi", 26)]:
            sb.table("beyannameler").insert({
                "kullanici_id": kid,
                "beyanname_turu": ad,
                "son_gun": f"{bugun.year}-{bugun.month:02d}-{gun:02d}",
                "durum": "Bekliyor",
                "ay": ay
            }).execute()
        r = sb.table("beyannameler").select("*").eq("kullanici_id", kid).eq("ay", ay).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def b_guncelle(bid, durum):
    sb.table("beyannameler").update({"durum": durum}).eq("id", bid).execute()

def ai_sor(soru):
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sen Türk vergi mevzuatı uzmanı bir mali müşavir asistanısın. Kısa ve net cevaplar ver."},
            {"role": "user", "content": soru}
        ]
    )
    return r.choices[0].message.content

if "kullanici" not in st.session_state:
    st.session_state.kullanici = None

if st.session_state.kullanici is None:
    st.title("📋 BuroAsist")
    g, k = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with g:
        adi = st.text_input("Kullanıcı Adı", key="g_adi")
        sifre = st.text_input("Şifre", type="password", key="g_sifre")
        if st.button("Giriş Yap"):
            u = giris(adi, sifre)
            if u:
                st.session_state.kullanici = u
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre yanlış!")

    with k:
        buro = st.text_input("Büro Adı")
        yadi = st.text_input("Kullanıcı Adı", key="k_adi")
        ysifre = st.text_input("Şifre", type="password", key="k_sifre")
        if st.button("Kayıt Ol"):
            if kayit_ol(yadi, ysifre, buro):
                st.success("Hesap oluşturuldu! Giriş yapabilirsiniz.")
            else:
                st.error("Kayıt başarısız. Tekrar deneyin.")

else:
    kid = st.session_state.kullanici["id"]
    buro_adi = st.session_state.kullanici["buro_adi"]

    with st.sidebar:
        st.write(f"👤 {buro_adi}")
        st.divider()
        st.subheader("Yeni Mükellef")
        isim = st.text_input("Ad Soyad")
        vno = st.text_input("Vergi No")
        tel = st.text_input("Telefon")
        email = st.text_input("Email")
        tur = st.selectbox("Tür", ["Şahıs", "Limited", "Anonim"])
        ucret = st.number_input("Aylık Ücret (TL)", min_value=0, value=1500)
        if st.button("Ekle") and isim:
            m_ekle(kid, isim, vno, tel, tur, ucret, email)
            st.rerun()
        st.divider()
        if st.button("Çıkış"):
            st.session_state.kullanici = None
            st.rerun()

    st.title(f"📋 BuroAsist — {buro_adi}")
    df = m_liste(kid)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam", len(df))
    c2.metric("⚠️ Belge Bekleyen", len(df[df.belge_durumu=="Bekleniyor"]) if not df.empty else 0)
    c3.metric("✅ Belge Gelen", len(df[df.belge_durumu=="Geldi"]) if not df.empty else 0)
    toplam = int(df["ucret"].sum()) if not df.empty else 0
    odendi = int(df[df.odeme_durumu=="Ödendi"]["ucret"].sum()) if not df.empty else 0
    c4.metric("💰 Toplam Gelir", f"{toplam:,} TL")
    c5.metric("❌ Tahsil Edilmedi", f"{toplam-odendi:,} TL")

    st.divider()
    t1, t2, t3, t4, t5 = st.tabs(["📊 Mükellefler", "💰 Ücret Takibi", "📅 Beyanname", "📱 WhatsApp", "🤖 AI Asistan"])

    with t1:
        if not df.empty:
            for _, r in df.iterrows():
                a,b,c,d,e,f = st.columns([3,1,2,2,2,1])
                a.write(f"**{r.isim}**")
                b.write(r.tur)
                c.write(r.telefon)
                with d:
                    sec = st.selectbox("Belge", ["Bekleniyor","Geldi"], index=0 if r.belge_durumu=="Bekleniyor" else 1, key=f"d{r.id}")
                    if sec != r.belge_durumu:
                        m_belge(r.id, sec)
                        st.rerun()
                with e:
                    ode = st.selectbox("Ödeme", ["Ödenmedi","Ödendi"], index=0 if r.odeme_durumu=="Ödenmedi" else 1, key=f"o{r.id}")
                    if ode != r.odeme_durumu:
                        m_odeme(r.id, ode)
                        st.rerun()
                with f:
                    if st.button("🗑️", key=f"s{r.id}"):
                        m_sil(r.id)
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
                st.error(f"❌ Ödenmemiş: {len(odenmemis)} kişi — {int(odenmemis['ucret'].sum()):,} TL")
                for _, r in odenmemis.iterrows():
                    st.write(f"• **{r.isim}** — {int(r.ucret):,} TL — {r.telefon}")
            with col2:
                st.success(f"✅ Ödendi: {len(odenmis)} kişi — {int(odenmis['ucret'].sum()):,} TL")
                for _, r in odenmis.iterrows():
                    st.write(f"• **{r.isim}** — {int(r.ucret):,} TL")
        else:
            st.info("Mükellef yok")

    with t3:
        st.subheader("📅 Beyanname Takvimi")
        bdf = b_liste(kid)
        bugun = date.today()
        if not bdf.empty:
            for _, r in bdf.iterrows():
                sg = date.fromisoformat(r.son_gun)
                kalan = (sg - bugun).days
                a,b,c,d = st.columns([3,2,2,2])
                a.write(f"**{r.beyanname_turu}**")
                b.write(sg.strftime("%d.%m.%Y"))
                with c:
                    if kalan < 0: st.error("⛔ Geçti")
                    elif kalan <= 3: st.warning(f"⚠️ {kalan} gün")
                    else: st.success(f"✅ {kalan} gün")
                with d:
                    yeni = st.selectbox("", ["Bekliyor","Gönderildi"], index=0 if r.durum=="Bekliyor" else 1, key=f"b{r.id}")
                    if yeni != r.durum:
                        b_guncelle(r.id, yeni)
                        st.rerun()
                st.divider()

    with t4:
        st.subheader("📱 Belge Hatırlatma")
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
            role = "user" if m["rol"] == "kullanici" else "assistant"
            st.chat_message(role).write(m["icerik"])
        soru = st.chat_input("Sorunuzu yazın...")
        if soru:
            st.session_state.mesajlar.append({"rol": "kullanici", "icerik": soru})
            st.chat_message("user").write(soru)
            with st.spinner("Düşünüyor..."):
                cevap = ai_sor(soru)
            st.session_state.mesajlar.append({"rol": "asistan", "icerik": cevap})
            st.chat_message("assistant").write(cevap)