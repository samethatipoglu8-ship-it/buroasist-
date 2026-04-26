import streamlit as st
import pandas as pd
from datetime import datetime, date
import hashlib
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="BuroAsist", page_icon="📋", layout="wide")

client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
supabase = create_client(
    st.secrets.get("SUPABASE_URL", ""),
    st.secrets.get("SUPABASE_KEY", "")
)

def sifre_hashle(sifre):
    return hashlib.sha256(sifre.encode()).hexdigest()

def kayit_ol(kullanici_adi, sifre, buro_adi):
    try:
        supabase.table("kullanicilar").insert({
            "kullanici_adi": kullanici_adi,
            "sifre": sifre_hashle(sifre),
            "buro_adi": buro_adi
        }).execute()
        return True
    except:
        return False

def giris_yap(kullanici_adi, sifre):
    sonuc = supabase.table("kullanicilar")\
        .select("*")\
        .eq("kullanici_adi", kullanici_adi)\
        .eq("sifre", sifre_hashle(sifre))\
        .execute()
    if sonuc.data:
        return sonuc.data[0]
    return None

def mukellef_ekle(kullanici_id, isim, vergi_no, telefon, tur, ucret, email):
    supabase.table("mukellefler").insert({
        "kullanici_id": kullanici_id,
        "isim": isim,
        "vergi_no": vergi_no,
        "telefon": telefon,
        "tur": tur,
        "ucret": ucret,
        "email": email,
        "belge_durumu": "Bekleniyor",
        "odeme_durumu": "Ödenmedi",
        "eklenme": datetime.now().strftime("%d.%m.%Y")
    }).execute()

def liste(kullanici_id):
    sonuc = supabase.table("mukellefler")\
        .select("*")\
        .eq("kullanici_id", kullanici_id)\
        .execute()
    if sonuc.data:
        return pd.DataFrame(sonuc.data)
    return pd.DataFrame()

def guncelle(mid, durum):
    supabase.table("mukellefler").update({"belge_durumu": durum}).eq("id", mid).execute()

def odeme_guncelle(mid, durum):
    supabase.table("mukellefler").update({"odeme_durumu": durum}).eq("id", mid).execute()

def sil(mid):
    supabase.table("mukellefler").delete().eq("id", mid).execute()

def beyanname_listesi(kullanici_id):
    bugun = date.today()
    ay = bugun.strftime("%Y-%m")
    sonuc = supabase.table("beyannameler")\
        .select("*")\
        .eq("kullanici_id", kullanici_id)\
        .eq("ay", ay)\
        .execute()
    if not sonuc.data:
        for bt in [
            ("KDV", f"{bugun.year}-{bugun.month:02d}-28"),
            ("Muhtasar", f"{bugun.year}-{bugun.month:02d}-26"),
            ("SGK", f"{bugun.year}-{bugun.month:02d}-23"),
            ("Damga Vergisi", f"{bugun.year}-{bugun.month:02d}-26")
        ]:
            supabase.table("beyannameler").insert({
                "kullanici_id": kullanici_id,
                "beyanname_turu": bt[0],
                "son_gun": bt[1],
                "durum": "Bekliyor",
                "ay": ay
            }).execute()
        sonuc = supabase.table("beyannameler")\
            .select("*")\
            .eq("kullanici_id", kullanici_id)\
            .eq("ay", ay)\
            .execute()
    return pd.DataFrame(sonuc.data) if sonuc.data else pd.DataFrame()

def beyanname_guncelle(bid, durum):
    supabase.table("beyannameler").update({"durum": durum}).eq("id", bid).execute()

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
                st.session_state.kullanici = {"id": sonuc["id"], "buro_adi": sonuc["buro_adi"], "adi": k_adi}
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
        email = st.text_input("Email")
        tur = st.selectbox("Tür", ["Şahıs", "Limited", "Anonim"])
        ucret = st.number_input("Aylık Ücret (TL)", min_value=0, value=1500)
        if st.button("Ekle") and isim:
            mukellef_ekle(kullanici_id, isim, vno, tel, tur, ucret, email)
            st.rerun()
        st.divider()
        if st.button("Çıkış Yap"):
            st.session_state.kullanici = None
            st.rerun()

    st.title(f"📋 BuroAsist — {buro_adi}")
    df = liste(kullanici_id)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Mükellef", len(df))
    c2.metric("⚠️ Belge Bekleyen", len(df[df.belge_durumu=="Bekleniyor"]) if not df.empty else 0)
    c3.metric("✅ Belge Gelen", len(df[df.belge_durumu=="Geldi"]) if not df.empty else 0)
    toplam_gelir = int(df["ucret"].sum()) if not df.empty else 0
    odenen = int(df[df.odeme_durumu=="Ödendi"]["ucret"].sum()) if not df.empty else 0
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
                st.error(f"❌ Ödenmemiş: {len(odenmemis)} mükellef — {int(odenmemis['ucret'].sum()):,} TL")
                for _, r in odenmemis.iterrows():
                    st.write(f"• **{r.isim}** — {int(r.ucret):,} TL — {r.telefon}")
            with col2:
                st.success(f"✅ Ödendi: {len(odenmis)} mükellef — {int(odenmis['ucret'].sum()):,} TL")
                for _, r in odenmis.iterrows():
                    st.write(f"• **{r.isim}** — {int(r.ucret):,} TL")
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