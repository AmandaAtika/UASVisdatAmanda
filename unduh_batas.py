"""Mengunduh shapefile batas kab/kota (514 daerah, 38 provinsi, pembaruan Juni 2023) ke folder geo/.
Sumber: https://github.com/Alf-Anas/batas-administrasi-indonesia (folder Kab_Kota)
Perlu:  pip install py7zr
Jalankan SEBELUM buat_geojson.py:   python unduh_batas.py
Total unduhan sekitar 116 MB; berkas yang sudah ada dilewati.
"""
import os
import urllib.request

import py7zr

BASE = "https://raw.githubusercontent.com/Alf-Anas/batas-administrasi-indonesia/master/Kab_Kota/"
BAGIAN = ["Kab_Kota%20SHP.7z.001", "Kab_Kota%20SHP.7z.002", "Kab_Kota%20SHP.7z.003"]
TMP, OUT = "geo/_unduhan", "geo"
os.makedirs(TMP, exist_ok=True)

if os.path.exists(f"{OUT}/Kab_Kota.shp"):
    raise SystemExit("geo/Kab_Kota.shp sudah ada, tidak perlu mengunduh lagi.")

bagian_lokal = []
for nama in BAGIAN:
    tujuan = f"{TMP}/{nama.replace('%20', '_')}"
    if not os.path.exists(tujuan):
        print("Mengunduh", nama, "...")
        urllib.request.urlretrieve(BASE + nama, tujuan)
    bagian_lokal.append(tujuan)

gabung = f"{TMP}/Kab_Kota.7z"
with open(gabung, "wb") as f:                       # arsip 7z terbagi: sambung berurutan
    for b in bagian_lokal:
        with open(b, "rb") as g:
            f.write(g.read())

with py7zr.SevenZipFile(gabung) as z:
    z.extractall(OUT)

assert os.path.exists(f"{OUT}/Kab_Kota.shp"), "Ekstraksi gagal: Kab_Kota.shp tidak ditemukan"
print("Selesai. Lanjutkan dengan:  python buat_geojson.py")