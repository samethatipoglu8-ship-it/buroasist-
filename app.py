import streamlit as st
import pandas as pd
from datetime import datetime, date
import hashlib
import plotly.graph_objects as go
import plotly.express as px
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="BuroAsist", page_icon="📋", layout="wide")

# ── Stil ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 16px 20px;
    border-left: 4px solid #4f8ef7;
    margin-bottom: 8px;
}
.metric-card.red  { border-left-color: #e53e3e; }
.metric-card.green{ border-left-color: #38a169; }
.metric-card.orange{ border-left-color: #dd6b20; }
.alert-box {
    background: #fff5f5;
    border: 1px solid #feb2b2;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 6px;
    font-size: 14px;
}
.alert-box.warn {
    background: #fffaf0;
    border-color: #fbd38d;
}
</style>
""", unsafe_allow_html=True)

# ── Bağlantılar ───────────────────────────────────────────────────────────────
groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
sb = create_client(st.secrets.get("SUPABASE_URL", ""), st.secrets.get("SUPABASE_KEY", ""))

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────
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
    return pd.DataFrame(r.data) if r.data else pd.DataFrame(columns=[
        "id","kullanici_id","isim","vergi_no","telefon","tur",
        "belge_durumu","ucret","odeme_durumu","email","eklenme"
    ])

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

# ── Gelir grafiği (son 6 ay Supabase'den) ─────────────────────────────────────
def gelir_grafigi(kid):
    r = sb.table("mukellefler").select("ucret,odeme_durumu,eklenme").eq("kullanici_id", kid).execute()
    if not r.data:
        return None
    df = pd.DataFrame(r.data)
    try:
        df["tarih"] = pd.to_datetime(df["eklenme"], format="%d.%m.%Y", errors="coerce")
    except Exception:
        return None
    df = df.dropna(subset=["tarih"])
    df["ay"] = df["tarih"].dt.strftime("%Y-%m")
    ozet = df.groupby(["ay","odeme_durumu"])["ucret"].sum().reset_index()
    aylar = sorted(ozet["ay"].unique())[-6:]
    ozet = ozet[ozet["ay"].isin(aylar)]
    odendi   = ozet[ozet["odeme_durumu"]=="Ödendi"].set_index("ay")["ucret"]
    odenmedi = ozet[ozet["odeme_durumu"]=="Ödenmedi"].set_index("ay")["ucret"]
    # Ay etiketlerini Türkçe göster
    ay_etiket = {a: datetime.strptime(a, "%Y-%m").strftime("%b %Y") for a in aylar}
    fig = go.Figure()
    fig.add_bar(x=[ay_etiket[a] for a in aylar], y=[odendi.get(a,0) for a in aylar],   name="Tahsil Edildi",  marker_color="#38a169")
    fig.add_bar(x=[ay_etiket[a] for a in aylar], y=[odenmedi.get(a,0) for a in aylar], name="Tahsil Edilmedi", marker_color="#e53e3e")
    fig.update_layout(
        barmode="group",
        title="Son 6 Ay Gelir Durumu (TL)",
        xaxis_title="Ay",
        yaxis_title="TL",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", y=1.1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#333333"),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#333333"))
    fig.update_yaxes(gridcolor="#f0f0f0", tickfont=dict(color="#333333"))
    return fig

# ── Kritik uyarılar ───────────────────────────────────────────────────────────
def kritik_uyarilar(df, bdf):
    uyarilar = []
    bugun = date.today()

    # Belge bekleyen mükellefler
    if not df.empty:
        bek = df[df.belge_durumu == "Bekleniyor"]
        for _, r in bek.iterrows():
            uyarilar.append(("red", f"📁 Belge bekleniyor: <b>{r.isim}</b>"))

    # Yaklaşan beyannameler (≤5 gün)
    if not bdf.empty:
        for _, r in bdf.iterrows():
            try:
                sg = date.fromisoformat(r.son_gun)
                kalan = (sg - bugun).days
                if r.durum == "Bekliyor":
                    if kalan < 0:
                        uyarilar.append(("red", f"⛔ <b>{r.beyanname_turu}</b> beyannamesi süresi geçti!"))
                    elif kalan <= 5:
                        uyarilar.append(("warn", f"⚠️ <b>{r.beyanname_turu}</b> son gün: {sg.strftime('%d.%m.%Y')} ({kalan} gün kaldı)"))
            except Exception:
                continue
    return uyarilar

# ── Session state ─────────────────────────────────────────────────────────────
if "kullanici" not in st.session_state:
    st.session_state.kullanici = None

# ═══════════════════════════════════════════════════════════════════════════════
# GİRİŞ EKRANI
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.kullanici is None:
    st.title("📋 BuroAsist")
    g, k = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with g:
        adi   = st.text_input("Kullanıcı Adı", key="g_adi")
        sifre = st.text_input("Şifre", type="password", key="g_sifre")
        if st.button("Giriş Yap"):
            u = giris(adi, sifre)
            if u:
                st.session_state.kullanici = u
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre yanlış!")

    with k:
        buro  = st.text_input("Büro Adı")
        yadi  = st.text_input("Kullanıcı Adı", key="k_adi")
        ysifre= st.text_input("Şifre", type="password", key="k_sifre")
        if st.button("Kayıt Ol"):
            if kayit_ol(yadi, ysifre, buro):
                st.success("Hesap oluşturuldu! Giriş yapabilirsiniz.")
            else:
                st.error("Kayıt başarısız. Tekrar deneyin.")

# ═══════════════════════════════════════════════════════════════════════════════
# ANA EKRAN
# ═══════════════════════════════════════════════════════════════════════════════
else:
    kid      = st.session_state.kullanici["id"]
    buro_adi = st.session_state.kullanici["buro_adi"]

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.write(f"👤 **{buro_adi}**")
        st.caption(f"📅 {date.today().strftime('%d.%m.%Y')}")
        st.divider()
        st.subheader("Yeni Mükellef")
        isim  = st.text_input("Ad Soyad")
        vno   = st.text_input("Vergi No")
        tel   = st.text_input("Telefon")
        email = st.text_input("Email")
        tur   = st.selectbox("Tür", ["Şahıs", "Limited", "Anonim"])
        ucret = st.number_input("Aylık Ücret (TL)", min_value=0, value=1500)
        if st.button("➕ Ekle", use_container_width=True) and isim:
            m_ekle(kid, isim, vno, tel, tur, ucret, email)
            st.rerun()
        st.divider()
        if st.button("🚪 Çıkış", use_container_width=True):
            st.session_state.kullanici = None
            st.rerun()

    # ── Başlık ────────────────────────────────────────────────────────────────
    st.title(f"📋 BuroAsist — {buro_adi}")

    # ── Veri ─────────────────────────────────────────────────────────────────
    df  = m_liste(kid)
    bdf = b_liste(kid)

    # ── Metrikler ─────────────────────────────────────────────────────────────
    toplam  = int(df["ucret"].sum()) if not df.empty else 0
    odendi  = int(df[df.odeme_durumu=="Ödendi"]["ucret"].sum()) if not df.empty else 0
    bek_cnt = len(df[df.belge_durumu=="Bekleniyor"]) if not df.empty else 0
    gel_cnt = len(df[df.belge_durumu=="Geldi"]) if not df.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Toplam Mükellef",    len(df))
    c2.metric("📁 Belge Bekleyen",     bek_cnt,  delta=f"-{bek_cnt}" if bek_cnt else None, delta_color="inverse")
    c3.metric("✅ Belge Gelen",        gel_cnt)
    c4.metric("💰 Tahsil Edildi",      f"{odendi:,} TL")
    c5.metric("❌ Tahsil Edilmedi",    f"{toplam-odendi:,} TL",
              delta=f"-{toplam-odendi:,} TL" if (toplam-odendi) else None, delta_color="inverse")

    st.divider()

    # ── Grafik + Uyarılar ─────────────────────────────────────────────────────
    col_grafik, col_uyari = st.columns([3, 2])

    with col_grafik:
        fig = gelir_grafigi(kid)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Grafik için henüz yeterli veri yok.")

    with col_uyari:
        st.subheader("🚨 Kritik Uyarılar")
        uyarilar = kritik_uyarilar(df, bdf)
        if uyarilar:
            for tip, mesaj in uyarilar:
                # HTML taglerini temizle
                temiz = mesaj.replace("<b>","**").replace("</b>","**")
                if tip == "red":
                    st.error(temiz)
                else:
                    st.warning(temiz)
        else:
            st.success("✅ Kritik uyarı yok.")

    st.divider()

    # ── Sekmeler ──────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs(["📊 Mükellefler", "💰 Ücret Takibi", "📅 Beyanname", "📱 WhatsApp", "🤖 AI Asistan"])

    # ── T1: Mükellefler ───────────────────────────────────────────────────────
    with t1:
        if not df.empty:
            for _, r in df.iterrows():
                a, b, c, d, e, f = st.columns([3,1,2,2,2,1])
                a.write(f"**{r.isim}**")
                b.write(r.tur)
                c.write(r.telefon)
                with d:
                    sec = st.selectbox("Belge", ["Bekleniyor","Geldi"],
                                       index=0 if r.belge_durumu=="Bekleniyor" else 1,
                                       key=f"d{r.id}")
                    if sec != r.belge_durumu:
                        m_belge(r.id, sec); st.rerun()
                with e:
                    ode = st.selectbox("Ödeme", ["Ödenmedi","Ödendi"],
                                       index=0 if r.odeme_durumu=="Ödenmedi" else 1,
                                       key=f"o{r.id}")
                    if ode != r.odeme_durumu:
                        m_odeme(r.id, ode); st.rerun()
                with f:
                    if st.button("🗑️", key=f"s{r.id}"):
                        m_sil(r.id); st.rerun()
        else:
            st.info("Henüz mükellef eklenmedi.")

    # ── T2: Ücret Takibi ──────────────────────────────────────────────────────
    with t2:
        st.subheader("💰 Ücret Takibi")
        if not df.empty:
            odenmemis = df[df.odeme_durumu=="Ödenmedi"]
            odenmis   = df[df.odeme_durumu=="Ödendi"]
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

    # ── T3: Beyanname ─────────────────────────────────────────────────────────
    with t3:
        st.subheader("📅 Beyanname Takvimi")
        bugun = date.today()
        if not bdf.empty:
            for _, r in bdf.iterrows():
                sg    = date.fromisoformat(r.son_gun)
                kalan = (sg - bugun).days
                a, b, c, d = st.columns([3,2,2,2])
                a.write(f"**{r.beyanname_turu}**")
                b.write(sg.strftime("%d.%m.%Y"))
                with c:
                    if kalan < 0:        st.error("⛔ Geçti")
                    elif kalan <= 3:     st.warning(f"⚠️ {kalan} gün")
                    else:                st.success(f"✅ {kalan} gün")
                with d:
                    yeni = st.selectbox("", ["Bekliyor","Gönderildi"],
                                        index=0 if r.durum=="Bekliyor" else 1,
                                        key=f"b{r.id}")
                    if yeni != r.durum:
                        b_guncelle(r.id, yeni); st.rerun()
                st.divider()

    # ── T4: WhatsApp ─────────────────────────────────────────────────────────
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

    # ── T5: AI Asistan ───────────────────────────────────────────────────────
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
