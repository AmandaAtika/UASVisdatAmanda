# -*- coding: utf-8 -*-
"""
Dasbor Webstory: Pembangunan & Kualitas Lingkungan Daerah Indonesia 2024
Data Resmi: BPS & KLHK 2024
"""
import json
import os
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

GEO = "data_processed/kabkota_bps.geojson"
DATA = "data_processed/data_master_2024.csv"
LOAD = "data_processed/pca_loadings.csv"
VAR = "data_processed/pca_variance.csv"
OUTLIER_FILE = "data_processed/daerah_pencilan.csv"
OUT = "docs/index.html"

LAB = {
    "kepadatan": "Kepadatan",
    "pdrb_juta": "PDRB/kapita",
    "ipm": "IPM",
    "tpt": "TPT",
    "usia_produktif": "Usia produktif",
    "kemiskinan": "Kemiskinan",
    "iklh_lahan": "IKLH lahan",
    "iklh_udara": "IKLH udara",
    "iklh_air": "IKLH air"
}

def pulau(kode):
    p = int(str(kode)[:2])
    return ("Sumatera" if p <= 21 else "Jawa" if p <= 36 else "Bali & Nusa Tenggara" if p <= 53 else
            "Kalimantan" if p <= 65 else "Sulawesi" if p <= 76 else "Maluku" if p <= 82 else "Papua")

print("1. Membaca data master...")
d = pd.read_csv(DATA, dtype={"kode": str})
d["pulau"] = d["kode"].apply(pulau)

# ---- 1. PETA GEOSPASIAL ----
print("2. Menyiapkan batas geospasial & variabel...")
g = gpd.read_file(GEO)[["kode", "geometry"]].merge(
    d[["kode", "kabkota", "provinsi", "penduduk", "kepadatan", "pdrb_juta", "ipm", "kemiskinan",
       "usia_produktif", "iklh_lahan", "iklh_udara", "iklh_air", "cluster", "pencilan", "pulau"]],
    on="kode", how="left")
assert g["penduduk"].notna().all(), "Kode GeoJSON dan data tidak cocok"

pt = g.geometry.representative_point()
g["lat"], g["lon"] = pt.y.round(3), pt.x.round(3)
g["geometry"] = shapely.set_precision(g.geometry.values, 0.001)

for k, n in [("penduduk", 0), ("kepadatan", 0), ("pdrb_juta", 1), ("ipm", 2),
            ("kemiskinan", 2), ("usia_produktif", 2), ("iklh_lahan", 1), ("iklh_udara", 1), ("iklh_air", 1)]:
    g[k] = g[k].round(n)

EDGES = {k: [round(float(x), 2) for x in np.nanquantile(g[k], [0, .2, .4, .6, .8, 1])]
         for k in ["kemiskinan", "ipm", "usia_produktif", "kepadatan", "iklh_lahan", "iklh_udara", "iklh_air"]}

geo = json.loads(g.to_json(drop_id=True))
for f in geo["features"]:
    c = f["properties"].get("cluster")
    f["properties"]["cluster"] = None if c is None or c != c else int(c)

# ---- 2. STATISTIK NASIONAL & PULAU ----
print("3. Menghitung ringkasan nasional & wilayah kepulauan...")
BOUNDS = {
    "Semua": [[-11.0, 95.0], [6.0, 141.0]],
    "Sumatera": [[-6.0, 95.0], [6.0, 109.0]],
    "Jawa": [[-8.8, 105.0], [-5.8, 114.6]],
    "Bali & Nusa Tenggara": [[-11.0, 114.4], [-8.0, 125.2]],
    "Kalimantan": [[-4.2, 108.5], [4.4, 119.0]],
    "Sulawesi": [[-5.8, 118.5], [2.0, 125.5]],
    "Maluku": [[-8.5, 125.5], [3.0, 131.5]],
    "Papua": [[-9.2, 130.5], [0.0, 141.0]]
}

ISLAND_STATS = {}
for pu, grp in d.groupby("pulau"):
    cl_counts = grp["cluster"].value_counts().to_dict()
    ISLAND_STATS[pu] = {
        "n": len(grp),
        "penduduk": int(grp["penduduk"].sum()),
        "ipm": round(float(grp["ipm"].mean()), 2),
        "kemiskinan": round(float(grp["kemiskinan"].mean()), 2),
        "pdrb_juta": round(float(grp["pdrb_juta"].mean()), 1),
        "kepadatan": int(round(float(grp["kepadatan"].mean()))),
        "usia_prod": round(float(grp["usia_produktif"].mean()), 1),
        "iklh_lahan": round(float(grp["iklh_lahan"].mean()), 1),
        "iklh_udara": round(float(grp["iklh_udara"].mean()), 1),
        "iklh_air": round(float(grp["iklh_air"].mean()), 1),
        "k1": int(cl_counts.get(1, 0)),
        "k2": int(cl_counts.get(2, 0)),
        "k3": int(cl_counts.get(3, 0)),
        "bounds": BOUNDS[pu]
    }

cl_nat = d["cluster"].value_counts().to_dict()
NAT_STATS = {
    "n": len(d),
    "penduduk": int(d["penduduk"].sum()),
    "ipm": round(float(d["ipm"].mean()), 2),
    "kemiskinan": round(float(d["kemiskinan"].mean()), 2),
    "pdrb_juta": round(float(d["pdrb_juta"].mean()), 1),
    "kepadatan": int(round(float(d["kepadatan"].mean()))),
    "usia_prod": round(float(d["usia_produktif"].mean()), 1),
    "iklh_lahan": round(float(d["iklh_lahan"].mean()), 1),
    "iklh_udara": round(float(d["iklh_udara"].mean()), 1),
    "iklh_air": round(float(d["iklh_air"].mean()), 1),
    "k1": int(cl_nat.get(1, 0)),
    "k2": int(cl_nat.get(2, 0)),
    "k3": int(cl_nat.get(3, 0)),
    "outliers": int(d["pencilan"].sum()),
    "bounds": BOUNDS["Semua"]
}

# ---- 3. SCATTER DATA UNTUK ALUR CERITA ----
print("4. Menyiapkan data scatter IPM vs Kemiskinan & PDRB vs IPM...")
SCATTER_IPM_POV = [
    dict(k=r.kode, n=r.kabkota, prv=r.provinsi, pu=r.pulau,
         ipm=round(float(r.ipm), 2), pov=round(float(r.kemiskinan), 2),
         pdrb=round(float(r.pdrb_juta), 1), c=int(r.cluster) if pd.notna(r.cluster) else 2,
         pend=int(r.penduduk), o=bool(r.pencilan))
    for r in d.itertuples() if pd.notna(r.ipm) and pd.notna(r.kemiskinan)
]

ANOMALIES = {
    "7206": "Morowali (Sektor Industri Logam/Nikel)",
    "9203": "Teluk Bintuni (Sektor Migas & LNG)",
    "8204": "Halmahera Tengah (Sektor Industri Logam)",
    "9401": "Mimika (Sektor Pertambangan Logam)",
    "6408": "Kutai Timur (Sektor Batubara)",
    "3571": "Kota Kediri (Sektor Industri Pengolahan & Jasa)",
    "3471": "Kota Yogyakarta (Pusat Pendidikan & Pariwisata)",
    "5171": "Kota Denpasar (Pariwisata & Perdagangan)",
    "3171": "Kota Jakarta Pusat (Pusat Keuangan & Layanan Jasa)"
}

SCATTER_PDRB_IPM = [
    dict(k=r.kode, n=r.kabkota, prv=r.provinsi, pu=r.pulau,
         pdrb=round(float(r.pdrb_juta), 1), ipm=round(float(r.ipm), 2),
         pov=round(float(r.kemiskinan), 2), c=int(r.cluster) if pd.notna(r.cluster) else 2,
         pend=int(r.penduduk), o=bool(r.pencilan), anom=ANOMALIES.get(str(r.kode), ""))
    for r in d.itertuples() if pd.notna(r.pdrb_juta) and pd.notna(r.ipm)
]

# ---- 4. PCA, LOADINGS, HEATMAP, PARALLEL COORDINATES ----
print("5. Menyiapkan analisis multivariat...")
c = d[d["data_lengkap"] == True].copy()
P = [dict(k=r.kode, n=r.kabkota, prv=r.provinsi, x=round(r.PC1, 3), y=round(r.PC2, 3), c=int(r.cluster), o=bool(r.pencilan),
          pdrb=round(r.pdrb_juta, 1), ipm=round(r.ipm, 2), miskin=round(r.kemiskinan, 2), padat=int(round(r.kepadatan)))
     for r in c.itertuples()]

L = pd.read_csv(LOAD, index_col=0)
s = 0.85 * max(c.PC1.abs().max(), c.PC2.abs().max()) / L[["PC1", "PC2"]].abs().to_numpy().max()
A = [dict(t=LAB[v], x=round(L.loc[v, "PC1"] * s, 3), y=round(L.loc[v, "PC2"] * s, 3)) for v in L.index]
VARPC = pd.read_csv(VAR)["varians_pct"].round(1).tolist()[:3]

X = c[list(L.index)].copy()
for v in ["kepadatan", "pdrb_juta", "kemiskinan"]:
    X[v] = np.log10(X[v])
Zc = ((X - X.mean()) / X.std(ddof=0)).groupby(c["cluster"].astype(int)).mean().round(2)
H = dict(z=Zc.values.tolist(), x=[LAB[v] for v in L.index], y=[f"Klaster {i}" for i in Zc.index])

PAR = [dict(k=r.kode, n=r.kabkota, c=int(r.cluster),
            kepadatan=round(float(r.kepadatan), 1),
            pdrb_juta=round(float(r.pdrb_juta), 1),
            ipm=round(float(r.ipm), 2),
            tpt=round(float(r.tpt), 2),
            usia_produktif=round(float(r.usia_produktif), 2),
            kemiskinan=round(float(r.kemiskinan), 2),
            iklh_lahan=round(float(r.iklh_lahan), 2),
            iklh_udara=round(float(r.iklh_udara), 2),
            iklh_air=round(float(r.iklh_air), 2))
       for r in c.itertuples()]

pencilan_df = pd.read_csv(OUTLIER_FILE)
OUTLIERS = {str(r.kode): dict(kabkota=r.kabkota, provinsi=r.provinsi, d2=round(float(r.d2), 1),
                              cluster=int(r.cluster), var_ekstrem=LAB.get(r.variabel_paling_ekstrem, r.variabel_paling_ekstrem))
            for r in pencilan_df.itertuples()}

# ---- 5. STRUKTUR HIERARKI ----
print("6. Menyiapkan struktur hierarki wilayah...")
t = d[["kode", "kabkota", "provinsi", "penduduk", "kemiskinan"]].copy()
t["pulau"] = t["kode"].map(pulau)
t["provinsi"] = t["provinsi"].str.title()
nodes = {}

def tambah(i, label, induk, sub):
    nodes[i] = dict(l=label, p=induk, v=int(round(sub.penduduk.sum())),
                    c=round(float((sub.kemiskinan * sub.penduduk).sum() / sub.penduduk.sum()), 2), k=sub.kode.tolist())

tambah("Indonesia", "Indonesia", "", t)
for pu, a in t.groupby("pulau"):
    ip = "Indonesia/" + pu
    tambah(ip, pu, "Indonesia", a)
    for pr, b in a.groupby("provinsi"):
        iv = ip + "/" + pr
        tambah(iv, pr, ip, b)
        for r in b.itertuples():
            tambah(iv + "/" + r.kabkota, r.kabkota, iv, b[b["kode"] == r.kode])
ids = list(nodes)
T = dict(ids=ids, labels=[nodes[i]["l"] for i in ids], parents=[nodes[i]["p"] for i in ids],
         values=[nodes[i]["v"] for i in ids], colors=[nodes[i]["c"] for i in ids])
NODE = {i: nodes[i]["k"] for i in ids}

# ---- 6. DATA LINGKUNGAN ANTAR PULAU ----
IKLH_ISLANDS = {
    pu: {
        "lahan": round(float(grp["iklh_lahan"].mean()), 1),
        "air": round(float(grp["iklh_air"].mean()), 1),
        "udara": round(float(grp["iklh_udara"].mean()), 1),
        "ipm": round(float(grp["ipm"].mean()), 2),
        "kemiskinan": round(float(grp["kemiskinan"].mean()), 2)
    }
    for pu, grp in d.groupby("pulau")
}

print("Semua data berhasil dipersiapkan.")


# ---- 7. TEMPLATE HTML DENGAN WEBSTORY LENGKAP ----
HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pembangunan dan Kualitas Lingkungan Daerah Indonesia 2024</title>
<meta name="description" content="Visualisasi data capaian pembangunan manusia, kondisi ekonomi, dan kualitas lingkungan hidup di 514 kabupaten/kota Indonesia berdasarkan data BPS & KLHK 2024.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Poppins:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
/* ============================================================
   DESIGN SYSTEM & THEME
   ============================================================ */
