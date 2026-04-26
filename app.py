import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import hashlib
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="BuroAsist", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── Ana içerik yazı rengi (sidebar ve butonlar hariç) ── */
.main p, .main span:not(button span), .main li, .main td, .main th,
.main label, .main h1, .main h2, .main h3, .main h4,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stText"] {
    color: #1a1a2e !important;
}

/* ── Buton yazıları beyaz kalsın ── */
.stButton button, .stButton button span,
.stButton button p, .stButton button div {
    color: white !important;
}
.stDownloadButton button, .stDownloadButton button span {
    color: #1a1a2e !important;
}

/* ── Chat mesajları ── */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
    color: #1a1a2e !important;
}

.main .block-container {
    padding: 2rem 2.5rem 3rem 2.5rem;
    max-width: 1400px;
}

/* ── Arka plan ── */
.stApp {
    background: #f8f7f4;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1a1a2e !important;
    border-right: 1px solid #2d2d4e;
}
[data-testid="stSidebar"] * {
    color: #e8e8f0 !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #2d2d4e !important;
    border: 1px solid #3d3d6e !important;
    color: #e8e8f0 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] label {
    color: #a8a8c8 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stSidebar"] .stButton button {
    background: #4f46e5 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: #4338ca !important;
    transform: translateY(-1px) !important;
}

/* ── Başlık alanı ── */
h1 {
    font-family: 'Instrument Serif', serif !important;
    font-size: 2.2rem !important;
    color: #1a1a2e !important;
    font-weight: 400 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0 !important;
}
h2, h3 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #1a1a2e !important;
    font-weight: 600 !important;
}

/* ── Metrik kartlar ── */
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e8e4de;
    border-radius: 14px;
    padding: 1.2rem 1.4rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #888 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #1a1a2e !important;
}

/* ── Input alanları ── */
.stTextInput input, .stNumberInput input {
    background: white !important;
    border: 1.5px solid #e0dbd3 !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.9rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
    color: #1a1a2e !important;
    transition: border-color 0.2s !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,0.1) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: white !important;
    border: 1.5px solid #e0dbd3 !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #1a1a2e !important;
}
.stSelectbox > div > div > div,
.stSelectbox [data-baseweb="select"] span,
.stSelectbox [data-baseweb="select"] div {
    color: #1a1a2e !important;
}
/* Dropdown liste seçenekleri */
[data-baseweb="popover"] li,
[data-baseweb="popover"] div,
[data-baseweb="menu"] li {
    color: #1a1a2e !important;
    background: white !important;
}

/* ── Butonlar ── */
.stButton button {
    background: #1a1a2e !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.2rem !important;
    transition: all 0.2s !important;
    letter-spacing: 0.01em !important;
}
.stButton button:hover {
    background: #2d2d4e !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(26,26,46,0.25) !important;
}

/* ── Download butonu ── */
.stDownloadButton button {
    background: white !important;
    color: #1a1a2e !important;
    border: 1.5px solid #e0dbd3 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stDownloadButton button:hover {
    border-color: #4f46e5 !important;
    color: #4f46e5 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: white;
    border-radius: 12px;
    padding: 4px;
    border: 1px solid #e8e4de;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    color: #444 !important;
    padding: 0.5rem 1rem !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] * {
    color: #444 !important;
}
.stTabs [aria-selected="true"] {
    background: #1a1a2e !important;
    color: white !important;
}
.stTabs [aria-selected="true"] * {
    color: white !important;
}

/* ── Sidebar input label'ları ── */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] p {
    color: #a8a8c8 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: white !important;
    border: 1px solid #e8e4de !important;
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
    padding: 0.9rem 1.2rem !important;
}
.streamlit-expanderContent {
    background: white !important;
    border: 1px solid #e8e4de !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
    padding: 1.2rem !important;
}

/* ── Alert / info / success / error ── */
.stAlert {
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    border: none !important;
    font-size: 0.88rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #e8e4de !important;
}

/* ── Chat ── */
[data-testid="stChatMessage"] {
    color: #1a1a2e !important;
    border-radius: 12px !important;
    background: white !important;
    border: 1px solid #e8e4de !important;
    margin-bottom: 0.5rem !important;
}
.stChatInputContainer {
    color: #1a1a2e !important;
    border-radius: 12px !important;
    border: 1.5px solid #e0dbd3 !important;
    background: white !important;
}

/* ── Divider ── */
hr {
    border-color: #ede9e2 !important;
    margin: 1.2rem 0 !important;
}

/* ── Caption / small text ── */
.stCaption {
    color: #888 !important;
    font-size: 0.8rem !important;
}

