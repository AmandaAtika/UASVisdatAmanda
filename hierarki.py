"""Visualisasi data berhierarki: Indonesia > Kelompok Pulau > Provinsi > Kab/Kota (4 level).
Dua representasi: treemap dan icicle (keduanya punya drill-down + breadcrumb/pathbar).
Ukuran = jumlah penduduk (jiwa); warna = variabel rasio (WARNA_VAR).
Jalankan setelah cleaning.py:  python hierarki.py   ->  data_processed/hierarki.html
"""
import pandas as pd
import plotly.express as px

IN = "data_processed/data_bersih.csv"
OUT = "data_processed/hierarki.html"
WARNA_VAR = "kemiskinan"          # ganti: "ipm", "usia_produktif", "tpt", dst.
LABEL = {"kemiskinan": "Kemiskinan (%)", "ipm": "IPM", "usia_produktif": "Usia produktif (%)",
         "tpt": "TPT (%)"}

# Kelompok pulau dari 2 digit awal kode provinsi BPS (data pendukung non-BPS: pengelompokan sendiri)
PULAU = {"11": "Sumatera", "12": "Sumatera", "13": "Sumatera", "14": "Sumatera", "15": "Sumatera",
         "16": "Sumatera", "17": "Sumatera", "18": "Sumatera", "19": "Sumatera", "21": "Sumatera",
         "31": "Jawa", "32": "Jawa", "33": "Jawa", "34": "Jawa", "35": "Jawa", "36": "Jawa",
         "51": "Bali & Nusa Tenggara", "52": "Bali & Nusa Tenggara", "53": "Bali & Nusa Tenggara",
         "61": "Kalimantan", "62": "Kalimantan", "63": "Kalimantan", "64": "Kalimantan", "65": "Kalimantan",
         "71": "Sulawesi", "72": "Sulawesi", "73": "Sulawesi", "74": "Sulawesi", "75": "Sulawesi",
         "76": "Sulawesi", "81": "Maluku", "82": "Maluku",
         "91": "Papua", "92": "Papua", "94": "Papua", "95": "Papua", "96": "Papua", "97": "Papua"}

df = pd.read_csv(IN, dtype={"kode": str})
df["pulau"] = df["kode"].str[:2].map(PULAU)
assert df["pulau"].notna().all(), "Ada kode provinsi yang belum dipetakan ke kelompok pulau"
df["provinsi"] = df["provinsi"].str.title()
df["negara"] = "Indonesia"
df["kunci"] = df["kode"]          # kode unik: dipakai sebagai id agar nama kembar tidak bentrok

jalur = ["negara", "pulau", "provinsi", "kabkota"]
judul = f"Penduduk (ukuran) dan {LABEL.get(WARNA_VAR, WARNA_VAR)} (warna), 2024 | Sumber: BPS"
tmpl = ("<b>%{label}</b><br>Penduduk: %{value:,.0f} jiwa<br>"
        f"{LABEL.get(WARNA_VAR, WARNA_VAR)} (rata-rata tertimbang penduduk): %{{color:.2f}}"
        "<br>%{currentPath}<extra></extra>")


def buat(fungsi, judul_grafik):
    fig = fungsi(df, path=jalur, values="penduduk", color=WARNA_VAR,
                 color_continuous_scale="Viridis_r" if WARNA_VAR in ("kemiskinan", "tpt") else "Viridis",
                 labels={WARNA_VAR: LABEL.get(WARNA_VAR, WARNA_VAR)}, title=judul_grafik)
    fig.update_traces(hovertemplate=tmpl, root_color="lightgrey")
    fig.update_layout(margin=dict(t=60, l=5, r=5, b=5), height=620)
    return fig


fig_tm = buat(px.treemap, "Treemap: " + judul)
fig_ic = buat(px.icicle, "Icicle: " + judul)
fig_tm.update_traces(pathbar_visible=True)
fig_ic.update_traces(pathbar_visible=True)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Hierarki wilayah</title></head><body>")
    f.write(fig_tm.to_html(full_html=False, include_plotlyjs="cdn"))
    f.write(fig_ic.to_html(full_html=False, include_plotlyjs=False))
    f.write("</body></html>")
print("Tersimpan:", OUT)