:root {
  --bg:        #0c1a1f;
  --bg2:       #0f2028;
  --bg-card:   #11242e;
  --surface:   rgba(255,255,255,0.04);
  --surface2:  rgba(255,255,255,0.07);
  --border:    rgba(255,255,255,0.10);
  --border2:   rgba(255,255,255,0.06);

  --txt:       #f1f5f9;
  --txt2:      #94a3b8;
  --txt3:      #64748b;

  --accent:    #5eadb6;
  --accent2:   #7ec8cf;
  --accent-g:  linear-gradient(135deg, #5eadb6, #7ec8cf);

  --c1: #fde047; /* Kuning Terang - Klaster 1 Perkotaan Padat */
  --c2: #f59e0b; /* Kuning Emas/Amber - Klaster 2 Menengah & Transisi */
  --c3: #b45309; /* Kuning Oker Tua - Klaster 3 Perdesaan */

  /* IKLH Theme */
  --iklh-lahan:   #22c55e;
  --iklh-lahan-bg: rgba(34,197,94,0.12);
  --iklh-air:     #5eadb6;
  --iklh-air-bg:  rgba(94,173,182,0.12);
  --iklh-udara:   #94a3b8;
  --iklh-udara-bg: rgba(148,163,184,0.12);

  --sh-sm: 0 2px 8px rgba(0,0,0,0.4);
  --sh-md: 0 8px 32px rgba(0,0,0,0.5);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }

body {
  font-family: 'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: var(--bg);
  color: var(--txt);
  min-height: 100vh;
  overflow-x: hidden;
  line-height: 1.65;
}

/* ============================================================
   LEAFLET TOOLTIP OVERRIDE: HILANGKAN OUTLINE PUTIH
   ============================================================ */
.leaflet-tooltip {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.leaflet-tooltip-top::before,
.leaflet-tooltip-bottom::before,
.leaflet-tooltip-left::before,
.leaflet-tooltip-right::before {
  display: none !important;
  border: none !important;
}

/* ============================================================
   STICKY NAV RIBBON
   ============================================================ */
.story-ribbon {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(12,26,31,0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 24px;
  gap: 16px;
}

.brand-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #fff;
  white-space: nowrap;
}
.brand-badge span {
  background: linear-gradient(135deg, #d4a574, #e8c9a0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.story-nav-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  padding: 2px 0;
  scrollbar-width: none;
}
.story-nav-pills::-webkit-scrollbar { display: none; }

.story-pill {
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  color: var(--txt2);
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border2);
  border-radius: 20px;
  padding: 5px 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 5px;
}
.story-pill:hover {
  background: rgba(255,255,255,0.08);
  color: #fff;
  border-color: var(--border);
}
.story-pill.active {
  background: rgba(94,173,182,0.18);
  color: var(--accent);
  border-color: rgba(94,173,182,0.4);
  box-shadow: 0 0 10px rgba(94,173,182,0.2);
}





/* ============================================================
   STORY LAYOUT & TRANSISI HALUS SAAT SCROLL
   ============================================================ */
.story-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 28px 80px;
}

/* Transisi halus saat scroll */
.story-chapter {
  position: relative;
  padding: 44px 0 20px;
  scroll-margin-top: 60px;
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1), transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: opacity, transform;
}
.story-chapter.visible {
  opacity: 1;
  transform: translateY(0);
}

.chapter-header {
  margin-bottom: 22px;
}

.chapter-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(94,173,182,0.12);
  border: 1px solid rgba(94,173,182,0.25);
  color: var(--accent);
  margin-bottom: 12px;
}
.chapter-badge.green {
  background: rgba(34,197,94,0.10);
  border-color: rgba(34,197,94,0.25);
  color: #4ade80;
}
.chapter-badge.amber {
  background: rgba(245,158,11,0.10);
  border-color: rgba(245,158,11,0.25);
  color: #fbbf24;
}

.chapter-title {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: #fff;
  margin-bottom: 12px;
}
.chapter-title .hl-blue  { color: var(--accent); }
.chapter-title .hl-green { color: var(--iklh-lahan); }
.chapter-title .hl-amber { color: var(--c1); }

.chapter-lead {
  font-size: 15px;
  line-height: 1.7;
  color: var(--txt2);
  max-width: 950px;
}

/* Pembatas alur cerita */
.story-flow-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 34px 0 16px;
  gap: 8px;
}
.flow-line {
  width: 2px;
  height: 30px;
  background: linear-gradient(to bottom, rgba(56,189,248,0.4), rgba(56,189,248,0.08));
}
.flow-arrow-circle {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(56,189,248,0.1);
  border: 1px solid rgba(56,189,248,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  font-size: 13px;
  box-shadow: 0 0 12px rgba(56,189,248,0.15);
  animation: bounceSoft 2.5s infinite;
}
@keyframes bounceSoft {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(4px); }
}
.flow-text {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--txt3);
}

/* Catatan narasi */
.story-callout {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 18px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--txt2);
}
.story-callout strong { color: var(--txt); }
.story-callout.green { border-left-color: var(--iklh-lahan); }
.story-callout.amber { border-left-color: var(--c1); }

/* Panels */
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--sh-md);
  transition: border-color 0.2s;
}
.panel:hover { border-color: rgba(255,255,255,0.14); }

.panel-head {
  padding: 12px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border2);
  background: rgba(255,255,255,0.015);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--txt);
}
.panel-icon {
  width: 30px; height: 30px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
.icon-geo  { background: rgba(56,189,248,0.15); }
.icon-mv   { background: rgba(129,140,248,0.15); }
.icon-hier { background: rgba(52,211,153,0.15); }
.icon-det  { background: rgba(245,158,11,0.15); }
.icon-iklh { background: rgba(34,197,94,0.15); }

.panel-foot {
  padding: 8px 18px;
  font-size: 11px;
  color: var(--txt3);
  border-top: 1px solid var(--border2);
  line-height: 1.5;
  background: rgba(0,0,0,0.12);
}

/* Segmented Control */
.seg-ctrl {
  display: flex;
  background: rgba(0,0,0,0.25);
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}
.seg-btn {
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 11px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--txt3);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.seg-btn.active {
  background: rgba(56,189,248,0.18);
  color: var(--accent);
  box-shadow: 0 0 0 1px rgba(56,189,248,0.3);
}
.seg-btn:hover:not(.active) { color: var(--txt); background: var(--surface2); }

/* ============================================================
   ACT 1: OPENING HERO
   ============================================================ */
.hero-box {
  padding: 48px 36px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(14,22,44,0.9) 0%, rgba(9,14,28,0.95) 100%);
  border: 1px solid rgba(56,189,248,0.2);
  box-shadow: var(--sh-md);
  position: relative;
  overflow: hidden;
}
.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 12px;
}
.hero-title {
  font-size: 38px;
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.2;
  color: #fff;
  margin-bottom: 16px;
}
.hero-desc {
  font-size: 15.5px;
  line-height: 1.7;
  color: var(--txt2);
  max-width: 900px;
  margin-bottom: 22px;
}
.hero-pillars {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.pillar-badge {
  font-size: 11.5px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border);
  color: var(--txt);
  display: flex;
  align-items: center;
  gap: 6px;
}
.pillar-badge.green { border-color: rgba(34,197,94,0.3); color: #4ade80; background: rgba(34,197,94,0.08); }
.pillar-badge.blue  { border-color: rgba(56,189,248,0.3); color: #38bdf8; background: rgba(56,189,248,0.08); }
.pillar-badge.amber { border-color: rgba(245,158,11,0.3); color: #fbbf24; background: rgba(245,158,11,0.08); }

/* ============================================================
   ACT 2: 514 KAB/KOTA STATS
   ============================================================ */
.stats-grid-6 {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card-big {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  transition: transform 0.2s, border-color 0.2s;
}
.stat-card-big:hover {
  transform: translateY(-2px);
  border-color: rgba(56,189,248,0.3);
}
.stat-card-val {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.stat-card-lbl {
  font-size: 11px;
  color: var(--txt2);
  margin-top: 4px;
  font-weight: 500;
}
.stat-card-sub {
  font-size: 9.5px;
  color: var(--txt3);
  margin-top: 2px;
}

.island-cards-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}
.island-mini-card {
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 10px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.island-mini-card:hover, .island-mini-card.active {
  background: rgba(56,189,248,0.12);
  border-color: rgba(56,189,248,0.4);
  transform: translateY(-2px);
}
.island-card-title {
  font-size: 11.5px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.island-card-pop {
  font-size: 10px;
  color: var(--txt3);
  margin-top: 2px;
}
.island-card-stat {
  font-size: 11px;
  font-weight: 600;
  margin-top: 5px;
  color: var(--accent);
}

/* ============================================================
   ACT 3: MAP & CONTROLS DI ATAS PETA
   ============================================================ */
.island-filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 12px;
  scrollbar-width: none;
}
.island-filter-bar::-webkit-scrollbar { display: none; }

.island-btn {
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  padding: 5px 13px;
  border-radius: 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--txt2);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.island-btn:hover { background: var(--surface2); color: #fff; }
.island-btn.active {
  background: rgba(56,189,248,0.18);
  color: var(--accent);
  border-color: rgba(56,189,248,0.4);
}

/* Toolbar khusus di atas peta (tidak menutupi zoom) */
.map-top-bar {
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--border2);
  flex-wrap: wrap;
}
.map-selector-label {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--txt2);
}
.map-var-select {
  background: #090e1c;
  border: 1px solid var(--border);
  color: #fff;
  border-radius: 7px;
  padding: 5px 12px;
  font-size: 12px;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  min-width: 220px;
}
.map-var-select option {
  background: #090e1c;
  color: #fff;
}

.row-map-custom {
  display: grid;
  grid-template-columns: 1.55fr 1fr;
  gap: 16px;
  align-items: start;
}

#map-container {
  height: 520px;
  border-radius: 8px;
  overflow: hidden;
  background: #090e1c;
}

.map-ctrl-box {
  background: rgba(9,14,28,0.92);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 11px;
  color: var(--txt);
  box-shadow: var(--sh-md);
}
.sw {
  display: inline-block;
  width: 11px;
  height: 11px;
  border-radius: 2px;
  margin-right: 6px;
  vertical-align: middle;
}

/* Detail Panel */
.detail-box-inner {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.nat-header {
  border-bottom: 1px solid var(--border2);
  padding-bottom: 10px;
}
.nat-title {
  font-size: 17px;
  font-weight: 800;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}
.nat-sub {
  font-size: 11.5px;
  color: var(--txt2);
  margin-top: 3px;
}
.nat-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(56,189,248,0.12);
  color: var(--accent);
  border: 1px solid rgba(56,189,248,0.25);
  margin-top: 6px;
}

.kpi-grid-6 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.kpi-card-mini {
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 9px;
  text-align: center;
}
.kpi-lbl {
  font-size: 9.5px;
  color: var(--txt3);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 700;
}
.kpi-val {
  font-size: 17px;
  font-weight: 800;
  color: #fff;
  margin-top: 2px;
}
.kpi-unit {
  font-size: 10px;
  font-weight: 400;
  color: var(--txt3);
  margin-left: 2px;
}

.iklh-panel-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.iklh-card-custom {
  border-radius: 8px;
  padding: 10px 8px;
  text-align: center;
  border: 1px solid transparent;
}
.iklh-card-custom.lahan {
  background: var(--iklh-lahan-bg);
  border-color: rgba(34,197,94,0.25);
}
.iklh-card-custom.air {
  background: var(--iklh-air-bg);
  border-color: rgba(56,189,248,0.25);
}
.iklh-card-custom.udara {
  background: var(--iklh-udara-bg);
  border-color: rgba(148,163,184,0.25);
}
.iklh-c-val {
  font-size: 18px;
  font-weight: 800;
}
.iklh-c-lbl {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  margin-top: 2px;
}

.cluster-pills-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
}
.cl-chip {
  flex: 1;
  padding: 5px 6px;
  border-radius: 6px;
  text-align: center;
  font-weight: 600;
  border: 1px solid transparent;
}
.cl-chip.k1 { background: rgba(253,224,71,0.16); color: #fef08a; border-color: rgba(253,224,71,0.35); }
.cl-chip.k2 { background: rgba(245,158,11,0.16); color: #fde68a; border-color: rgba(245,158,11,0.35); }
.cl-chip.k3 { background: rgba(180,83,9,0.22); color: #fcd34d; border-color: rgba(180,83,9,0.4); }

.island-comparison-bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.comp-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.comp-bar-name {
  width: 90px;
  color: var(--txt2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.comp-bar-track {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
  overflow: hidden;
}
.comp-bar-fill {
  height: 100%;
  border-radius: 3px;
}
.comp-bar-val {
  width: 40px;
  text-align: right;
  font-weight: 700;
  color: var(--txt);
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}

.btn-back-nat {
  width: 100%;
  padding: 8px;
  border-radius: 8px;
  background: rgba(56,189,248,0.12);
  border: 1px solid rgba(56,189,248,0.25);
  color: var(--accent);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.btn-back-nat:hover { background: rgba(56,189,248,0.2); }

/* ============================================================
   ACT 4 & 5: SCATTER PLOTS
   ============================================================ */
.scatter-plot-box {
  height: 430px;
  width: 100%;
}

.anomaly-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.anom-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 5px;
  background: rgba(255,255,255,0.05);
  color: var(--txt2);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.15s;
}
.anom-tag:hover {
  background: rgba(56,189,248,0.15);
  color: #fff;
  border-color: rgba(56,189,248,0.3);
}

/* ============================================================
   ACT 6: DIMENSI LINGKUNGAN (IKLH)
   ============================================================ */
.iklh-dimension-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}
.iklh-dimension-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px 18px;
  border: 1px solid var(--border);
  position: relative;
  overflow: hidden;
}
.iklh-dimension-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}
.iklh-dimension-card.lahan::before { background: var(--iklh-lahan); }
.iklh-dimension-card.air::before   { background: var(--iklh-air); }
.iklh-dimension-card.udara::before { background: var(--iklh-udara); }

.iklh-dim-icon { font-size: 28px; margin-bottom: 10px; }
.iklh-dim-title { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 6px; }
.iklh-dim-desc { font-size: 12.5px; line-height: 1.6; color: var(--txt2); margin-bottom: 12px; }
.iklh-dim-stat { display: flex; align-items: baseline; gap: 8px; }
.iklh-dim-score { font-size: 26px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
.iklh-dim-status { font-size: 11px; font-weight: 600; }

#iklh-island-chart { height: 360px; width: 100%; }

/* ============================================================
   ACT 7: PCA & CLUSTER
   ============================================================ */
#pca-view, #par-view, #hm-view { height: 430px; width: 100%; }

.outlier-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 16px;
}
.outlier-chip {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 5px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  color: var(--txt2);
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.outlier-chip:hover {
  background: rgba(56,189,248,0.15);
  border-color: rgba(56,189,248,0.3);
  color: #fff;
}
.d2-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  background: rgba(0,0,0,0.3);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--accent);
}

/* ============================================================
   ACT 8: HIERARCHY
   ============================================================ */
#tm-view { height: 460px; width: 100%; }

/* ============================================================
   ACT 9: CONCLUSION & FOOTER
   ============================================================ */
.conclusion-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.conclusion-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}
.conclusion-card-num {
  width: 28px; height: 28px;
  border-radius: 6px;
  background: rgba(56,189,248,0.12);
  color: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 12px;
}
.conclusion-card-title {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
}
.conclusion-card-desc {
  font-size: 13px;
  line-height: 1.6;
  color: var(--txt2);
}

footer {
  margin-top: 50px;
  padding: 28px 0;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 11.5px;
  color: var(--txt3);
  line-height: 1.8;
}

@media (max-width: 1100px) {
  .row-map-custom, .iklh-dimension-grid, .conclusion-grid { grid-template-columns: 1fr; }
  .stats-grid-6 { grid-template-columns: repeat(3, 1fr); }
  .island-cards-grid { grid-template-columns: repeat(4, 1fr); }
}
@media (max-width: 640px) {
  .stats-grid-6 { grid-template-columns: repeat(2, 1fr); }
  .island-cards-grid { grid-template-columns: repeat(2, 1fr); }
  .hero-title { font-size: 26px; }
  .chapter-title { font-size: 22px; }
}

/* ============================================================
   FULL-SCREEN HERO LANDING (PHOTO-BASED)
   ============================================================ */
#landing-hero {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  overflow: hidden;
}

/* Background image */
#landing-hero .hero-bg-img {
  position: absolute;
  inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  object-position: center 40%;
  z-index: 0;
}

