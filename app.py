import json, os, re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Profil Kabupaten/Kota Indonesia 2024", layout="wide")

CSV = "data_processed/data_master_2024.csv"
LOAD = "data_processed/pca_loadings.csv"
GEO = "data/kabkota.geojson"

VARS = ["kepadatan", "pdrb_juta", "ipm", "laju_penduduk", "tpt",
        "kemiskinan", "iklh_lahan", "iklh_udara", "iklh_air"]
try:  # varians PC1 dan PC2 (%) dibaca dari hasil analysis.py
    _ev = pd.read_csv("data_processed/pca_variance.csv")["varians_pct"]
    EV1, EV2 = float(_ev[0]), float(_ev[1])
except Exception:
    EV1, EV2 = 41.7, 13.9
LABEL = {
    "kepadatan": "Kepadatan penduduk (jiwa/km²)",
    "pdrb_juta": "PDRB per kapita ADHK (juta Rp/jiwa)",
    "ipm": "IPM 2024",
    "laju_penduduk": "Laju pertumbuhan penduduk (%/tahun)",
    "tpt": "Tingkat pengangguran terbuka (%)",
    "kemiskinan": "Persentase penduduk miskin (%)",
    "iklh_lahan": "Indeks kualitas lahan",
    "iklh_udara": "Indeks kualitas udara",
    "iklh_air": "Indeks kualitas air",
}
# TODO: isi judul tabel, tahun, URL, tanggal akses untuk setiap variabel
SUMBER = "Sumber: BPS (judul tabel, tahun 2024, URL, diakses: ISI TANGGAL). Batas wilayah: non-BPS."

# Nama cluster diturunkan dari profil rata-rata (lihat data_processed/profil_cluster.csv)
CL_NAME = {0: "C0 Padat, IPM tinggi", 1: "C1 Menengah",
           2: "C2 Jarang penduduk, kemiskinan tinggi"}
NA_NAME = "Data tidak lengkap"
# Palet Okabe-Ito (ramah buta warna)
CL_COLOR = {CL_NAME[0]: "#0072B2", CL_NAME[1]: "#E69F00",
            CL_NAME[2]: "#009E73", NA_NAME: "#999999"}

NEW = hasattr(px, "choropleth_map")
STYLE = {"map_style" if NEW else "mapbox_style": "carto-positron"}


@st.cache_data
def load():
    df = pd.read_csv(CSV)
    df["kode"] = df["kode"].astype(str).str.replace(r"\D", "", regex=True)
    if df["cluster"].min() == 1:
        df["cluster"] = df["cluster"] - 1
    if "data_lengkap" not in df.columns:
        df["data_lengkap"] = df[VARS].notna().all(axis=1)
    df["klaster"] = df["cluster"].map(lambda c: CL_NAME[int(c)] if pd.notna(c) else NA_NAME)
    load_df = pd.read_csv(LOAD, index_col=0)
    return df, load_df


def _pts(c):
    if isinstance(c[0], (int, float)):
        yield c
    else:
        for x in c:
            yield from _pts(x)


@st.cache_data
def load_geo(codes):
    if not os.path.exists(GEO):
        return None, None, 0
    gj = json.load(open(GEO, encoding="utf-8"))
    feats = gj["features"]
    keys = feats[0]["properties"].keys()
    norm = lambda v: re.sub(r"\D", "", str(v))
    best = max(keys, key=lambda k: len({norm(f["properties"].get(k)) for f in feats} & set(codes)))
    cent = {}
    for f in feats:
        f["id"] = norm(f["properties"].get(best))
        p = np.array(list(_pts(f["geometry"]["coordinates"])))
        cent[f["id"]] = ((p[:, 1].min() + p[:, 1].max()) / 2, (p[:, 0].min() + p[:, 0].max()) / 2)
    matched = len(set(cent) & set(codes))
    return gj, cent, matched


df, loadings = load()
comp = df[df["data_lengkap"]].copy()
gj, cent, matched = load_geo(tuple(df["kode"]))

st.title("Profil Kabupaten/Kota Indonesia 2024")
st.caption("Bagaimana karakteristik sosial, ekonomi, demografi, dan lingkungan daerah berbeda secara spasial dan multivariat?")

t1, t2, t3, t4 = st.tabs(["Ringkasan", "Peta", "Multivariat", "Hierarki"])

