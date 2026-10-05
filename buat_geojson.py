"""Menyiapkan batas wilayah kab/kota dengan Kode Wilayah BPS sebagai kunci.

Mengapa lewat nama? Shapefile batas (Alf-Anas/batas-administrasi-indonesia, pembaruan Juni 2023,
514 kab/kota) memakai kode Kemendagri (mis. 11.01 = Aceh Selatan), sedangkan data Anda memakai
kode BPS (1101 = Simeulue). Menggabung lewat kode akan salah diam-diam: hanya 295 dari 514 nama cocok.
Karena itu kunci penggabungan adalah (tipe, nama) dan hasilnya diperiksa.

Jalankan:  python buat_geojson.py
Masukan : data_processed/data_bersih.csv (hasil cleaning.py) dan geo/Kab_Kota.shp
Keluaran: data_processed/kabkota_bps.geojson (properti 'kode' = Kode Wilayah BPS)
"""
import re
import geopandas as gpd
import pandas as pd

SHP = "geo/Kab_Kota.shp"
DATA = "data_processed/data_bersih.csv"
OUT = "data_processed/kabkota_bps.geojson"
TOLERANSI = 0.01          # derajat (~1 km) untuk penyederhanaan geometri; naikkan bila berkas terlalu besar

# Pasangan yang tulisannya berbeda (kunci: nama di data BPS -> nama di shapefile)
MANUAL = {
    "Toba Samosir / Toba": "Toba",
    "Kota Padangsidimpuan": "Kota Padang Sidempuan",
    "Kep. Seribu": "Administrasi Kepulauan Seribu",
    "Kota Jakarta Selatan": "Kota Administrasi Jakarta Selatan",
    "Kota Jakarta Timur": "Kota Administrasi Jakarta Timur",
    "Kota Jakarta Pusat": "Kota Administrasi Jakarta Pusat",
    "Kota Jakarta Barat": "Kota Administrasi Jakarta Barat",
    "Kota Jakarta Utara": "Kota Administrasi Jakarta Utara",
    "Siau Tagulandang Biaro": "Kepulauan Siau Tagulandang Biaro",
    "Pangkajene dan Kepulauan": "Pangkajene Kepulauan",
    "Kota Makasar": "Kota Makassar",
    "Mamuju Utara / Pasangkayu": "Pasangkayu",
    "Maluku Tenggara Barat / Kepulauan Tanimbar": "Kepulauan Tanimbar",
}


def tipe(s):
    return "kota" if re.match(r"^\s*kota\b", str(s).lower()) else "kab"


def kunci(s):
    t = str(s).lower()
    t = re.sub(r"^\s*(kota|kab\.?|kabupaten)\s+", "", t).split("/")[0]
    return tipe(s) + "|" + re.sub(r"[^a-z]", "", t)


g = gpd.read_file(SHP)
d = pd.read_csv(DATA, dtype={"kode": str})

d["kabkota"] = d["kabkota"].str.replace(r"\s+", " ", regex=True).str.strip()   # rapikan spasi ganda
d["nama_geo"] = d["kabkota"].replace(MANUAL)
d["kunci"] = d["nama_geo"].map(kunci)
g["kunci"] = g["KAB_KOTA"].map(kunci)

assert not g["kunci"].duplicated().any() and not d["kunci"].duplicated().any(), "Kunci ganda"
m = d[["kode", "kabkota", "provinsi", "kunci"]].merge(g[["kunci", "KAB_KOTA", "PROVINSI", "geometry"]],
                                                      on="kunci", how="outer", indicator=True)
tak_cocok = m[m["_merge"] != "both"]
if len(tak_cocok):
    print(tak_cocok[["kode", "kabkota", "KAB_KOTA", "_merge"]].to_string())
    raise SystemExit("Masih ada daerah yang tidak berpasangan (lihat tabel di atas)")

# Pemeriksaan kewajaran: provinsi di data vs di shapefile (Papua dikecualikan: kode/nama provinsi lama)
def p(s): return re.sub(r"[^a-z]", "", str(s).lower().replace("daerah istimewa", "di").replace("kepulauan", "kep"))
m["prov_sama"] = [p(a) == p(b) for a, b in zip(m["provinsi"], m["PROVINSI"])]
beda = m[~m["prov_sama"]]
print(f"Berpasangan: {len(m)} dari {len(d)} | provinsi berbeda tulisan: {len(beda)}")
print(beda.groupby(["provinsi", "PROVINSI"]).size().to_string())

hasil = gpd.GeoDataFrame(m[["kode", "kabkota", "provinsi", "geometry"]], geometry="geometry", crs=g.crs)
hasil["geometry"] = hasil.geometry.simplify(TOLERANSI, preserve_topology=True)
assert hasil.geometry.is_valid.all() and not hasil.geometry.is_empty.any()
hasil.to_file(OUT, driver="GeoJSON")
print("Tersimpan:", OUT)