/* ── Form ── */
[data-testid="stForm"] {
    background: #faf9f6 !important;
    border: 1px solid #e8e4de !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

/* ── Label ── */
label {
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    color: #444 !important;
}

/* ── Subheader ── */
.stSubheader {
    color: #1a1a2e !important;
    font-weight: 600 !important;
}

/* ── Mobile ── */
@media (max-width: 768px) {
    .block-container { padding: 1rem !important; }
    div[data-testid="column"] { min-width: 100% !important; }
    h1 { font-size: 1.6rem !important; }
}

/* ── Sidebar başlık ── */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #e8e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# ── Bağlantılar ───────────────────────────────────────────────────────────────
groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
sb = create_client(st.secrets.get("SUPABASE_URL", ""), st.secrets.get("SUPABASE_KEY", ""))
GMAIL_USER = st.secrets.get("GMAIL_USER", "")
GMAIL_PASS = st.secrets.get("GMAIL_PASSWORD", "")

# ── DB fonksiyonları ──────────────────────────────────────────────────────────
def hashle(s):
    return hashlib.sha256(s.encode()).hexdigest()

def kayit_ol(adi, sifre, buro):
    sb.table("kullanicilar").insert({
        "kullanici_adi": adi, "sifre": hashle(sifre), "buro_adi": buro
    }).execute()
    return True

def giris(adi, sifre):
    r = sb.table("kullanicilar").select("*").eq("kullanici_adi", adi).eq("sifre", hashle(sifre)).execute()
    return r.data[0] if r.data else None

def m_ekle(kid, isim, vno, tel, tur, ucret, email, defter_turu, efatura, sozlesme_tarihi, stopaj_orani, babs):
    sb.table("mukellefler").insert({
        "kullanici_id": kid, "isim": isim, "vergi_no": vno,
        "telefon": tel, "tur": tur, "ucret": ucret, "email": email,
        "belge_durumu": "Bekleniyor", "odeme_durumu": "Ödenmedi",
        "eklenme": datetime.now().strftime("%d.%m.%Y"),
        "defter_turu": defter_turu,
        "efatura": efatura,
        "sozlesme_tarihi": sozlesme_tarihi,
        "stopaj_orani": stopaj_orani,
        "babs": babs,
    }).execute()

def m_liste(kid):
    r = sb.table("mukellefler").select("*").eq("kullanici_id", kid).execute()
    cols = ["id","kullanici_id","isim","vergi_no","telefon","tur",
            "belge_durumu","ucret","odeme_durumu","email","eklenme",
            "defter_turu","efatura","sozlesme_tarihi","stopaj_orani","babs"]
    return pd.DataFrame(r.data) if r.data else pd.DataFrame(columns=cols)

def m_belge(mid, durum):
    sb.table("mukellefler").update({"belge_durumu": durum}).eq("id", mid).execute()

def m_odeme(mid, durum):
    sb.table("mukellefler").update({"odeme_durumu": durum}).eq("id", mid).execute()

def m_sil(mid):
    sb.table("mukellefler").delete().eq("id", mid).execute()

def b_liste_genel(kid):
    bugun = date.today()
    ay = bugun.strftime("%Y-%m")
    r = sb.table("beyannameler").select("*").eq("kullanici_id", kid).eq("ay", ay).execute()
    if not r.data:
        for ad, gun in [("KDV", 28), ("Muhtasar", 26), ("SGK", 23), ("Damga Vergisi", 26)]:
            sb.table("beyannameler").insert({
                "kullanici_id": kid, "beyanname_turu": ad,
                "son_gun": f"{bugun.year}-{bugun.month:02d}-{gun:02d}",
                "durum": "Bekliyor", "ay": ay
            }).execute()
        r = sb.table("beyannameler").select("*").eq("kullanici_id", kid).eq("ay", ay).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def b_guncelle(bid, durum):
    sb.table("beyannameler").update({"durum": durum}).eq("id", bid).execute()

def mb_liste(kid, mukellef_id):
    r = sb.table("mukellef_beyanname").select("*").eq("kullanici_id", kid).eq("mukellef_id", mukellef_id).order("ay", desc=True).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def mb_ekle(kid, mukellef_id, tur, ay, son_gun, durum, not_):
    sb.table("mukellef_beyanname").insert({
        "kullanici_id": kid, "mukellef_id": mukellef_id,
        "beyanname_turu": tur, "ay": ay, "son_gun": son_gun,
        "durum": durum, "aciklama": not_
    }).execute()

def gorev_liste(kid):
    r = sb.table("gorevler").select("*").eq("kullanici_id", kid).order("son_gun").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def gorev_ekle(kid, baslik, mukellef_adi, son_gun, oncelik):
    sb.table("gorevler").insert({
        "kullanici_id": kid, "baslik": baslik,
        "mukellef_adi": mukellef_adi, "son_gun": son_gun,
        "oncelik": oncelik, "tamamlandi": False
    }).execute()

def gorev_tamamla(gid):
    sb.table("gorevler").update({"tamamlandi": True}).eq("id", gid).execute()

def gorev_sil(gid):
    sb.table("gorevler").delete().eq("id", gid).execute()

def borc_liste(kid, mukellef_id):
    r = sb.table("borc_takip").select("*").eq("kullanici_id", kid).eq("mukellef_id", mukellef_id).order("son_odeme").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def borc_ekle(kid, mukellef_id, tur, tutar, son_odeme, durum):
    sb.table("borc_takip").insert({
        "kullanici_id": kid, "mukellef_id": mukellef_id,
        "tur": tur, "tutar": tutar, "son_odeme": son_odeme, "durum": durum
    }).execute()

def ai_sor(soru):
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": "Sen Türk vergi ve muhasebe mevzuatı konusunda uzman bir mali müşavir asistanısın. Türkçe, net ve pratik cevaplar ver. Kanun maddeleri, oranlar ve tarihler konusunda doğru bilgi sun. Eğer bir konuda emin değilsen belirt."},
            {"role": "user", "content": soru}
        ]
    )
    return r.choices[0].message.content