# ---------------- Ringkasan ----------------
with t1:
    a, b, c = st.columns(3)
    a.metric("Kabupaten/Kota", len(df))
    b.metric("Variabel numerik", len(VARS))
    c.metric("Data lengkap (PCA & klaster)", len(comp))
    st.write("Delapan indikator diringkas dengan PCA (kepadatan dan PDRB di-log10, lalu distandardisasi) "
             "dan dikelompokkan dengan K-Means (K=3, dipilih dari silhouette). "
             "Daerah dengan data kualitas udara/air kosong tidak ikut PCA dan klaster.")
    st.dataframe(df["klaster"].value_counts().rename("jumlah daerah"))
    st.info("Tiga klaster membentuk gradien urbanisasi: dari daerah padat dengan IPM tinggi dan lingkungan "
            "paling tertekan (C0), menengah (C1), hingga jarang penduduk dengan kemiskinan tinggi tetapi "
            "kualitas lahan terbaik (C2). Silhouette rendah (sekitar 0,2), jadi batas antarklaster tidak tegas.")
    st.caption(SUMBER)

# ---------------- Peta ----------------
with t2:
    if gj is None:
        st.warning("File data/kabkota.geojson belum ada, peta belum bisa ditampilkan.")
    else:
        st.caption(f"{matched} dari {len(df)} daerah cocok dengan batas wilayah.")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Peta koroplet")
            v = st.selectbox("Indikator", VARS, index=2, format_func=LABEL.get)
            d = df.copy()
            d["kelas"] = pd.qcut(d[v], 5, duplicates="drop").astype(str)
            order = sorted(d["kelas"].dropna().unique(), key=lambda s: float(s.split(",")[0].strip("([")))
            colors = px.colors.sequential.Viridis[::2][:len(order)]
            fig = (px.choropleth_map if NEW else px.choropleth_mapbox)(
                d.dropna(subset=[v]), geojson=gj, locations="kode", color="kelas",
                category_orders={"kelas": order}, color_discrete_sequence=colors,
                hover_name="kabkota", hover_data={"kode": False, "kelas": False, v: ":.2f"},
                labels={v: LABEL[v], "kelas": "Kuantil"}, center={"lat": -2.5, "lon": 118},
                zoom=3.2, opacity=0.85, **STYLE)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend_title_text=LABEL[v])
            st.plotly_chart(fig, width="stretch")
            st.caption("Kelas kuantil (5 kelas) agar tiap warna berisi jumlah daerah sama pada data miring. "
                       "Daerah tanpa data tidak diwarnai. " + SUMBER)
        with c2:
            st.subheader("Peta simbol proporsional")
            sz = st.selectbox("Ukuran lingkaran", ["pdrb_juta", "kepadatan"], format_func=LABEL.get)
            pilih = st.multiselect("Tampilkan klaster", list(CL_COLOR), default=list(CL_COLOR))
            d = df[df["kode"].isin(cent) & df["klaster"].isin(pilih)].copy()
            d["lat"] = d["kode"].map(lambda k: cent[k][0])
            d["lon"] = d["kode"].map(lambda k: cent[k][1])
            fig = (px.scatter_map if hasattr(px, "scatter_map") else px.scatter_mapbox)(
                d, lat="lat", lon="lon", size=sz, size_max=28, color="klaster",
                color_discrete_map=CL_COLOR, hover_name="kabkota",
                hover_data={"lat": False, "lon": False, sz: ":.1f", "klaster": True},
                center={"lat": -2.5, "lon": 118}, zoom=3.2, opacity=0.7, **STYLE)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend_title_text="Klaster")
            st.plotly_chart(fig, width="stretch")
            st.caption("Ukuran = " + LABEL[sz] + "; warna = klaster. " + SUMBER)