/* Dark gradient overlay for readability */
#landing-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(8,20,26,0.88) 0%, rgba(8,20,26,0.65) 40%, rgba(8,20,26,0.15) 75%, transparent 100%),
    linear-gradient(180deg, rgba(8,20,26,0.3) 0%, transparent 40%, rgba(8,20,26,0.6) 100%);
  z-index: 1;
  pointer-events: none;
}

/* Warm glow accent */
#landing-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 50% 70% at 15% 50%, rgba(212,165,116,0.12) 0%, transparent 70%),
    radial-gradient(ellipse 40% 50% at 70% 80%, rgba(94,173,182,0.06) 0%, transparent 70%);
  z-index: 1;
  pointer-events: none;
}

.hero-landing-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  padding: 0 60px;
  max-width: 700px;
  gap: 20px;
  animation: heroFadeUp 1.2s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes heroFadeUp {
  from { opacity: 0; transform: translateY(40px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Eyebrow badge */
.hero-landing-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Poppins', sans-serif;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(212,165,116,0.9);
  background: rgba(212,165,116,0.08);
  border: 1px solid rgba(212,165,116,0.2);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 30px;
  padding: 6px 16px;
  animation: heroFadeUp 1.2s 0.1s cubic-bezier(0.16,1,0.3,1) both;
}
.hero-landing-badge i { color: #d4a574; font-size: 12px; }

/* Title */
.hero-landing-title {
  font-family: 'Poppins', sans-serif;
  font-size: clamp(32px, 5vw, 56px);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: #f5efe6;
  animation: heroFadeUp 1.2s 0.2s cubic-bezier(0.16,1,0.3,1) both;
}
.hero-landing-title .word-highlight {
  display: inline;
  background: linear-gradient(135deg, #d4a574 0%, #e8c9a0 50%, #f5dfc0 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Subtitle */
.hero-landing-sub {
  font-family: 'Poppins', sans-serif;
  font-size: 15px;
  line-height: 1.7;
  color: rgba(200,210,215,0.85);
  max-width: 520px;
  animation: heroFadeUp 1.2s 0.3s cubic-bezier(0.16,1,0.3,1) both;
}

/* Scroll indicator at bottom center */
.hero-scroll-hint {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  animation: heroFadeUp 1.2s 0.5s cubic-bezier(0.16,1,0.3,1) both;
  cursor: pointer;
  transition: opacity 0.3s;
}
.hero-scroll-hint:hover { opacity: 0.7; }
.hero-scroll-hint .scroll-label {
  font-family: 'Poppins', sans-serif;
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(200,210,215,0.6);
}
.scroll-mouse {
  width: 24px;
  height: 38px;
  border-radius: 12px;
  border: 2px solid rgba(200,210,215,0.35);
  display: flex;
  justify-content: center;
  padding-top: 7px;
}
.scroll-mouse-dot {
  width: 3px;
  height: 7px;
  background: rgba(200,210,215,0.6);
  border-radius: 2px;
  animation: scrollDot 2s ease-in-out infinite;
}
@keyframes scrollDot {
  0%   { transform: translateY(0);  opacity: 1; }
  60%  { transform: translateY(10px); opacity: 0; }
  61%  { transform: translateY(0);  opacity: 0; }
  100% { transform: translateY(0);  opacity: 1; }
}

/* NAV: initially hidden on hero, show when scrolled */
.story-ribbon { transition: opacity 0.4s, transform 0.4s; }
.story-ribbon.hidden-on-hero {
  opacity: 0;
  pointer-events: none;
  transform: translateY(-100%);
}

@media (max-width: 768px) {
  .hero-landing-content { padding: 0 28px; }
  .hero-landing-title { font-size: clamp(28px, 7vw, 42px); }
}
</style>
</head>
<body>

<!-- ============================================================
     FULL-SCREEN HERO LANDING PAGE
     ============================================================ -->
<section id="landing-hero">
  <!-- Background image -->
  <img class="hero-bg-img" src="landing_page.jpg" alt="Peta Indonesia 3D">

  <div class="hero-landing-content">
    <!-- Eyebrow badge -->
    <div class="hero-landing-badge">
      <i class="fa-solid fa-chart-pie"></i>
      Visualisasi Data &bull; BPS &amp; KLHK 2024
    </div>

    <!-- Title: left-aligned -->
    <h1 class="hero-landing-title">
      Menjelajahi<br>
      <span class="word-highlight">Karakteristik<br>Indonesia</span>
    </h1>

    <!-- Subtitle -->
    <p class="hero-landing-sub">
      Berdasarkan Indikator Sosial, Ekonomi,<br>dan Lingkungan di 514 Kabupaten/Kota
    </p>
  </div>

  <!-- Scroll down indicator -->
  <div class="hero-scroll-hint" onclick="document.getElementById('story-start').scrollIntoView({behavior:'smooth'})">
    <div class="scroll-mouse"><div class="scroll-mouse-dot"></div></div>
    <span class="scroll-label">Scroll untuk Menjelajahi</span>
  </div>
</section>

<!-- ============================================================
     STICKY NAV RIBBON (hidden until user scrolls past hero)
     ============================================================ -->
<nav class="story-ribbon hidden-on-hero" id="story-ribbon">
  <div class="brand-badge">
    <span>DATA DAERAH 2024</span> &bull; BPS &amp; KLHK
  </div>

  <div class="story-nav-pills" id="story-nav-pills">
    <button class="story-pill active" onclick="scrollToAct('sec-opening')"><i class="fa-solid fa-compass"></i> Pembuka</button>
    <button class="story-pill" onclick="scrollToAct('sec-514')"><i class="fa-solid fa-chart-simple"></i> 514 Daerah</button>
    <button class="story-pill" onclick="scrollToAct('sec-geo')"><i class="fa-solid fa-map-location-dot"></i> Peta Sebaran</button>
    <button class="story-pill" onclick="scrollToAct('sec-ipm-pov')"><i class="fa-solid fa-chart-line"></i> IPM &amp; Kemiskinan</button>
    <button class="story-pill" onclick="scrollToAct('sec-pdrb-ipm')"><i class="fa-solid fa-coins"></i> PDRB &amp; IPM</button>
    <button class="story-pill" onclick="scrollToAct('sec-iklh')"><i class="fa-solid fa-leaf"></i> Lingkungan Hidup</button>
    <button class="story-pill" onclick="scrollToAct('sec-mv')"><i class="fa-solid fa-cubes"></i> Tipe Daerah (PCA)</button>
    <button class="story-pill" onclick="scrollToAct('sec-hier')"><i class="fa-solid fa-sitemap"></i> Struktur Wilayah</button>
    <button class="story-pill" onclick="scrollToAct('sec-conclusion')"><i class="fa-solid fa-flag-checkered"></i> Catatan Penutup</button>
  </div>
</nav>

<!-- Story start anchor -->
<div id="story-start"></div>

<!-- ============================================================
     KONTEN UTAMA WEBSTORY
     ============================================================ -->
<div class="story-container">

  <!-- ── ACT 1: PEMBUKA ── -->
  <section class="story-chapter visible" id="sec-opening" style="padding-top:16px;">
    <div class="chapter-header">
      <div class="chapter-badge">BAB 00 &bull; PENGANTAR</div>
      <h2 class="chapter-title">
        Seberapa Merata <span class="hl-blue">Pembangunan di Indonesia?</span>
      </h2>
      <p class="chapter-lead">
        Indonesia terdiri dari 514 kabupaten dan kota yang tersebar di 38 provinsi. Setiap daerah memiliki karakteristik geografis, potensi ekonomi, dan tantangan yang berbeda. Melalui visualisasi data resmi BPS dan KLHK tahun 2024, kita melihat gambaran capaian pembangunan manusia, kondisi ekonomi antardaerah, hingga kualitas lingkungan hidup di seluruh Indonesia.
      </p>
    </div>
    <div class="hero-pillars" style="margin-bottom:20px;">
      <div class="pillar-badge blue"><i class="fa-solid fa-user-graduate"></i> Capaian Pembangunan Manusia (IPM)</div>
      <div class="pillar-badge amber"><i class="fa-solid fa-wallet"></i> Perekonomian &amp; Kemiskinan</div>
      <div class="pillar-badge green"><i class="fa-solid fa-tree"></i> Kualitas Lingkungan Hidup</div>
    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Gambaran Umum 514 Kabupaten dan Kota</span>
    </div>
  </section>

  <!-- ── ACT 2: 514 KAB/KOTA ── -->
  <section class="story-chapter" id="sec-514">
    <div class="chapter-header">
      <div class="chapter-badge">BAB 01 &bull; GAMBARAN UMUM</div>
      <h2 class="chapter-title">
        Potret <span class="hl-blue">514 Kabupaten dan Kota</span> di Indonesia
      </h2>
      <p class="chapter-lead">
        Indonesia memiliki sekitar 281 juta penduduk yang tersebar di berbagai pulau. Sebagian besar penduduk bertempat tinggal di Pulau Jawa, sementara pulau-pulau lainnya memiliki sebaran penduduk dan kepadatan yang bervariasi. Keragaman ini menjadi dasar penting dalam memahami capaian pembangunan di setiap wilayah.
      </p>
    </div>

    <!-- 6 Kartu Statistik Kunci -->
    <div class="stats-grid-6">
      <div class="stat-card-big">
        <div class="stat-card-val" id="stat-tot-kab">514</div>
        <div class="stat-card-lbl">Kabupaten &amp; Kota</div>
        <div class="stat-card-sub">38 Provinsi Indonesia</div>
      </div>
      <div class="stat-card-big">
        <div class="stat-card-val" id="stat-tot-pop">281,6 Jt</div>
        <div class="stat-card-lbl">Total Penduduk</div>
        <div class="stat-card-sub">Sekitar 55,7% di Pulau Jawa</div>
      </div>
      <div class="stat-card-big">
        <div class="stat-card-val" id="stat-avg-ipm" style="color:#38bdf8;">72,02</div>
        <div class="stat-card-lbl">Rata-rata IPM</div>
        <div class="stat-card-sub">Rentang: 34,14 – 88,61</div>
      </div>
      <div class="stat-card-big">
        <div class="stat-card-val" id="stat-avg-pov" style="color:#f59e0b;">11,17%</div>
        <div class="stat-card-lbl">Rerata Kemiskinan</div>
        <div class="stat-card-sub">Rentang: 1,53% – 41,52%</div>
      </div>
      <div class="stat-card-big">
        <div class="stat-card-val" id="stat-avg-pdrb">Rp 42,9 Jt</div>
        <div class="stat-card-lbl">PDRB/kapita ADHK</div>
        <div class="stat-card-sub">Nilai tengah antardaerah</div>
      </div>
      <div class="stat-card-big">
        <div class="stat-card-val" id="stat-tot-out" style="color:#38bdf8;">13</div>
        <div class="stat-card-lbl">Daerah Pencilan</div>
        <div class="stat-card-sub">Karakteristik kombinasi unik</div>
      </div>
    </div>

    <!-- Kartu Wilayah Kepulauan -->
    <div class="story-callout">
      <strong>Navigasi Cepat Wilayah:</strong> Klik salah satu kartu kepulauan di bawah ini untuk melihat ringkasan data wilayah tersebut pada panel peta di bab selanjutnya.
    </div>

    <div class="island-cards-grid" id="island-quick-cards"></div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Persebaran Pembangunan di Peta Indonesia</span>
    </div>
  </section>

  <!-- ── ACT 3: PETA GEOSPASIAL ── -->
  <section class="story-chapter" id="sec-geo">
    <div class="chapter-header">
      <div class="chapter-badge">BAB 02 &bull; ANALISIS WILAYAH (TOPIK E)</div>
      <h2 class="chapter-title">
        <i class="fa-solid fa-map-location-dot" style="color:var(--accent);margin-right:6px;"></i> Persebaran Pembangunan di <span class="hl-blue">Peta Indonesia</span>
      </h2>
      <p class="chapter-lead">
        Peta ini menampilkan persebaran berbagai indikator pembangunan di tingkat kabupaten dan kota. Anda dapat memilih indikator melalui menu pilihan di atas peta, mengubah jenis tampilan peta, serta memilih pulau yang ingin diamati.
        <strong>Sebelum memilih daerah tertentu, panel di sebelah kanan menampilkan ringkasan data nasional atau wilayah pulau yang sedang aktif.</strong>
      </p>
    </div>

    <!-- Filter Bar Pulau -->
    <div class="island-filter-bar" id="island-filter-bar">
      <button class="island-btn active" onclick="setIslandFilter('Semua')"><i class="fa-solid fa-earth-asia"></i> Seluruh Indonesia</button>
      <button class="island-btn" onclick="setIslandFilter('Sumatera')"><i class="fa-solid fa-mountain-sun"></i> Sumatera</button>
      <button class="island-btn" onclick="setIslandFilter('Jawa')"><i class="fa-solid fa-city"></i> Jawa</button>
      <button class="island-btn" onclick="setIslandFilter('Bali & Nusa Tenggara')"><i class="fa-solid fa-umbrella-beach"></i> Bali &amp; NT</button>
      <button class="island-btn" onclick="setIslandFilter('Kalimantan')"><i class="fa-solid fa-tree"></i> Kalimantan</button>
      <button class="island-btn" onclick="setIslandFilter('Sulawesi')"><i class="fa-solid fa-water"></i> Sulawesi</button>
      <button class="island-btn" onclick="setIslandFilter('Maluku')"><i class="fa-solid fa-fish"></i> Maluku</button>
      <button class="island-btn" onclick="setIslandFilter('Papua')"><i class="fa-solid fa-mountain"></i> Papua</button>
    </div>

    <!-- Row Peta + Panel Rinci -->
    <div class="row-map-custom">

      <!-- PETA -->
      <div class="panel">
        <div class="panel-head">
          <div class="panel-title">
            <div class="panel-icon icon-geo"><i class="fa-solid fa-map" style="color:var(--accent);"></i></div>
            Peta Persebaran 514 Kabupaten/Kota
          </div>
          <div class="seg-ctrl">
            <button class="seg-btn active" id="btn-map-choro" onclick="setMapMode('choro')">Koroplet</button>
            <button class="seg-btn" id="btn-map-sym" onclick="setMapMode('sym')">Simbol Proporsional</button>
          </div>
        </div>

        <!-- PILIHAN INDIKATOR DI ATAS PETA (TIDAK MENGHALANGI ZOOM) -->
        <div class="map-top-bar">
          <div style="display:flex;align-items:center;gap:10px;">
            <label for="map-var-select" class="map-selector-label">PILIH INDIKATOR PETA:</label>
            <select id="map-var-select" class="map-var-select">
              <option value="kemiskinan" selected>Persentase Kemiskinan (%)</option>
              <option value="ipm">Indeks Pembangunan Manusia</option>
              <option value="usia_produktif">Usia Produktif (% penduduk)</option>
              <option value="kepadatan">Kepadatan Penduduk (jiwa/km²)</option>
              <option value="iklh_lahan">IKLH Lahan (Tutupan Hutan/Vegetasi)</option>
              <option value="iklh_air">IKLH Air (Baku Mutu Air)</option>
              <option value="iklh_udara">IKLH Udara (Kualitas Udara ISPU)</option>
              <option value="cluster">Klaster Pembangunan</option>
            </select>
          </div>
          <span style="font-size:11px;color:var(--txt3);">Metode: 5 Kuantil Berimbang</span>
        </div>

        <div style="padding:10px 14px 0;">
          <div id="map-container"></div>
        </div>
        <div class="panel-foot">
          <strong>Sumber Data:</strong> BPS &amp; KLHK (2024) &bull; Batas wilayah: Alf-Anas (Juni 2023) &bull; Arahkan kursor ke wilayah untuk melihat tooltip tanpa outline putih.
        </div>
      </div>

      <!-- DETAIL PANEL (DEFAULT: RINGKASAN NASIONAL / WILAYAH) -->
      <div class="panel" id="detail-panel" style="display:flex;flex-direction:column;min-height:580px;">
        <div class="panel-head">
          <div class="panel-title">
            <div class="panel-icon icon-det"><i class="fa-solid fa-id-card" style="color:#f59e0b;"></i></div>
            <span id="detail-panel-title">Profil Wilayah</span>
          </div>
          <span id="detail-panel-badge" class="nat-badge">Ringkasan Nasional</span>
        </div>

        <div style="flex:1; overflow-y:auto;" id="detail-content-wrapper"></div>

        <div class="panel-foot" style="background:rgba(0,0,0,0.18);">
          Klik wilayah pada peta untuk melihat profil per kabupaten/kota, atau gunakan tombol reset untuk kembali.
        </div>
      </div>

    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Hubungan antara IPM dan Tingkat Kemiskinan</span>
    </div>
  </section>

  <!-- ── ACT 4: IPM vs KEMISKINAN ── -->
  <section class="story-chapter" id="sec-ipm-pov">
    <div class="chapter-header">
      <div class="chapter-badge green">BAB 03 &bull; PEMBANGUNAN MANUSIA</div>
      <h2 class="chapter-title">
        Hubungan antara <span class="hl-green">IPM dan Tingkat Kemiskinan</span>
      </h2>
      <p class="chapter-lead">
        Indeks Pembangunan Manusia (IPM) mencerminkan kualitas kesehatan, tingkat pendidikan, dan standar hidup layak. Secara statistik, terdapat hubungan negatif yang cukup kuat antara capaian IPM dan persentase kemiskinan di 514 kabupaten/kota (<strong>korelasi r = -0,70</strong>). Daerah dengan IPM yang lebih tinggi umumnya mencatatkan angka kemiskinan yang lebih rendah.
      </p>
    </div>

    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-head">
        <div class="panel-title">
          <div class="panel-icon icon-mv"><i class="fa-solid fa-chart-line" style="color:#4ade80;"></i></div>
          Diagram Tebaran: IPM vs Persentase Kemiskinan
        </div>
        <div style="font-size:11px;color:var(--txt3);">
          Garis Tren Kuadratik &bull; Warna Berdasarkan Klaster Daerah
        </div>
      </div>
      <div style="padding:12px 16px 6px;">
        <div id="scatter-ipm-pov" class="scatter-plot-box"></div>
      </div>
      <div class="panel-foot">
        <strong>Pola Data:</strong> Sebagian besar daerah dengan IPM di atas 75 memiliki angka kemiskinan di bawah 7%. Pada daerah dengan IPM 70–75, persentase kemiskinan berkisar antara 4% hingga 15%, yang mengindikasikan bahwa perbaikan modal manusia perlu didukung oleh perluasan lapangan kerja lokal yang merata.
      </div>
    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Hubungan antara PDRB per Kapita dan IPM</span>
    </div>
  </section>

  <!-- ── ACT 5: PDRB vs IPM ── -->
  <section class="story-chapter" id="sec-pdrb-ipm">
    <div class="chapter-header">
      <div class="chapter-badge amber">BAB 04 &bull; EKONOMI &amp; KESEJAHTERAAN</div>
      <h2 class="chapter-title">
        PDRB per Kapita dan <span class="hl-amber">Capaian IPM</span> di Berbagai Daerah
      </h2>
      <p class="chapter-lead">
        PDRB per kapita mengukur nilai tambah barang dan jasa yang dihasilkan di suatu daerah. Korelasi antara PDRB per kapita dengan capaian IPM berada pada tingkat sedang (<strong>r = 0,33</strong>). Daerah dengan kegiatan industri pengolahan tambang dan migas yang berskala besar cenderung memiliki PDRB per kapita yang sangat tinggi, sedangkan daerah berbasis jasa dan pendidikan seperti Yogyakarta dan Denpasar mencatatkan IPM tinggi dengan PDRB per kapita yang berada pada tingkat moderat.
      </p>
    </div>

    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-head">
        <div class="panel-title">
          <div class="panel-icon" style="background:rgba(245,158,11,0.15);"><i class="fa-solid fa-coins" style="color:#fbbf24;"></i></div>
          Diagram Tebaran: PDRB per Kapita ADHK (Skala Logaritmik) vs IPM
        </div>
        <div style="font-size:11px;color:var(--txt3);">
          Klik salah satu label daerah di bawah untuk menyorot posisinya di grafik
        </div>
      </div>
      <div style="padding:12px 16px 6px;">
        <div id="scatter-pdrb-ipm" class="scatter-plot-box"></div>
      </div>
      <div style="padding:0 18px 12px;">
        <div style="font-size:11px;font-weight:700;color:var(--txt2);text-transform:uppercase;margin-bottom:6px;">
          Contoh Karakteristik Berdasarkan Sektor Utama Daerah:
        </div>
        <div class="anomaly-tags-row">
          <span class="anom-tag" onclick="focusKabkota('7206')">Morowali &bull; PDRB Rp570 Jt | IPM 73,5 | Sektor Industri Logam</span>
          <span class="anom-tag" onclick="focusKabkota('9203')">Teluk Bintuni &bull; PDRB Rp384 Jt | IPM 69,8 | Sektor Migas &amp; LNG</span>
          <span class="anom-tag" onclick="focusKabkota('8204')">Halmahera Tengah &bull; PDRB Rp294 Jt | IPM 68,5 | Sektor Industri Logam</span>
          <span class="anom-tag" onclick="focusKabkota('9401')">Mimika &bull; PDRB Rp277 Jt | IPM 76,9 | Sektor Pertambangan</span>
          <span class="anom-tag" onclick="focusKabkota('3471')">Kota Yogyakarta &bull; PDRB Rp95 Jt | IPM 88,61 | Pendidikan &amp; Wisata</span>
          <span class="anom-tag" onclick="focusKabkota('5171')">Kota Denpasar &bull; PDRB Rp86 Jt | Kemiskinan 1,53% | Pariwisata &amp; Jasa</span>
        </div>
      </div>
      <div class="panel-foot">
        <strong>Catatan Analisis:</strong> Tingginya PDRB pada daerah industri ekstraktif didorong oleh besarnya modal dan nilai komoditas. Di daerah-daerah ini, penguatan layanan kesehatan, fasilitas sekolah, serta pelatihan keterampilan kerja menjadi kunci agar manfaat ekonomi dapat dirasakan secara optimal oleh penduduk setempat.
      </div>
    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Kualitas Lingkungan Hidup: Lahan, Air, dan Udara</span>
    </div>
  </section>

  <!-- ── ACT 6: DIMENSI LINGKUNGAN ── -->
  <section class="story-chapter" id="sec-iklh">
    <div class="chapter-header">
      <div class="chapter-badge green">BAB 05 &bull; LINGKUNGAN HIDUP</div>
      <h2 class="chapter-title">
        <i class="fa-solid fa-leaf" style="color:var(--iklh-lahan);margin-right:6px;"></i> Kualitas Lingkungan Hidup: <span class="hl-green">Lahan, Air, dan Udara</span>
      </h2>
      <p class="chapter-lead">
        Kondisi lingkungan hidup dinilai melalui Indeks Kualitas Lingkungan Hidup (IKLH) yang diterbitkan KLHK, mencakup tiga komponen utama: tutupan lahan, kualitas air, dan kualitas udara. Data memperlihatkan perbedaan profil antarwilayah: daerah yang padat penduduk dan aktivitas industri menghadapi tantangan lebih besar pada kualitas udara dan tutupan vegetasi, sedangkan daerah di luar Jawa dengan kepadatan lebih rendah umumnya mempertahankan tutupan lahan yang lebih baik.
      </p>
    </div>

    <!-- 3 Kartu Dimensi Lingkungan -->
    <div class="iklh-dimension-grid">
      <div class="iklh-dimension-card lahan">
        <div class="iklh-dim-icon"><i class="fa-solid fa-tree" style="color:var(--iklh-lahan);"></i></div>
        <div class="iklh-dim-title">IKLH Lahan</div>
        <p class="iklh-dim-desc">
          Mengukur tutupan vegetasi dan kawasan berhutan. Pulau Jawa memiliki tutupan vegetasi yang lebih terbatas (rerata 41,9) seiring padatnya permukiman dan lahan budidaya, sedangkan wilayah Papua mencatatkan rerata tutupan lahan tertinggi (96,9).
        </p>
        <div class="iklh-dim-stat">
          <span class="iklh-dim-score" style="color:var(--iklh-lahan);">56,3</span>
          <span class="iklh-dim-status" style="color:#4ade80;">Rata-rata Nasional</span>
        </div>
      </div>

      <div class="iklh-dimension-card air">
        <div class="iklh-dim-icon"><i class="fa-solid fa-droplet" style="color:var(--iklh-air);"></i></div>
        <div class="iklh-dim-title">IKLH Air</div>
        <p class="iklh-dim-desc">
          Mengukur baku mutu air sungai dan danau. Rata-rata nasional berada pada angka 55,9, dengan tantangan pengelolaan badan air permukaan yang lebih tinggi di daerah perkotaan dan daerah aliran sungai yang padat permukiman.
        </p>
        <div class="iklh-dim-stat">
          <span class="iklh-dim-score" style="color:var(--iklh-air);">55,9</span>
          <span class="iklh-dim-status" style="color:#38bdf8;">Rata-rata Nasional</span>
        </div>
      </div>

      <div class="iklh-dimension-card udara">
        <div class="iklh-dim-icon"><i class="fa-solid fa-wind" style="color:var(--iklh-udara);"></i></div>
        <div class="iklh-dim-title">IKLH Udara</div>
        <p class="iklh-dim-desc">
          Mengukur indeks pencemar udara ambien (ISPU). Sebagian besar kabupaten/kota di luar Jawa mencatatkan kualitas udara yang baik (skor di atas 90), sementara daerah padat transportasi dan aglomerasi industri mencatatkan skor yang relatif lebih rendah.
        </p>
        <div class="iklh-dim-stat">
          <span class="iklh-dim-score" style="color:var(--iklh-udara);">91,0</span>
          <span class="iklh-dim-status" style="color:#cbd5e1;">Rata-rata Nasional</span>
        </div>
      </div>
    </div>

    <!-- Grafik Komparasi IKLH Antarpulau -->
    <div class="panel">
      <div class="panel-head">
        <div class="panel-title">
          <div class="panel-icon icon-iklh"><i class="fa-solid fa-chart-bar" style="color:#22c55e;"></i></div>
          Rata-rata Kualitas Lingkungan (Lahan, Air, Udara) di 7 Wilayah Kepulauan
        </div>
        <span class="nat-badge" style="background:rgba(34,197,94,0.12);color:#4ade80;">Data IKLH KLHK 2024</span>
      </div>
      <div style="padding:12px 16px 6px;">
        <div id="iklh-island-chart"></div>
      </div>
      <div class="panel-foot">
        <strong>Perbandingan Wilayah:</strong> Terlihat adanya perbedaan karakteristik antara pulau dengan kepadatan tinggi (Jawa) yang memerlukan fokus pada perbaikan kualitas udara dan air, dengan pulau-pulau luar Jawa yang memiliki potensi besar dalam menjaga tutupan hutan dan vegetasi alami.
      </div>
    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Pengelompokan Karakteristik Tipe Daerah</span>
    </div>
  </section>

  <!-- ── ACT 7: PCA & CLUSTER (TOPIK A) ── -->
  <section class="story-chapter" id="sec-mv">
    <div class="chapter-header">
      <div class="chapter-badge">BAB 06 &bull; ANALISIS MULTIVARIAT (TOPIK A)</div>
      <h2 class="chapter-title">
        <i class="fa-solid fa-cubes" style="color:#818cf8;margin-right:6px;"></i> Pengelompokan Tipe Daerah: <span class="hl-blue">Hasil Analisis PCA &amp; Klaster</span>
      </h2>
      <p class="chapter-lead">
        Dengan menggunakan analisis multivariat Principal Component Analysis (PCA) terhadap 9 indikator pembangunan, data diringkas menjadi dua komponen utama yang merangkum <strong>56,5% variansi</strong>. Analisis klaster membagi 514 daerah ke dalam tiga kelompok utama berdasarkan profil sosio-ekonomi dan lingkungannya.
      </p>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div class="panel-title">
          <div class="panel-icon icon-mv"><i class="fa-solid fa-cubes" style="color:#818cf8;"></i></div>
          Visualisasi Multivariat 514 Daerah
        </div>
        <div class="seg-ctrl">
          <button class="seg-btn active" id="btn-pca" onclick="setMultiMode('pca')">Biplot PCA (2D)</button>
          <button class="seg-btn" id="btn-par" onclick="setMultiMode('par')">Parallel Coordinates</button>
          <button class="seg-btn" id="btn-hm" onclick="setMultiMode('hm')">Matriks Heatmap</button>
        </div>
      </div>
      <div style="padding:10px 14px 6px;">
        <div id="pca-view"></div>
        <div id="par-view" style="display:none;"></div>
        <div id="hm-view" style="display:none;"></div>
      </div>
      <div class="panel-foot">
        <strong>Karakteristik Tipe Daerah:</strong> Klaster 1 mencakup perkotaan padat dengan aktivitas ekonomi tinggi (72 daerah); Klaster 2 mencakup daerah agraris dan transisi (334 daerah); Klaster 3 mencakup perdesaan dengan tutupan lahan yang luas (93 daerah).
      </div>
    </div>

    <!-- Pencilan -->
    <div class="panel" style="margin-top:14px;">
      <div class="panel-head">
        <div class="panel-title">
          <div class="panel-icon" style="background:rgba(56,189,248,0.15);"><i class="fa-solid fa-crosshairs" style="color:var(--accent);"></i></div>
          13 Daerah dengan Karakteristik Unik (Jarak Mahalanobis p &lt; 0,001)
        </div>
        <span style="font-size:11px;color:var(--txt3);">Klik nama daerah untuk menyorot posisinya di seluruh visualisasi</span>
      </div>
      <div class="outlier-grid" id="outlier-container"></div>
    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Struktur Berjenjang Administrasi Wilayah</span>
    </div>
  </section>

  <!-- ── ACT 8: HIERARKI (TOPIK C) ── -->
  <section class="story-chapter" id="sec-hier">
    <div class="chapter-header">
      <div class="chapter-badge green">BAB 07 &bull; STRUKTUR BERHIERARKI (TOPIK C)</div>
      <h2 class="chapter-title">
        <i class="fa-solid fa-sitemap" style="color:#34d399;margin-right:6px;"></i> Struktur Berjenjang: <span class="hl-green">Indonesia &rarr; Pulau &rarr; Provinsi &rarr; Kab/Kota</span>
      </h2>
      <p class="chapter-lead">
        Visualisasi hierarki ini menampilkan pembagian wilayah secara berjenjang dari tingkat nasional hingga kabupaten/kota. Ukuran kotak mencerminkan jumlah penduduk, sedangkan warna menunjukkan rata-rata persentase kemiskinan. Anda dapat mengklik suatu bagian untuk memperbesar rincian tingkat provinsi maupun kabupaten/kota.
      </p>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div class="panel-title">
          <div class="panel-icon icon-hier"><i class="fa-solid fa-sitemap" style="color:#34d399;"></i></div>
          Visualisasi Wilayah Berjenjang (4 Tingkat)
        </div>
        <div class="seg-ctrl">
          <button class="seg-btn active" id="btn-tree" onclick="setHierMode('treemap')">Treemap</button>
          <button class="seg-btn" id="btn-sun" onclick="setHierMode('sunburst')">Sunburst</button>
          <button class="seg-btn" id="btn-icicle" onclick="setHierMode('icicle')">Icicle</button>
        </div>
      </div>
      <div style="padding:10px 14px 6px;">
        <div id="tm-view"></div>
      </div>
      <div class="panel-foot">
        <strong>Panduan:</strong> Klik pada sektor pulau atau provinsi untuk melihat kabupaten/kota di dalamnya. Klik kembali pada judul di bagian atas untuk kembali ke tingkat yang lebih tinggi.
      </div>
    </div>

    <div class="story-flow-divider">
      <div class="flow-line"></div>
      <div class="flow-arrow-circle"><i class="fa-solid fa-arrow-down"></i></div>
      <span class="flow-text">Catatan Penutup dan Kesimpulan</span>
    </div>
  </section>

  <!-- ── ACT 9: KESIMPULAN ── -->
  <section class="story-chapter" id="sec-conclusion">
    <div class="chapter-header">
      <div class="chapter-badge amber">BAB 08 &bull; CATATAN PENUTUP</div>
      <h2 class="chapter-title">
        <i class="fa-solid fa-flag-checkered" style="color:#fbbf24;margin-right:6px;"></i> Pembangunan Berkelanjutan: <span class="hl-blue">Keseimbangan Ekonomi, Sosial, dan Lingkungan</span>
      </h2>
      <p class="chapter-lead">
        Berdasarkan penelusuran terhadap 514 kabupaten dan kota di Indonesia, keberhasilan pembangunan memerlukan perhatian terpadu pada berbagai aspek:
      </p>
    </div>

    <div class="conclusion-grid">
      <div class="conclusion-card">
        <div class="conclusion-card-num">1</div>
        <h3 class="conclusion-card-title">Pemerataan Layanan Pendidikan &amp; Kesehatan</h3>
        <p class="conclusion-card-desc">
          Korelasi kuat antara IPM dan penurunan angka kemiskinan (r = -0,70) menunjukkan bahwa peningkatan mutu sekolah dan fasilitas kesehatan di daerah dengan IPM yang masih rendah merupakan langkah dasar yang sangat krusial bagi kesejahteraan warga.
        </p>
      </div>

      <div class="conclusion-card">
        <div class="conclusion-card-num">2</div>
        <h3 class="conclusion-card-title">Penguatan Sektor Ekonomi Lokal</h3>
        <p class="conclusion-card-desc">
          Di daerah yang memiliki PDRB tinggi dari sektor industri pengolahan sumber daya alam, pengembangan sektor pendukung dan pelatihan keterampilan kerja lokal dapat membantu agar dampak positif kegiatan ekonomi dapat dirasakan lebih luas oleh masyarakat sekitar.
        </p>
      </div>

      <div class="conclusion-card">
        <div class="conclusion-card-num">3</div>
        <h3 class="conclusion-card-title">Perlindungan Kualitas Lingkungan</h3>
        <p class="conclusion-card-desc">
          Kawasan perkotaan dan pusat industri memerlukan perhatian khusus pada pengendalian pencemaran udara dan air. Di sisi lain, daerah dengan tutupan hutan dan vegetasi yang masih luas perlu terus didukung dalam menjaga fungsi ekologisnya.
        </p>
      </div>
    </div>

    <div class="story-callout" style="border-left-color:var(--accent);background:rgba(56,189,248,0.06);">
      <strong>Ringkasan:</strong> Pembangunan berkelanjutan berfokus pada peningkatan taraf hidup masyarakat di seluruh wilayah Indonesia secara seimbang, dengan tetap memperhatikan daya dukung lingkungan hidup demi generasi mendatang.
    </div>

    <footer>
      <strong>Visualisasi Data Capaian Pembangunan &amp; Kualitas Lingkungan Daerah Indonesia 2024</strong><br>
      Ujian Akhir Semester Visualisasi Data &bull; Program Studi Komputasi Statistik &bull; Politeknik Statistika STIS 2026<br>
      <span style="color:var(--txt3);">Sumber Data Utama: BPS 2024 &bull; Indeks Kualitas Lingkungan: KLHK 2024 &bull; Batas Wilayah: Alf-Anas (Juni 2023) &bull; Dibuat dengan Leaflet.js &amp; Plotly.js</span>
    </footer>
  </section>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
// ── DATA INJEKSI ──
const GEO = __GEO__;
const EDGES = __E__;
const P = __P__;
const A = __A__;
const VP = __VP__;
const T = __T__;
const NODE = __NODE__;
const H = __H__;
const PAR = __PAR__;
const OUTLIERS = __OUTLIERS__;
const ISLAND_STATS = __ISLAND_STATS__;
const NAT_STATS = __NAT_STATS__;
const SCATTER_IPM = __SCATTER_IPM__;
const SCATTER_PDRB = __SCATTER_PDRB__;
const IKLH_ISLANDS = __IKLH_ISLANDS__;

// ── KONSTANTA & STATE ──
const V = {
  kemiskinan: { t: "Persentase Kemiskinan (%)", pal: ["#ffffb2","#fecc5c","#fd8d3c","#f03b20","#bd0026"] },
  ipm: { t: "Indeks Pembangunan Manusia", pal: ["#ffffcc","#a1dab4","#41b6c4","#2c7fb8","#253494"] },
  usia_produktif: { t: "Usia Produktif (% penduduk)", pal: ["#f2f0f7","#cbc9e2","#9e9ac8","#756bb1","#54278f"] },
  kepadatan: { t: "Kepadatan (jiwa/km²)", pal: ["#ffffd4","#fed98e","#fe9929","#d95f0e","#993404"] },
  iklh_lahan: { t: "IKLH Lahan (Tutupan)", pal: ["#f7fcf5","#c7e9c0","#74c476","#31a354","#006d2c"] },
  iklh_air: { t: "IKLH Air (Kualitas)", pal: ["#eff3ff","#bdd7e7","#6baed6","#3182bd","#08519c"] },
  iklh_udara: { t: "IKLH Udara (ISPU)", pal: ["#f7f7f7","#d9d9d9","#bdbdbd","#969696","#525252"] },
  cluster: {
    t: "Klaster Pembangunan",
    cat: { 1: "#fde047", 2: "#f59e0b", 3: "#b45309" },
    lab: { 1: "K1: Perkotaan Padat", 2: "K2: Menengah & Transisi", 3: "K3: Perdesaan" }
  }
};

const NA = "#334155";
const sel = new Set();
let curVar = "kemiskinan";
let curIsland = "Semua";
let mapMode = "choro";
let multiMode = "pca";
let hierMode = "treemap";
let parRendered = false, hmRendered = false;

const CL = {
  1: ["K1: Perkotaan Padat", "#fde047"],
  2: ["K2: Menengah & Transisi", "#f59e0b"],
  3: ["K3: Perdesaan", "#b45309"]
};

const fmt = v => v == null ? "—" : Number(v).toLocaleString("id-ID", { maximumFractionDigits: 2 });
const fmtK = v => v == null ? "—" : v >= 1000000 ? (v/1000000).toFixed(1)+"Jt" : v >= 1000 ? (v/1000).toFixed(0)+"Rb" : String(v);

function col(k, v) {
  if (v == null) return NA;
  const o = V[k];
  if (o.cat) return o.cat[v] || NA;
  const e = EDGES[k];
  let i = 0;
  while (i < 4 && v > e[i + 1]) i++;
  return o.pal[i];
}

// Tooltip Leaflet rapi tanpa outline putih
function mapTip(p) {
  return `<div style="font-family:'Inter',sans-serif;font-size:12px;line-height:1.5;background:#0d1428;color:#f1f5f9;padding:10px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);min-width:190px;box-shadow:0 8px 24px rgba(0,0,0,0.5);">
    <strong style="font-size:13px;color:#fff;">${p.kabkota}</strong><br>
    <span style="color:#94a3b8;font-size:11px;">Provinsi ${p.provinsi} &bull; ${p.pulau}</span>
    <div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;gap:2px;">
      <div><span style="color:#64748b;">${V[curVar].t}:</span> <strong>${curVar==="cluster"&&p.cluster?V.cluster.lab[p.cluster]:fmt(p[curVar])}</strong></div>
      <div><span style="color:#64748b;">Penduduk:</span> <strong>${fmt(p.penduduk)} jiwa</strong></div>
      <div><span style="color:#64748b;">PDRB/kapita:</span> <strong>Rp${fmt(p.pdrb_juta)} Jt</strong></div>
      <div><span style="color:#64748b;">Klaster:</span> <strong style="color:${p.cluster?CL[p.cluster][1]:'#94a3b8'};">${p.cluster?CL[p.cluster][0]:"—"}</strong></div>
      ${OUTLIERS[p.kode] ? `<div style="margin-top:4px;color:#38bdf8;font-weight:600;">Karakteristik Pencilan</div>` : ""}
    </div>
  </div>`;
}

// Styling polygon: tidak ada stroke putih
const sty = f => {
  const p = f.properties;
  const matchesIsland = curIsland === "Semua" || p.pulau === curIsland;
  const on = !sel.size ? matchesIsland : sel.has(p.kode);
  return {
    fillColor: col(curVar, p[curVar]),
    weight: on ? 0.7 : 0.2,
    color: on ? "rgba(56,189,248,0.4)" : "rgba(255,255,255,0.06)",
    fillOpacity: on ? 0.88 : (matchesIsland ? 0.35 : 0.1)
  };
};

// ── INISIALISASI LEAFLET MAP ──
const map = L.map("map-container", { zoomSnap: 0.5 }).setView([-2.5, 118], 4.5);

L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
  attribution: "Tiles &copy; Esri &bull; Data: BPS & KLHK 2024",
  maxZoom: 16
}).addTo(map);

map.createPane("sym").style.zIndex = 450;

const poly = L.geoJSON(GEO, {
  style: sty,
  onEachFeature: (f, l) => {
    l.bindTooltip(() => mapTip(f.properties), { sticky: true, opacity: 1, className: "custom-map-tooltip" });
    l.on({
      mouseover: e => {
        if (!sel.size || sel.has(f.properties.kode)) {
          e.target.setStyle({ weight: 2, color: "#38bdf8" });
        }
      },
      mouseout: e => poly.resetStyle(e.target),
      click: () => {
        toggleSelectKabkota(f.properties.kode);
      }
    });
  }
}).addTo(map);

const maxP = Math.max(...GEO.features.map(f => f.properties.penduduk));
const symMarkers = GEO.features.map(f => {
  const p = f.properties;
  return L.circleMarker([p.lat, p.lon], {
    pane: "sym",
    radius: 2 + 20 * Math.sqrt(p.penduduk / maxP),
    color: "#090e1c",
    weight: 0.8,
    fillColor: p.cluster ? CL[p.cluster][1] : "#64748b",
    fillOpacity: 0.7
  }).bindTooltip(() => mapTip(p), { sticky: true, opacity: 1, className: "custom-map-tooltip" }).on("click", () => {
    toggleSelectKabkota(p.kode);
  });
});
const sym = L.layerGroup(symMarkers);

// Hubungkan Selector Indikator di Luar Map Canvas (DI ATAS PETA)
document.getElementById("map-var-select").onchange = e => {
  curVar = e.target.value;
  poly.setStyle(sty);
  updateLegend();
};

// Legenda di pojok kanan bawah peta
const legCtrl = L.control({ position: "bottomright" });
legCtrl.onAdd = () => {
  const d = L.DomUtil.create("div", "map-ctrl-box");
  d.style.maxWidth = "190px";
  return d;
};
legCtrl.addTo(map);

function updateLegend() {
  const o = V[curVar];
  let h = `<strong style="color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:.05em;">${o.t}</strong><br>`;
  if (o.cat) {
    h += Object.keys(o.cat).map(k => `<div style="margin-top:4px;"><span class="sw" style="background:${o.cat[k]};border-radius:50%;"></span>${o.lab[k]}</div>`).join("");
  } else {
    const e = EDGES[curVar];
    h += o.pal.map((c, i) => `<div style="margin-top:3px;"><span class="sw" style="background:${c};"></span>${fmt(e[i])} – ${fmt(e[i+1])}</div>`).join("");
  }
  h += `<div style="margin-top:4px;"><span class="sw" style="background:#334155;"></span><span style="color:#64748b;">tidak tersedia</span></div>`;
  if (!o.cat) h += `<div style="margin-top:6px;font-size:9px;color:#64748b;">5 Kuantil Berimbang</div>`;
  legCtrl.getContainer().innerHTML = h;
}
updateLegend();

function setMapMode(mode) {
  mapMode = mode;
  document.getElementById("btn-map-choro").classList.toggle("active", mode === "choro");
  document.getElementById("btn-map-sym").classList.toggle("active", mode === "sym");
  if (mode === "choro") {
    if (!map.hasLayer(poly)) map.addLayer(poly);
    if (map.hasLayer(sym)) map.removeLayer(sym);
  } else {
    if (map.hasLayer(poly)) map.removeLayer(poly);
    if (!map.hasLayer(sym)) map.addLayer(sym);
  }
}

// ── ISLAND SELECTOR & DEFAULT PANEL ──
function renderIslandCards() {
  const cont = document.getElementById("island-quick-cards");
  cont.innerHTML = "";
  Object.keys(ISLAND_STATS).forEach(pu => {
    const st = ISLAND_STATS[pu];
    const card = document.createElement("div");
    card.className = "island-mini-card" + (curIsland === pu ? " active" : "");
    card.innerHTML = `
      <div class="island-card-title">${pu}</div>
      <div class="island-card-pop">${fmtK(st.penduduk)} jiwa &bull; ${st.n} daerah</div>
      <div class="island-card-stat">IPM: ${st.ipm}</div>
    `;
    card.onclick = () => {
      setIslandFilter(pu);
      scrollToAct("sec-geo");
    };
    cont.appendChild(card);
  });
}
renderIslandCards();

function setIslandFilter(pu) {
  curIsland = pu;
  sel.clear();

  document.querySelectorAll(".island-btn").forEach(b => {
    b.classList.toggle("active", b.textContent.includes(pu) || (pu==="Semua" && b.textContent.includes("Seluruh")));
  });
  renderIslandCards();

  const b = (pu === "Semua") ? NAT_STATS.bounds : ISLAND_STATS[pu].bounds;
  map.flyToBounds(b, { padding: [20, 20], duration: 1.2 });

  poly.setStyle(sty);
  showDefaultSummary(pu);
  refresh("island");
}

function showDefaultSummary(pulauName) {
  const isNat = (!pulauName || pulauName === "Semua");
  const data = isNat ? NAT_STATS : ISLAND_STATS[pulauName];
  const title = isNat ? `<i class="fa-solid fa-landmark" style="color:var(--accent);margin-right:8px;"></i> Ringkasan Nasional` : `<i class="fa-solid fa-map-pin" style="color:#4ade80;margin-right:8px;"></i> Wilayah: ${pulauName}`;
  const sub = isNat
    ? "514 Kabupaten/Kota &bull; 38 Provinsi &bull; 7 Wilayah Kepulauan"
    : `${data.n} Kabupaten/Kota &bull; Rata-rata &amp; Akumulasi Wilayah`;

  document.getElementById("detail-panel-title").textContent = isNat ? "Profil Nasional" : `Wilayah: ${pulauName}`;
  document.getElementById("detail-panel-badge").textContent = isNat ? "Ringkasan Nasional" : "Wilayah Terpilih";
  document.getElementById("detail-panel-badge").style.background = isNat ? "rgba(56,189,248,0.12)" : "rgba(34,197,94,0.12)";
  document.getElementById("detail-panel-badge").style.color = isNat ? "var(--accent)" : "#4ade80";

  const wrapper = document.getElementById("detail-content-wrapper");
  wrapper.innerHTML = `
    <div class="detail-box-inner">
      <div class="nat-header">
        <div class="nat-title">${title}</div>
        <div class="nat-sub">${sub}</div>
        <span class="nat-badge">${isNat ? "Data Agregat Nasional" : "Data Agregat Wilayah Terpilih"}</span>
      </div>

      <div class="kpi-grid-6">
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Rerata Kemiskinan</div>
          <div class="kpi-val" style="color:${data.kemiskinan>15?'#f87171':data.kemiskinan>10?'#fbbf24':'#34d399'};">${fmt(data.kemiskinan)}<span class="kpi-unit">%</span></div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Rerata IPM</div>
          <div class="kpi-val" style="color:#38bdf8;">${fmt(data.ipm)}</div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">PDRB / kapita</div>
          <div class="kpi-val">Rp${fmt(data.pdrb_juta)}<span class="kpi-unit">Jt</span></div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Total Penduduk</div>
          <div class="kpi-val" style="font-size:14px;">${fmtK(data.penduduk)}</div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Usia Produktif</div>
          <div class="kpi-val">${fmt(data.usia_prod)}<span class="kpi-unit">%</span></div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Kepadatan</div>
          <div class="kpi-val">${fmt(data.kepadatan)}<span class="kpi-unit">jw/km²</span></div>
        </div>
      </div>

      <div>
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--txt3);letter-spacing:.05em;margin-bottom:6px;">
          Rerata Kualitas Lingkungan Hidup (IKLH)
        </div>
        <div class="iklh-panel-row">
          <div class="iklh-card-custom lahan">
            <div style="font-size:14px;"><i class="fa-solid fa-tree" style="color:var(--iklh-lahan);"></i></div>
            <div class="iklh-c-val" style="color:var(--iklh-lahan);">${fmt(data.iklh_lahan)}</div>
            <div class="iklh-c-lbl" style="color:#4ade80;">Lahan</div>
          </div>
          <div class="iklh-card-custom air">
            <div style="font-size:14px;"><i class="fa-solid fa-droplet" style="color:var(--iklh-air);"></i></div>
            <div class="iklh-c-val" style="color:var(--iklh-air);">${fmt(data.iklh_air)}</div>
            <div class="iklh-c-lbl" style="color:#38bdf8;">Air</div>
          </div>
          <div class="iklh-card-custom udara">
            <div style="font-size:14px;"><i class="fa-solid fa-wind" style="color:var(--iklh-udara);"></i></div>
            <div class="iklh-c-val" style="color:var(--iklh-udara);">${fmt(data.iklh_udara)}</div>
            <div class="iklh-c-lbl" style="color:#cbd5e1;">Udara</div>
          </div>
        </div>
      </div>

      <div>
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--txt3);letter-spacing:.05em;margin-bottom:6px;">
          Komposisi Klaster Daerah
        </div>
        <div class="cluster-pills-row">
          <div class="cl-chip k1">K1 Perkotaan: ${data.k1}</div>
          <div class="cl-chip k2">K2 Menengah: ${data.k2}</div>
          <div class="cl-chip k3">K3 Perdesaan: ${data.k3}</div>
        </div>
      </div>

      ${isNat ? `
      <div>
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--txt3);letter-spacing:.05em;margin-bottom:6px;">
          Perbandingan Rata-rata IPM Antarpulau
        </div>
        <div class="island-comparison-bars">
          ${Object.keys(ISLAND_STATS).map(pu => {
            const st = ISLAND_STATS[pu];
            const pct = Math.min(100, Math.max(0, (st.ipm - 60) * 3.3));
            return `
              <div class="comp-bar-row">
                <div class="comp-bar-name">${pu}</div>
                <div class="comp-bar-track">
                  <div class="comp-bar-fill" style="width:${pct}%;background:${st.ipm>=74?'#38bdf8':st.ipm>=70?'#818cf8':'#f59e0b'};"></div>
                </div>
                <div class="comp-bar-val">${st.ipm}</div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
      ` : `
        <button class="btn-back-nat" onclick="setIslandFilter('Semua')">
          <i class="fa-solid fa-arrow-left"></i> Tampilkan Ringkasan Nasional
        </button>
      `}
    </div>
  `;
}
showDefaultSummary("Semua");

// ── DETAIL PANEL UNTUK KAB/KOTA SPESIFIK ──
function showDetail(kode) {
  const f = GEO.features.find(f => f.properties.kode === kode);
  if (!f) return;
  const pr = f.properties;
  const out = OUTLIERS[kode];
  const clCol = pr.cluster ? CL[pr.cluster][1] : "#64748b";
  const clNm = pr.cluster ? CL[pr.cluster][0] : "Data Tidak Lengkap";

  document.getElementById("detail-panel-title").textContent = pr.kabkota;
  document.getElementById("detail-panel-badge").textContent = pr.pulau;
  document.getElementById("detail-panel-badge").style.background = "rgba(56,189,248,0.12)";
  document.getElementById("detail-panel-badge").style.color = "var(--accent)";

  const wrapper = document.getElementById("detail-content-wrapper");
  wrapper.innerHTML = `
    <div class="detail-box-inner">
      <div class="nat-header">
        <div class="nat-title">${pr.kabkota}</div>
        <div class="nat-sub">Provinsi ${pr.provinsi} &bull; Kode BPS: ${pr.kode} &bull; ${pr.pulau}</div>
        <div style="margin-top:6px;">
          <span class="nat-badge" style="background:${clCol}22;color:${clCol};border-color:${clCol}44;">
            ${clNm}
          </span>
        </div>
      </div>

      ${out ? `
      <div style="background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.25);border-radius:8px;padding:9px 12px;font-size:11.5px;color:#bae6fd;">
        <strong>Karakteristik Kombinasi Unik:</strong><br>
        Jarak Mahalanobis: <strong>${out.d2}</strong> &bull; Variabel Paling Berbeda: <strong>${out.var_ekstrem}</strong>
      </div>` : ""}

      <div class="kpi-grid-6">
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Kemiskinan</div>
          <div class="kpi-val" style="color:${pr.kemiskinan>20?'#f87171':pr.kemiskinan>10?'#fbbf24':'#34d399'};">${fmt(pr.kemiskinan)}<span class="kpi-unit">%</span></div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">IPM 2024</div>
          <div class="kpi-val" style="color:${pr.ipm>=75?'#34d399':pr.ipm>=65?'#38bdf8':'#94a3b8'};">${fmt(pr.ipm)}</div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">PDRB/kapita</div>
          <div class="kpi-val">Rp${fmt(pr.pdrb_juta)}<span class="kpi-unit">Jt</span></div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Total Populasi</div>
          <div class="kpi-val" style="font-size:13px;">${fmt(pr.penduduk)}</div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Usia Produktif</div>
          <div class="kpi-val">${fmt(pr.usia_produktif)}<span class="kpi-unit">%</span></div>
        </div>
        <div class="kpi-card-mini">
          <div class="kpi-lbl">Kepadatan</div>
          <div class="kpi-val">${fmt(pr.kepadatan)}<span class="kpi-unit">jw/km²</span></div>
        </div>
      </div>

      <div>
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--txt3);letter-spacing:.05em;margin-bottom:6px;">
          Kualitas Lingkungan Hidup Daerah (IKLH)
        </div>
        <div class="iklh-panel-row">
          <div class="iklh-card-custom lahan">
            <div style="font-size:14px;"><i class="fa-solid fa-tree" style="color:var(--iklh-lahan);"></i></div>
            <div class="iklh-c-val" style="color:var(--iklh-lahan);">${fmt(pr.iklh_lahan)}</div>
            <div class="iklh-c-lbl" style="color:#4ade80;">Lahan</div>
          </div>
          <div class="iklh-card-custom air">
            <div style="font-size:14px;"><i class="fa-solid fa-droplet" style="color:var(--iklh-air);"></i></div>
            <div class="iklh-c-val" style="color:var(--iklh-air);">${fmt(pr.iklh_air)}</div>
            <div class="iklh-c-lbl" style="color:#38bdf8;">Air</div>
          </div>
          <div class="iklh-card-custom udara">
            <div style="font-size:14px;"><i class="fa-solid fa-wind" style="color:var(--iklh-udara);"></i></div>
            <div class="iklh-c-val" style="color:var(--iklh-udara);">${fmt(pr.iklh_udara)}</div>
            <div class="iklh-c-lbl" style="color:#cbd5e1;">Udara</div>
          </div>
        </div>
      </div>

      <button class="btn-back-nat" onclick="deselectToSummary()">
        <i class="fa-solid fa-arrow-left"></i> Kembali ke Ringkasan ${pr.pulau}
      </button>
    </div>
  `;
}


// ── TOGGLE SELEKSI WILAYAH: KLIK 1 = PILIH, KLIK 2 = UNSELECT ──
function toggleSelectKabkota(kode) {
  if (sel.has(kode)) {
    // Sedang terpilih -> batalkan pilihan (unselect)
    sel.clear();
    refresh("map");
    showDefaultSummary(curIsland);
  } else {
    // Belum terpilih -> pilih wilayah ini
    sel.clear();
    sel.add(kode);
    refresh("map");
    showDetail(kode);
  }
}

function deselectToSummary() {
  sel.clear();
  refresh("deselect");
  showDefaultSummary(curIsland);
}

function focusKabkota(kode) {
  if (sel.has(kode)) {
    // Toggle off jika diklik lagi
    sel.clear();
    refresh("focus");
    showDefaultSummary(curIsland);
    return;
  }
  sel.clear();
  sel.add(kode);
  refresh("focus");
  showDetail(kode);
  const f = GEO.features.find(x => x.properties.kode === kode);
  if (f) {
    map.setView([f.properties.lat, f.properties.lon], 7.5);
    scrollToAct("sec-geo");
  }
}

// ── ACT 4: SCATTER IPM vs KEMISKINAN ──
function renderScatterIpmPov() {
  const traces = [1, 2, 3].map(c => {
    const pts = SCATTER_IPM.filter(x => x.c === c);
    return {
      type: "scatter",
      mode: "markers",
      name: CL[c][0],
      x: pts.map(x => x.ipm),
      y: pts.map(x => x.pov),
      customdata: pts.map(x => x.k),
      text: pts.map(x => `<b>${x.n}</b> (${x.prv})<br>IPM: ${x.ipm} &bull; Kemiskinan: ${x.pov}%<br>Penduduk: ${fmt(x.pend)} jiwa`),
      marker: {
        color: CL[c][1],
        size: pts.map(x => x.o ? 10 : 6.5),
        symbol: pts.map(x => x.o ? "diamond" : "circle"),
        opacity: 0.8,
        line: { width: pts.map(x => x.o ? 1.5 : 0.5), color: pts.map(x => x.o ? "#fff" : "rgba(0,0,0,0.3)") }
      },
      hovertemplate: "%{text}<extra></extra>"
    };
  });

  const ipmX = [];
  const povY = [];
  for (let x = 40; x <= 88; x += 1) {
    ipmX.push(x);
    const y = Math.max(1, 0.0203 * x * x - 3.666 * x + 169);
    povY.push(y);
  }
  traces.push({
    type: "scatter",
    mode: "lines",
    name: "Garis Tren (r = -0,70)",
    x: ipmX,
    y: povY,
    line: { color: "rgba(255,255,255,0.45)", width: 2, dash: "dash" },
    hoverinfo: "none"
  });

  Plotly.newPlot("scatter-ipm-pov", traces, {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8" },
    dragmode: "lasso",
    margin: { t: 20, l: 45, r: 20, b: 45 },
    legend: { orientation: "h", y: -0.22, x: 0.02, font: { size: 10.5 }, bgcolor: "rgba(0,0,0,0)" },
    xaxis: { title: "Indeks Pembangunan Manusia (IPM)", gridcolor: "rgba(255,255,255,0.05)", zeroline: false },
    yaxis: { title: "Persentase Kemiskinan (%)", gridcolor: "rgba(255,255,255,0.05)", zeroline: false }
  }, { responsive: true });

  const el = document.getElementById("scatter-ipm-pov");
  el.on("plotly_click", ev => {
    if (ev?.points?.[0]?.customdata) focusKabkota(ev.points[0].customdata);
  });
  el.on("plotly_selected", ev => {
    if (!ev || !ev.points || ev.points.length === 0) return;
    sel.clear();
    ev.points.forEach(p => { if (p.customdata) sel.add(p.customdata); });
    refresh("scatter-ipm");
    if (ev.points.length === 1) showDetail(ev.points[0].customdata);
  });
}
renderScatterIpmPov();

// ── ACT 5: SCATTER PDRB vs IPM ──
function renderScatterPdrbIpm() {
  const traces = [1, 2, 3].map(c => {
    const pts = SCATTER_PDRB.filter(x => x.c === c);
    return {
      type: "scatter",
      mode: "markers",
      name: CL[c][0],
      x: pts.map(x => x.pdrb),
      y: pts.map(x => x.ipm),
      customdata: pts.map(x => x.k),
      text: pts.map(x => `<b>${x.n}</b> (${x.prv})<br>PDRB/kapita: Rp${fmt(x.pdrb)} Jt<br>IPM: ${x.ipm} &bull; Kemiskinan: ${x.pov}%${x.anom ? '<br>&bull; '+x.anom : ''}`),
      marker: {
        color: CL[c][1],
        size: pts.map(x => x.anom ? 11 : 6.5),
        symbol: pts.map(x => x.anom ? "diamond" : "circle"),
        opacity: 0.8,
        line: { width: pts.map(x => x.anom ? 2 : 0.5), color: pts.map(x => x.anom ? "#fff" : "rgba(0,0,0,0.3)") }
      },
      hovertemplate: "%{text}<extra></extra>"
    };
  });

  const anomAnnotations = [
    { x: 570.1, y: 73.54, text: "Morowali (Industri Logam)", ax: -40, ay: -30 },
    { x: 384.7, y: 69.79, text: "Teluk Bintuni (Migas/LNG)", ax: -50, ay: 30 },
    { x: 277.0, y: 76.85, text: "Mimika (Pertambangan)", ax: -40, ay: -25 },
    { x: 95.1,  y: 88.61, text: "Kota Yogyakarta (Pendidikan/Jasa)", ax: 50, ay: -20 },
    { x: 86.4,  y: 85.16, text: "Kota Denpasar (Pariwisata/Jasa)", ax: 50, ay: 20 }
  ].map(a => ({
    x: a.x, y: a.y, ax: a.ax, ay: a.ay,
    xref: "x", yref: "y", text: a.text,
    showarrow: true, arrowhead: 2, arrowcolor: "#38bdf8",
    font: { size: 10, color: "#fff" },
    bgcolor: "rgba(14,22,44,0.85)", borderpad: 3
  }));

  Plotly.newPlot("scatter-pdrb-ipm", traces, {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8" },
    dragmode: "lasso",
    margin: { t: 20, l: 45, r: 20, b: 45 },
    legend: { orientation: "h", y: -0.22, x: 0.02, font: { size: 10.5 }, bgcolor: "rgba(0,0,0,0)" },
    xaxis: { title: "PDRB per kapita ADHK (Juta Rp, Skala Logaritmik)", type: "log", gridcolor: "rgba(255,255,255,0.05)" },
    yaxis: { title: "Indeks Pembangunan Manusia (IPM)", gridcolor: "rgba(255,255,255,0.05)", zeroline: false },
    annotations: anomAnnotations
  }, { responsive: true });

  const el2 = document.getElementById("scatter-pdrb-ipm");
  el2.on("plotly_click", ev => {
    if (ev?.points?.[0]?.customdata) focusKabkota(ev.points[0].customdata);
  });
}
renderScatterPdrbIpm();

// ── ACT 6: IKLH ISLAND COMPARISON CHART ──
function renderIklhIslandChart() {
  const islands = Object.keys(IKLH_ISLANDS);
  const lahan = islands.map(pu => IKLH_ISLANDS[pu].lahan);
  const air = islands.map(pu => IKLH_ISLANDS[pu].air);
  const udara = islands.map(pu => IKLH_ISLANDS[pu].udara);

  const traces = [
    {
      x: lahan, y: islands, type: "bar", orientation: "h",
      name: "IKLH Lahan (Tutupan)", marker: { color: "#22c55e" }
    },
    {
      x: air, y: islands, type: "bar", orientation: "h",
      name: "IKLH Air (Kualitas)", marker: { color: "#38bdf8" }
    },
    {
      x: udara, y: islands, type: "bar", orientation: "h",
      name: "IKLH Udara (ISPU)", marker: { color: "#94a3b8" }
    }
  ];

  Plotly.newPlot("iklh-island-chart", traces, {
    barmode: "group",
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8" },
    margin: { t: 20, l: 110, r: 20, b: 40 },
    legend: { orientation: "h", y: -0.18, x: 0.05, font: { size: 11 } },
    xaxis: { title: "Skor Rata-rata IKLH", gridcolor: "rgba(255,255,255,0.05)", range: [0, 105] },
    yaxis: { gridcolor: "rgba(255,255,255,0.05)", autorange: "reversed" }
  }, { responsive: true });
}
renderIklhIslandChart();

// ── ACT 7: PCA BIPLOT, PARALLEL COORDINATES, HEATMAP ──
const pcaTraces = [1, 2, 3].map(c => {
  const pts = P.filter(x => x.c === c);
  return {
    type: "scatter",
    mode: "markers",
    name: CL[c][0],
    x: pts.map(x => x.x),
    y: pts.map(x => x.y),
    customdata: pts.map(x => x.k),
    text: pts.map(x => `<b>${x.n}</b> (${x.prv})<br>PDRB: Rp${fmt(x.pdrb)} jt &bull; IPM: ${fmt(x.ipm)}<br>Kemiskinan: ${fmt(x.miskin)}%${x.o ? '<br>&bull; Pencilan Multivariat' : ''}`),
    marker: {
      color: CL[c][1],
      size: pts.map(x => x.o ? 11 : 6.5),
      symbol: pts.map(x => x.o ? "diamond" : "circle"),
      opacity: 0.85,
      line: { width: pts.map(x => x.o ? 1.5 : 0.5), color: pts.map(x => x.o ? "#fff" : "rgba(0,0,0,0.3)") }
    },
    hovertemplate: "%{text}<br>PC1: %{x:.2f} | PC2: %{y:.2f}<extra></extra>",
    unselected: { marker: { opacity: 0.1 } }
  };
});

Plotly.newPlot("pca-view", pcaTraces, {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, sans-serif", color: "#94a3b8" },
  dragmode: "lasso",
  margin: { t: 15, l: 45, r: 15, b: 45 },
  legend: { orientation: "h", y: -0.20, x: 0.02, font: { size: 11 }, bgcolor: "rgba(0,0,0,0)" },
  xaxis: {
    title: `PC1 (${VP[0]}% varians - Urbanisasi & Sosio-Ekonomi)`,
    zeroline: true, zerolinecolor: "rgba(255,255,255,0.1)",
    gridcolor: "rgba(255,255,255,0.05)"
  },
  yaxis: {
    title: `PC2 (${VP[1]}% varians - Demografi & Tutupan Alam)`,
    zeroline: true, zerolinecolor: "rgba(255,255,255,0.1)",
    gridcolor: "rgba(255,255,255,0.05)"
  },
  annotations: A.map(a => ({
    x: a.x, y: a.y, ax: 0, ay: 0, axref: "x", ayref: "y", xref: "x", yref: "y",
    showarrow: true, arrowhead: 2, arrowcolor: "rgba(148,163,184,0.7)", arrowwidth: 1.5,
    text: a.t, font: { size: 10, color: "#cbd5e1" },
    bgcolor: "rgba(14,22,44,0.75)", borderpad: 3
  }))
}, { responsive: true });

const pcaEl = document.getElementById("pca-view");
pcaEl.on("plotly_selected", ev => {
  if (!ev || !ev.points || ev.points.length === 0) return;
  sel.clear();
  ev.points.forEach(p => sel.add(p.customdata));
  refresh("pca");
  if (ev.points.length === 1) showDetail(ev.points[0].customdata);
});
pcaEl.on("plotly_deselect", () => { sel.clear(); refresh("pca"); });
pcaEl.on("plotly_click", ev => {
  if (ev?.points?.[0]?.customdata) focusKabkota(ev.points[0].customdata);
});

function renderParallelCoords() {
  if (parRendered) return;
  parRendered = true;
  Plotly.newPlot("par-view", [{
    type: "parcoords",
    line: {
      color: PAR.map(p => p.c),
      colorscale: [[0,"#fde047"],[0.5,"#f59e0b"],[1,"#b45309"]],
      cmin: 1, cmax: 3,
      colorbar: { title: "Klaster", tickvals:[1,2,3], ticktext:["K1","K2","K3"], len:0.65 }
    },
    dimensions: [
      { label: "Kepadatan", values: PAR.map(p => p.kepadatan), range: [0, 4500] },
      { label: "PDRB (Jt)", values: PAR.map(p => p.pdrb_juta), range: [0, 250] },
      { label: "IPM", values: PAR.map(p => p.ipm), range: [45, 90] },
      { label: "TPT (%)", values: PAR.map(p => p.tpt), range: [0, 15] },
      { label: "Usia Prod", values: PAR.map(p => p.usia_produktif), range: [45, 78] },
      { label: "Miskin (%)", values: PAR.map(p => p.kemiskinan), range: [0, 45] },
      { label: "IKLH Lahan", values: PAR.map(p => p.iklh_lahan), range: [20, 95] },
      { label: "IKLH Udara", values: PAR.map(p => p.iklh_udara), range: [65, 100] },
      { label: "IKLH Air", values: PAR.map(p => p.iklh_air), range: [25, 90] }
    ],
    labelangle: -25, labelside: "bottom"
  }], {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8", size: 10.5 },
    margin: { t: 40, l: 35, r: 40, b: 60 }
  }, { responsive: true });
}

function renderHeatmap() {
  if (hmRendered) return;
  hmRendered = true;
  Plotly.newPlot("hm-view", [{
    type: "heatmap",
    z: H.z, x: H.x, y: H.y,
    colorscale: [[0,"#ef4444"],[0.5,"#334155"],[1,"#38bdf8"]],
    zmid: 0,
    texttemplate: "%{z:.2f}",
    textfont: { color: "#f1f5f9", size: 12, family: "JetBrains Mono" }
  }], {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8" },
    margin: { t: 10, l: 80, r: 20, b: 90 },
    xaxis: { tickangle: -35, color: "#64748b" },
    yaxis: { color: "#64748b" }
  }, { responsive: true });
}

function setMultiMode(mode) {
  multiMode = mode;
  document.getElementById("btn-pca").classList.toggle("active", mode === "pca");
  document.getElementById("btn-par").classList.toggle("active", mode === "par");
  document.getElementById("btn-hm").classList.toggle("active", mode === "hm");
  document.getElementById("pca-view").style.display = (mode === "pca") ? "block" : "none";
  document.getElementById("par-view").style.display = (mode === "par") ? "block" : "none";
  document.getElementById("hm-view").style.display = (mode === "hm") ? "block" : "none";
  if (mode === "par") renderParallelCoords();
  if (mode === "hm") renderHeatmap();
  if (mode === "pca") Plotly.Plots.resize("pca-view");
}

// ── OUTLIER CHIPS ──
const outContainer = document.getElementById("outlier-container");
Object.keys(OUTLIERS).forEach(code => {
  const o = OUTLIERS[code];
  const chip = document.createElement("div");
  chip.className = "outlier-chip";
  chip.innerHTML = `${o.kabkota} <span class="d2-badge">d²=${o.d2}</span> <span style="font-size:9.5px;color:rgba(186,230,253,0.7);">${o.var_ekstrem}</span>`;
  chip.onclick = () => focusKabkota(code);
  outContainer.appendChild(chip);
});

// ── ACT 8: HIERARCHY ──
function renderHierarchyChart(type) {
  const trace = {
    type,
    ids: T.ids, labels: T.labels, parents: T.parents, values: T.values,
    branchvalues: "total",
    marker: {
      colors: T.colors,
      colorscale: [[0,"#334155"],[0.3,"#f59e0b"],[0.6,"#ef4444"],[1,"#dc2626"]],
      cmin: Math.min(...T.colors), cmax: Math.max(...T.colors),
      colorbar: { title: { text: "Kemiskinan (%)" }, thickness: 10 }
    },
    customdata: T.colors,
    hovertemplate: "<b>%{label}</b><br>Penduduk: %{value:,.0f} jiwa<br>Kemiskinan: %{customdata:.2f}%<extra></extra>"
  };
  if (type === "treemap" || type === "icicle") trace.pathbar = { visible: true, thickness: 20 };
  Plotly.newPlot("tm-view", [trace], {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8" },
    margin: { t: 5, l: 5, r: 5, b: 5 }
  }, { responsive: true });

  const clickEvt = (type === "sunburst") ? "plotly_sunburstclick" : "plotly_treemapclick";
  document.getElementById("tm-view").on(clickEvt, ev => {
    if (!ev?.points?.[0]) return;
    const codes = NODE[ev.points[0].id];
    if (codes && codes.length > 0 && codes.length < GEO.features.length) {
      sel.clear();
      codes.forEach(k => sel.add(k));
      refresh("tm");
      if (codes.length === 1) focusKabkota(codes[0]);
    }
  });
}
renderHierarchyChart("treemap");

function setHierMode(mode) {
  hierMode = mode;
  document.getElementById("btn-tree").classList.toggle("active", mode === "treemap");
  document.getElementById("btn-sun").classList.toggle("active", mode === "sunburst");
  document.getElementById("btn-icicle").classList.toggle("active", mode === "icicle");
  renderHierarchyChart(mode);
}

// ── REFRESH / SINKRONISASI VISUALISASI ──
function refresh(source) {
  poly.setStyle(sty);
  if (source !== "pca") {
    const sp = [1, 2, 3].map(c => {
      if (!sel.size) return null;
      return P.filter(x => x.c === c).map((x, i) => sel.has(x.k) ? i : -1).filter(i => i >= 0);
    });
    Plotly.restyle("pca-view", { selectedpoints: sp }, [0, 1, 2]);
  }
}

// ── RESET KE NASIONAL ──


// ── SCROLL KE BAGIAN TERTENTU ──
function scrollToAct(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── TRANSISI SCROLL DENGAN INTERSECTION OBSERVER ──
const chapterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("visible");
    }
  });
}, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });

document.querySelectorAll(".story-chapter").forEach(el => chapterObserver.observe(el));

// ── SHOW/HIDE NAV RIBBON BASED ON HERO SCROLL POSITION ──
const heroSection = document.getElementById("landing-hero");
const ribbon = document.getElementById("story-ribbon");

if (heroSection && ribbon) {
  const heroObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        ribbon.classList.add("hidden-on-hero");
      } else {
        ribbon.classList.remove("hidden-on-hero");
      }
    });
  }, { threshold: 0.15 });
  heroObserver.observe(heroSection);
}

// ── SCROLLSPY UNTUK STICKY NAV ──
window.addEventListener("scroll", () => {
  const acts = ["sec-opening","sec-514","sec-geo","sec-ipm-pov","sec-pdrb-ipm","sec-iklh","sec-mv","sec-hier","sec-conclusion"];
  const scrollPos = window.scrollY + 120;
  for (let i = acts.length - 1; i >= 0; i--) {
    const el = document.getElementById(acts[i]);
    if (el && el.offsetTop <= scrollPos) {
      document.querySelectorAll(".story-pill").forEach(p => p.classList.remove("active"));
      const targetPill = document.querySelector(`.story-pill[onclick*='${acts[i]}']`);
      if (targetPill) targetPill.classList.add("active");
      break;
    }
  }
});
</script>
</body>
</html>
"""

# ---- 8. INJEKSI DATA KE TEMPLATE & TULIS KE DOCS/INDEX.HTML DAN INDEX.HTML ----
print("7. Melakukan injeksi data ke template HTML...")
j = lambda o: json.dumps(o, separators=(",", ":"))
final_html = (HTML
        .replace("__GEO__", j(geo))
        .replace("__E__", j(EDGES))
        .replace("__P__", j(P))
        .replace("__A__", j(A))
        .replace("__VP__", j(VARPC))
        .replace("__T__", j(T))
        .replace("__NODE__", j(NODE))
        .replace("__H__", j(H))
        .replace("__PAR__", j(PAR))
        .replace("__OUTLIERS__", j(OUTLIERS))
        .replace("__ISLAND_STATS__", j(ISLAND_STATS))
        .replace("__NAT_STATS__", j(NAT_STATS))
        .replace("__SCATTER_IPM__", j(SCATTER_IPM_POV))
        .replace("__SCATTER_PDRB__", j(SCATTER_PDRB_IPM))
        .replace("__IKLH_ISLANDS__", j(IKLH_ISLANDS)))

os.makedirs("docs", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(final_html)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(final_html)

# Copy landing page image to docs/
import shutil
if os.path.exists("landing_page.jpg"):
    shutil.copy2("landing_page.jpg", "docs/landing_page.jpg")
    print("  -> landing_page.jpg disalin ke docs/")

print(f"SELESAI! Webstory berhasil di-generate ke {OUT} dan index.html (Ukuran: {len(final_html)/1e6:.2f} MB)")