# ── Mail ──────────────────────────────────────────────────────────────────────
def mail_gonder(alici, konu, mesaj):
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = alici
        msg["Subject"] = konu
        msg.attach(MIMEText(mesaj, "plain", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        return str(e)

def toplu_mail_gonder(df, konu, mesaj_sablonu):
    basarili, basarisiz = [], []
    hedefler = df[(df.belge_durumu == "Bekleniyor") & (df.email.notna()) & (df.email != "")]
    for _, r in hedefler.iterrows():
        mesaj = mesaj_sablonu.replace("{isim}", r.isim)
        sonuc = mail_gonder(r.email, konu, mesaj)
        if sonuc is True:
            basarili.append(r.isim)
        else:
            basarisiz.append(f"{r.isim} ({sonuc})")
    return basarili, basarisiz

# ── PDF makbuz ────────────────────────────────────────────────────────────────
def pdf_makbuz(buro_adi, isim, ucret, ay):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w/2, h-60, "UCRET MAKBUZU")
    c.setFont("Helvetica", 13)
    c.drawCentredString(w/2, h-85, buro_adi)
    c.line(50, h-100, w-50, h-100)
    c.setFont("Helvetica", 12)
    for s, y in [
        (f"Mukellef : {isim}", h-140),
        (f"Donem    : {ay}", h-168),
        (f"Tutar    : {int(ucret):,} TL", h-196),
        (f"Tarih    : {date.today().strftime('%d.%m.%Y')}", h-224),
        ("Odeme yapilmistir. Tesekkurler.", h-270),
    ]:
        c.drawString(60, y, s)
    c.line(50, h-290, w-50, h-290)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, h-315, "Bu makbuz BuroAsist tarafindan olusturulmustur.")
    c.save()
    buf.seek(0)
    return buf