# ---------------- Multivariat ----------------
with t3:
    st.subheader("Korelasi antarindikator")
    corr = comp[VARS].corr()
    fig = px.imshow(corr.values, x=[LABEL[v].split(" (")[0] for v in VARS],
                    y=[LABEL[v].split(" (")[0] for v in VARS], zmin=-1, zmax=1,
                    color_continuous_scale="RdBu_r", text_auto=".2f")
    st.plotly_chart(fig, width="stretch")
    st.caption("Korelasi bukan sebab-akibat. " + SUMBER)

    st.subheader("Sosial-ekonomi vs lingkungan (korelasi Spearman)")
    soc = ["kepadatan", "pdrb_juta", "ipm", "laju_penduduk", "tpt", "kemiskinan"]
    env = ["iklh_lahan", "iklh_udara", "iklh_air"]
    cx = comp[soc + env].corr(method="spearman").loc[soc, env]
    fig = px.imshow(cx.values, x=[LABEL[v].split(" (")[0] for v in env],
                    y=[LABEL[v].split(" (")[0] for v in soc], zmin=-1, zmax=1,
                    color_continuous_scale="RdBu_r", text_auto=".2f")
    st.plotly_chart(fig, width="stretch")
    st.info("Kepadatan paling kuat berhubungan negatif dengan kualitas lahan (-0,72) dan udara (-0,55). "
            "PDRB per kapita hampir tidak berhubungan dengan ketiga indeks lingkungan (-0,11 s.d. -0,16). "
            "TPT berhubungan negatif lemah-sedang dengan kualitas udara (-0,35) dan lahan (-0,29). "
            "Ini asosiasi, bukan sebab-akibat; urbanisasi kemungkinan ikut berperan.")

    st.subheader("Biplot PCA (seret kotak/lasso untuk memilih daerah)")
    fig = px.scatter(comp, x="PC1", y="PC2", color="klaster", color_discrete_map=CL_COLOR,
                     hover_name="kabkota", custom_data=["kode"], opacity=0.75)
    for v, r in loadings.iterrows():
        fig.add_trace(go.Scatter(x=[0, r["PC1"] * 5], y=[0, r["PC2"] * 5], mode="lines+text",
                                 text=["", v], textposition="top center",
                                 line=dict(color="#333", width=1.5), showlegend=False, hoverinfo="skip"))
    if "pencilan" in comp.columns:
        o = comp[comp["pencilan"] == True]
        fig.add_trace(go.Scatter(x=o["PC1"], y=o["PC2"], mode="markers+text", text=o["kabkota"],
                                 textposition="top center", name="Pencilan (Mahalanobis, p<0,001)",
                                 marker=dict(symbol="circle-open", size=15, color="#000", line=dict(width=2)),
                                 hoverinfo="skip"))
    fig.update_layout(dragmode="select", xaxis_title=f"PC1 ({EV1:.1f}%)".replace(".", ","), yaxis_title=f"PC2 ({EV2:.1f}%)".replace(".", ","))
    ev = st.plotly_chart(fig, width="stretch", on_select="rerun",
                         selection_mode=("box", "lasso", "points"), key="pca")
    kode_sel = [p["customdata"][0] for p in ev.selection.points if p.get("customdata")] if ev else []
    kode_sel = [str(k) for k in kode_sel]

    st.subheader("Parallel coordinates")
    sub = comp[comp["kode"].isin(kode_sel)] if kode_sel else comp
    st.caption(f"{len(sub)} daerah ditampilkan" + (" (hasil seleksi biplot)" if kode_sel else " (semua)"))
    fig = px.parallel_coordinates(sub, dimensions=VARS, color="cluster", labels=LABEL,
                                  color_continuous_scale=[[0, "#0072B2"], [0.5, "#E69F00"], [1, "#009E73"]])
    st.plotly_chart(fig, width="stretch")

    st.subheader("Profil satu daerah")
    nama = st.selectbox("Kabupaten/Kota", comp.sort_values("kabkota")["kabkota"] + " (" + comp["provinsi"] + ")")
    row = comp[(comp["kabkota"] + " (" + comp["provinsi"] + ")") == nama].iloc[0]
    pct = comp[VARS].rank(pct=True).loc[row.name] * 100
    fig = px.bar(x=pct.values, y=[LABEL[v] for v in VARS], orientation="h",
                 labels={"x": "Persentil terhadap 499 daerah", "y": ""},
                 color_discrete_sequence=[CL_COLOR[row["klaster"]]])
    fig.update_xaxes(range=[0, 100])
    st.plotly_chart(fig, width="stretch")
    st.caption(f"{row['kabkota']}: {row['klaster']}. " + SUMBER)

# ---------------- Hierarki ----------------
with t4:
    st.subheader("Struktur wilayah: Indonesia > Provinsi > Kabupaten/Kota")
    hv = st.selectbox("Warna = indikator", VARS, index=2, format_func=LABEL.get, key="hv")
    h = df.dropna(subset=[hv]).copy()
    h["Indonesia"] = "Indonesia"
    h["n"] = 1
    path = ["Indonesia", "provinsi", "kabkota"]
    kw = dict(path=path, values="n", color=hv, color_continuous_scale="Cividis",
              labels={hv: LABEL[hv], "n": "Jumlah daerah"})
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.treemap(h, **kw), width="stretch")
    c2.plotly_chart(px.sunburst(h, **kw), width="stretch")
    st.caption("Klik untuk drill-down; breadcrumb di bagian atas treemap. Ukuran = jumlah kab/kota "
               "(belum ada variabel penduduk). Warna = rata-rata indikator. " + SUMBER)