def excel_raporu(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        ozet = df[["isim","tur","ucret","odeme_durumu","belge_durumu","eklenme"]].copy()
        ozet.columns = ["Ad Soyad","Tur","Aylik Ucret","Odeme","Belge","Eklenme"]
        ozet.to_excel(writer, index=False, sheet_name="Mukellefler")
    buf.seek(0)
    return buf

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
    ay_etiket = {a: datetime.strptime(a, "%Y-%m").strftime("%b %Y") for a in aylar}
    fig = go.Figure()
    fig.add_bar(x=[ay_etiket[a] for a in aylar], y=[odendi.get(a,0) for a in aylar],
                name="Tahsil Edildi", marker_color="#38a169")
    fig.add_bar(x=[ay_etiket[a] for a in aylar], y=[odenmedi.get(a,0) for a in aylar],
                name="Tahsil Edilmedi", marker_color="#e53e3e")
    fig.update_layout(
        barmode="group", title="Son 6 Ay Gelir Durumu (TL)",
        xaxis_title="Ay", yaxis_title="TL", height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", y=1.1),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color="#333333"),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#333333"))
    fig.update_yaxes(gridcolor="#f0f0f0", tickfont=dict(color="#333333"))
    return fig

# ── Kritik uyarılar ───────────────────────────────────────────────────────────
def kritik_uyarilar(df, bdf):
    uyarilar = []
    bugun = date.today()

    # Belge bekleyenler
    if not df.empty:
        for _, r in df[df.belge_durumu=="Bekleniyor"].iterrows():
            uyarilar.append(("red", f"📁 Belge bekleniyor: **{r.isim}**"))

    # Beyanname yaklaşanlar
    if not bdf.empty:
        for _, r in bdf.iterrows():
            try:
                sg = date.fromisoformat(r.son_gun)
                kalan = (sg - bugun).days
                if r.durum == "Bekliyor":
                    if kalan < 0:
                        uyarilar.append(("red", f"⛔ **{r.beyanname_turu}** beyannamesi süresi geçti!"))
                    elif kalan <= 5:
                        uyarilar.append(("warn", f"⚠️ **{r.beyanname_turu}** son gün: {sg.strftime('%d.%m.%Y')} ({kalan} gün kaldı)"))
            except Exception:
                continue

    # Geçici vergi uyarısı (Nisan, Ağustos, Kasım, Şubat)
    gecici_vergi_aylari = [4, 8, 11, 2]
    if bugun.month in gecici_vergi_aylari and bugun.day >= 14:
        uyarilar.append(("warn", "📊 **Geçici Vergi** beyanname dönemi — kontrol et!"))

    # Ba/Bs uyarısı (her ayın 5'inden sonra)
    if bugun.day >= 5 and not df.empty:
        babs_var = df[df.get("babs", pd.Series()) == "Evet"] if "babs" in df.columns else pd.DataFrame()
        if not babs_var.empty:
            uyarilar.append(("warn", f"📋 **Ba/Bs formu** bekliyor: {len(babs_var)} mükellef"))

    # Sözleşme yenileme (30 gün içinde dolacak)
    if not df.empty and "sozlesme_tarihi" in df.columns:
        for _, r in df.iterrows():
            try:
                if r.sozlesme_tarihi:
                    st_date = datetime.strptime(r.sozlesme_tarihi, "%d.%m.%Y").date()
                    # Bir yıl sonrası
                    yenileme = st_date.replace(year=st_date.year + 1)
                    kalan = (yenileme - bugun).days
                    if 0 <= kalan <= 30:
                        uyarilar.append(("warn", f"📝 **{r.isim}** sözleşme yenileme: {kalan} gün kaldı"))
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
    st.markdown("""
    <div style='text-align:center; padding: 3rem 0 1rem 0;'>
        <div style='font-size:2.8rem; margin-bottom:0.5rem;'>⚖️</div>
        <div style='font-family:"Instrument Serif",serif; font-size:2.8rem; color:#1a1a2e; font-weight:400; letter-spacing:-0.02em;'>BuroAsist</div>
        <div style='color:#888; font-size:0.95rem; margin-top:0.4rem; font-family:"Plus Jakarta Sans",sans-serif;'>SMMM Büro Yönetim Platformu</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
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
        buro   = st.text_input("Büro Adı")
        yadi   = st.text_input("Kullanıcı Adı", key="k_adi")
        ysifre = st.text_input("Şifre", type="password", key="k_sifre")
        if st.button("Kayıt Ol"):
            if kayit_ol(yadi, ysifre, buro):
                st.success("Hesap oluşturuldu!")
            else:
                st.error("Kayıt başarısız.")

# ═══════════════════════════════════════════════════════════════════════════════
# ANA EKRAN
# ═══════════════════════════════════════════════════════════════════════════════
else:
    kid      = st.session_state.kullanici["id"]
    buro_adi = st.session_state.kullanici["buro_adi"]

    with st.sidebar:
        st.markdown(f"""
        <div style='padding:0.5rem 0 1rem 0;'>
            <div style='font-size:1.3rem; font-weight:700; color:#e8e8f0; letter-spacing:-0.01em;'>⚖️ BuroAsist</div>
            <div style='color:#a8a8c8; font-size:0.75rem; margin-top:4px; font-weight:500;'>{buro_adi}</div>
            <div style='color:#6868a0; font-size:0.72rem; margin-top:2px;'>📅 {date.today().strftime('%d.%m.%Y')}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        st.markdown("<div style='color:#a8a8c8; font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.8rem;'>+ YENİ MÜKELLEF</div>", unsafe_allow_html=True)
        isim            = st.text_input("Ad Soyad")
        vno             = st.text_input("Vergi No")
        tel             = st.text_input("Telefon")
        email           = st.text_input("Email")
        tur             = st.selectbox("Tür", ["Şahıs", "Limited", "Anonim"])
        defter_turu     = st.selectbox("Defter Türü", ["İşletme Defteri", "Bilanço"])
        efatura         = st.selectbox("E-Fatura", ["Hayır", "Evet"])
        babs            = st.selectbox("Ba/Bs Yükümlüsü", ["Hayır", "Evet"])
        stopaj_orani    = st.selectbox("Stopaj Oranı", ["Yok", "%10", "%15", "%20", "%25"])
        sozlesme_tarihi = st.text_input("Sözleşme Tarihi (gg.aa.yyyy)")
        ucret           = st.number_input("Aylık Ücret (TL)", min_value=0, value=1500)
        if st.button("➕ Ekle", use_container_width=True) and isim:
            m_ekle(kid, isim, vno, tel, tur, ucret, email, defter_turu, efatura, sozlesme_tarihi, stopaj_orani, babs)
            st.rerun()
        st.divider()
        if st.button("🚪 Çıkış", use_container_width=True):
            st.session_state.kullanici = None
            st.rerun()

    st.markdown(f"""
    <div style='display:flex; align-items:center; gap:1rem; margin-bottom:1.5rem; padding:1.2rem 1.5rem; background:white; border:1px solid #e8e4de; border-radius:14px; box-shadow:0 1px 4px rgba(0,0,0,0.04);'>
        <div style='font-size:2rem;'>⚖️</div>
        <div>
            <div style='font-family:"Instrument Serif",serif; font-size:1.8rem; color:#1a1a2e; font-weight:400; line-height:1;'>BuroAsist</div>
            <div style='color:#888; font-size:0.78rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-top:3px;'>{buro_adi}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    df  = m_liste(kid)
    bdf = b_liste_genel(kid)

    toplam   = int(df["ucret"].sum()) if not df.empty else 0
    odendi_t = int(df[df.odeme_durumu=="Ödendi"]["ucret"].sum()) if not df.empty else 0
    bek_cnt  = len(df[df.belge_durumu=="Bekleniyor"]) if not df.empty else 0
    gel_cnt  = len(df[df.belge_durumu=="Geldi"]) if not df.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Toplam Mükellef", len(df))
    c2.metric("📁 Belge Bekleyen",  bek_cnt, delta=f"-{bek_cnt}" if bek_cnt else None, delta_color="inverse")
    c3.metric("✅ Belge Gelen",     gel_cnt)
    c4.metric("💰 Tahsil Edildi",   f"{odendi_t:,} TL")
    c5.metric("❌ Tahsil Edilmedi", f"{toplam-odendi_t:,} TL",
              delta=f"-{toplam-odendi_t:,} TL" if (toplam-odendi_t) else None, delta_color="inverse")

    st.divider()

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
                if tip == "red": st.error(mesaj)
                else: st.warning(mesaj)
        else:
            st.success("✅ Kritik uyarı yok.")

    st.divider()

    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📊 Mükellefler", "📋 Görevler", "💰 Ücret Takibi",
        "📅 Beyanname", "📱 Toplu Mail", "📈 Rapor", "🤖 AI Asistan"
    ])

    # ── T1: Mükellefler ───────────────────────────────────────────────────────
    with t1:
        # Arama/filtre
        ara = st.text_input("🔍 Mükellef ara...", placeholder="İsim veya vergi no")
        fcol1, fcol2, fcol3 = st.columns(3)
        f_tur    = fcol1.selectbox("Tür", ["Tümü","Şahıs","Limited","Anonim"])
        f_belge  = fcol2.selectbox("Belge", ["Tümü","Bekleniyor","Geldi"])
        f_odeme  = fcol3.selectbox("Ödeme", ["Tümü","Ödenmedi","Ödendi"])

        gdf = df.copy()
        if ara:
            gdf = gdf[gdf.isim.str.contains(ara, case=False, na=False) |
                      gdf.vergi_no.astype(str).str.contains(ara, na=False)]
        if f_tur   != "Tümü": gdf = gdf[gdf.tur == f_tur]
        if f_belge != "Tümü": gdf = gdf[gdf.belge_durumu == f_belge]
        if f_odeme != "Tümü": gdf = gdf[gdf.odeme_durumu == f_odeme]

        st.caption(f"{len(gdf)} mükellef gösteriliyor")
        st.divider()

        if not gdf.empty:
            for _, r in gdf.iterrows():
                with st.expander(f"{'🟡' if r.belge_durumu=='Bekleniyor' else '🟢'} {r.isim} — {r.tur} — {int(r.ucret):,} TL"):

                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"📞 **Telefon:** {r.telefon}")
                    c1.markdown(f"📧 **Email:** {r.get('email','') or '—'}")
                    c2.markdown(f"🔢 **Vergi No:** {r.get('vergi_no','') or '—'}")
                    c2.markdown(f"📅 **Eklenme:** {r.eklenme}")
                    c3.markdown(f"📒 **Defter:** {r.get('defter_turu','—') or '—'}")
                    c3.markdown(f"🧾 **E-Fatura:** {r.get('efatura','—') or '—'}")
                    c3.markdown(f"📋 **Ba/Bs:** {r.get('babs','—') or '—'}")
                    c3.markdown(f"✂️ **Stopaj:** {r.get('stopaj_orani','—') or '—'}")
                    if r.get('sozlesme_tarihi'):
                        c1.markdown(f"📝 **Sözleşme:** {r.sozlesme_tarihi}")

                    st.divider()
                    d1, d2, d3 = st.columns([2,2,1])
                    with d1:
                        sec = st.selectbox("📁 Belge", ["Bekleniyor","Geldi"],
                                           index=0 if r.belge_durumu=="Bekleniyor" else 1,
                                           key=f"d{r.id}")
                        if sec != r.belge_durumu:
                            m_belge(r.id, sec); st.rerun()
                    with d2:
                        ode = st.selectbox("💰 Ödeme", ["Ödenmedi","Ödendi"],
                                           index=0 if r.odeme_durumu=="Ödenmedi" else 1,
                                           key=f"o{r.id}")
                        if ode != r.odeme_durumu:
                            m_odeme(r.id, ode); st.rerun()
                    with d3:
                        st.write(""); st.write("")
                        if st.button("🗑️ Sil", key=f"s{r.id}", use_container_width=True):
                            m_sil(r.id); st.rerun()

                    # Mükellef bazlı beyanname geçmişi
                    st.divider()
                    st.markdown("**📅 Beyanname Geçmişi**")
                    mbd = mb_liste(kid, r.id)
                    if not mbd.empty:
                        st.dataframe(mbd[["ay","beyanname_turu","son_gun","durum","aciklama"]].rename(columns={
                            "ay":"Ay","beyanname_turu":"Tür","son_gun":"Son Gün","durum":"Durum","aciklama":"Not"
                        }), use_container_width=True)
                    with st.form(key=f"mbf{r.id}"):
                        fc1, fc2, fc3 = st.columns(3)
                        mb_tur = fc1.selectbox("Tür", ["KDV","Muhtasar","SGK","Damga Vergisi","Geçici Vergi","Stopaj","Ba/Bs","Diğer"])
                        mb_ay  = fc2.text_input("Ay (yyyy-mm)", value=date.today().strftime("%Y-%m"))
                        mb_sg  = fc3.text_input("Son Gün (yyyy-mm-dd)", value=date.today().strftime("%Y-%m-28"))
                        mb_dur = st.selectbox("Durum", ["Bekliyor","Gönderildi","Gecikti"])
                        mb_not = st.text_input("Not (opsiyonel)")
                        if st.form_submit_button("➕ Beyanname Ekle"):
                            mb_ekle(kid, r.id, mb_tur, mb_ay, mb_sg, mb_dur, mb_not)
                            st.rerun()

                    # Borç takibi
                    st.divider()
                    st.markdown("**💳 Vergi Borç Takibi**")
                    borclar = borc_liste(kid, r.id)
                    if not borclar.empty:
                        st.dataframe(borclar[["tur","tutar","son_odeme","durum"]].rename(columns={
                            "tur":"Tür","tutar":"Tutar (TL)","son_odeme":"Son Ödeme","durum":"Durum"
                        }), use_container_width=True)
                    with st.form(key=f"bf{r.id}"):
                        bc1, bc2, bc3 = st.columns(3)
                        b_tur  = bc1.selectbox("Borç Türü", ["KDV Borcu","SGK Borcu","Gelir Vergisi","Kurumlar Vergisi","Geçici Vergi","Diğer"])
                        b_tut  = bc2.number_input("Tutar (TL)", min_value=0)
                        b_sg   = bc3.text_input("Son Ödeme (yyyy-mm-dd)")
                        b_dur  = st.selectbox("Durum", ["Ödenmedi","Ödendi","Taksitli"])
                        if st.form_submit_button("➕ Borç Ekle"):
                            borc_ekle(kid, r.id, b_tur, b_tut, b_sg, b_dur)
                            st.rerun()

                    # Dosya yükleme
                    st.divider()
                    st.markdown("**📎 Dosya Yükle**")
                    yukle = st.file_uploader("PDF veya görsel", type=["pdf","png","jpg","jpeg"], key=f"f{r.id}")
                    if yukle:
                        dosya_bytes = yukle.read()
                        dosya_yolu  = f"belgeler/{kid}/{r.id}/{yukle.name}"
                        try:
                            sb.storage.from_("belgeler").upload(
                                dosya_yolu, dosya_bytes,
                                {"content-type": yukle.type, "upsert": "true"}
                            )
                            st.success(f"✅ {yukle.name} yüklendi!")
                        except Exception as e:
                            st.error(f"Hata: {e}")

                    # Mail gönder
                    if r.get("email"):
                        st.divider()
                        st.markdown("**📧 Mail Gönder**")
                        mail_konu = st.text_input("Konu", value="Belge Hatırlatması", key=f"mk{r.id}")
                        mail_msg  = st.text_area("Mesaj",
                            value=f"Sayın {r.isim}, bu ayki belgelerinizi henüz almadık. Lütfen iletiniz.",
                            key=f"mm{r.id}")
                        if st.button("📨 Gönder", key=f"mg{r.id}"):
                            sonuc = mail_gonder(r.email, mail_konu, mail_msg)
                            if sonuc is True: st.success("✅ Mail gönderildi!")
                            else: st.error(f"Hata: {sonuc}")

                    # PDF makbuz
                    st.divider()
                    ay_str  = date.today().strftime("%B %Y")
                    pdf_buf = pdf_makbuz(buro_adi, r.isim, r.ucret, ay_str)
                    st.download_button(
                        label="🧾 PDF Makbuz İndir",
                        data=pdf_buf,
                        file_name=f"makbuz_{r.isim.replace(' ','_')}.pdf",
                        mime="application/pdf",
                        key=f"pdf{r.id}"
                    )
        else:
            st.info("Mükellef bulunamadı.")

    # ── T2: Görevler ──────────────────────────────────────────────────────────
    with t2:
        st.subheader("📋 Görev & Hatırlatma")
        bugun = date.today()
        with st.form("gorev_form"):
            gc1, gc2, gc3, gc4 = st.columns([3,2,2,1])
            g_baslik   = gc1.text_input("Görev")
            g_mukellef = gc2.text_input("Mükellef (opsiyonel)")
            g_tarih    = gc3.text_input("Son Gün (yyyy-mm-dd)", value=date.today().strftime("%Y-%m-%d"))
            g_oncelik  = gc4.selectbox("Öncelik", ["Yüksek","Orta","Düşük"])
            if st.form_submit_button("➕ Görev Ekle") and g_baslik:
                gorev_ekle(kid, g_baslik, g_mukellef, g_tarih, g_oncelik)
                st.rerun()

        st.divider()
        gorevler = gorev_liste(kid)
        if not gorevler.empty:
            bekleyenler   = gorevler[gorevler.tamamlandi == False]
            tamamlananlar = gorevler[gorevler.tamamlandi == True]
            st.markdown("**⏳ Bekleyen Görevler**")
            for _, r in bekleyenler.iterrows():
                gc1, gc2, gc3, gc4, gc5 = st.columns([3,2,1,1,1])
                gc1.write(f"**{r.baslik}**")
                gc2.write(r.mukellef_adi or "—")
                try:
                    kalan = (date.fromisoformat(r.son_gun) - bugun).days
                    if kalan < 0:    gc3.error(f"⛔ {abs(kalan)}g geçti")
                    elif kalan == 0: gc3.warning("⚠️ Bugün!")
                    else:            gc3.success(f"✅ {kalan}g")
                except:
                    gc3.write(r.son_gun)
                oncelik_renk = {"Yüksek":"🔴","Orta":"🟡","Düşük":"🟢"}.get(r.oncelik,"⚪")
                gc4.write(f"{oncelik_renk} {r.oncelik}")
                if gc5.button("✓", key=f"gt{r.id}"):
                    gorev_tamamla(r.id); st.rerun()
            if not tamamlananlar.empty:
                st.divider()
                st.markdown("**✅ Tamamlananlar**")
                for _, r in tamamlananlar.iterrows():
                    gc1, gc2 = st.columns([5,1])
                    gc1.write(f"~~{r.baslik}~~ — {r.mukellef_adi or ''}")
                    if gc2.button("🗑️", key=f"gs{r.id}"):
                        gorev_sil(r.id); st.rerun()
        else:
            st.info("Henüz görev eklenmedi.")

    # ── T3: Ücret Takibi ──────────────────────────────────────────────────────
    with t3:
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

    # ── T4: Beyanname ─────────────────────────────────────────────────────────
    with t4:
        st.subheader("📅 Genel Beyanname Takvimi")
        bugun = date.today()
        if not bdf.empty:
            for _, r in bdf.iterrows():
                sg    = date.fromisoformat(r.son_gun)
                kalan = (sg - bugun).days
                a, b, c, d = st.columns([3,2,2,2])
                a.write(f"**{r.beyanname_turu}**")
                b.write(sg.strftime("%d.%m.%Y"))
                with c:
                    if kalan < 0:    st.error("⛔ Geçti")
                    elif kalan <= 3: st.warning(f"⚠️ {kalan} gün")
                    else:            st.success(f"✅ {kalan} gün")
                with d:
                    yeni = st.selectbox("", ["Bekliyor","Gönderildi"],
                                        index=0 if r.durum=="Bekliyor" else 1,
                                        key=f"b{r.id}")
                    if yeni != r.durum:
                        b_guncelle(r.id, yeni); st.rerun()
                st.divider()

    # ── T5: Toplu Mail ────────────────────────────────────────────────────────
    with t5:
        st.subheader("📱 Toplu Mail & WhatsApp")

        if not df.empty:
            bek = df[df.belge_durumu=="Bekleniyor"]
            mail_hedef = bek[bek.email.notna() & (bek.email != "")]
            whatsapp_hedef = bek

            st.info(f"📬 Belge bekleyen **{len(bek)}** mükellef var. Mail gönderilebilecek: **{len(mail_hedef)}**")
            st.divider()

            # Toplu mail
            st.markdown("### 📧 Toplu Mail Gönder")
            toplu_konu = st.text_input("Mail Konusu", value="Belge Hatırlatması — " + date.today().strftime("%B %Y"))
            toplu_mesaj = st.text_area("Mail Şablonu ({isim} otomatik değişir)",
                value="Sayın {isim},\n\nBu ayki belgelerinizi henüz almadık. Lütfen en kısa sürede büromuza iletiniz.\n\nTeşekkürler,\n" + buro_adi,
                height=150)
            if st.button("📨 Tümüne Mail Gönder", use_container_width=True):
                if len(mail_hedef) == 0:
                    st.warning("Mail adresi olan mükellef yok.")
                else:
                    with st.spinner(f"{len(mail_hedef)} kişiye mail gönderiliyor..."):
                        basarili, basarisiz = toplu_mail_gonder(df, toplu_konu, toplu_mesaj)
                    if basarili:
                        st.success(f"✅ Gönderildi: {', '.join(basarili)}")
                    if basarisiz:
                        st.error(f"❌ Başarısız: {', '.join(basarisiz)}")

            st.divider()

            # WhatsApp şablonları
            st.markdown("### 📱 WhatsApp Şablonları")
            for _, r in whatsapp_hedef.iterrows():
                tel_goster = r.telefon if r.telefon else "—"
                st.markdown(f"""
                <div style='background:#e7fce8; border:1px solid #b7dfb9; border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:0.7rem;'>
                    <span style='font-size:1.3rem;'>📱</span>
                    <div>
                        <div style='font-weight:700; color:#1a1a2e; font-size:0.95rem;'>{r.isim}</div>
                        <div style='color:#444; font-size:0.82rem;'>📞 {tel_goster}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                mesaj_wa = f"Sayın {r.isim}, bu ayki belgelerinizi henüz almadık. Lütfen en kısa sürede iletiniz. Teşekkürler, {buro_adi}"
                st.code(mesaj_wa)
                tel_link = str(tel_goster).replace(" ", "").replace("-", "")
                if tel_link and tel_link != "—":
                    st.markdown(f"[📲 WhatsApp'ta Aç](https://wa.me/90{tel_link.lstrip('0')}?text={mesaj_wa.replace(' ', '%20')})", unsafe_allow_html=False)
                st.divider()
        else:
            st.info("Mükellef yok")

    # ── T6: Rapor ─────────────────────────────────────────────────────────────
    with t6:
        st.subheader("📈 Aylık Gelir Raporu")
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Potansiyel", f"{toplam:,} TL")
            col2.metric("Tahsil Edildi",     f"{odendi_t:,} TL")
            col3.metric("Tahsil Edilmedi",   f"{toplam-odendi_t:,} TL")
            st.divider()

            # E-fatura durumu
            if "efatura" in df.columns:
                ef_evet = len(df[df.efatura=="Evet"])
                ef_hayir = len(df[df.efatura=="Hayır"])
                ec1, ec2 = st.columns(2)
                ec1.metric("🧾 E-Fatura Mükellefi", ef_evet)
                ec2.metric("📄 E-Fatura Dışı", ef_hayir)
            st.divider()

            fig2 = go.Figure(data=[go.Pie(
                labels=["Tahsil Edildi","Tahsil Edilmedi"],
                values=[odendi_t, toplam-odendi_t],
                marker_colors=["#38a169","#e53e3e"],
                hole=0.4
            )])
            fig2.update_layout(height=300, margin=dict(l=20,r=20,t=20,b=20), paper_bgcolor="white")
            st.plotly_chart(fig2, use_container_width=True)
            st.divider()

            goster = df[["isim","tur","ucret","odeme_durumu","belge_durumu"]].copy()
            goster.columns = ["Ad Soyad","Tür","Aylık Ücret","Ödeme","Belge"]
            st.dataframe(goster, use_container_width=True)
            exc = excel_raporu(df)
            st.download_button(
                label="📥 Excel Olarak İndir",
                data=exc,
                file_name=f"buroasist_{date.today().strftime('%Y%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Henüz veri yok.")

    # ── T7: AI Asistan ───────────────────────────────────────────────────────
    with t7:
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
