"""Pembersihan data. Jalankan: python cleaning.py
Fungsi muat_data() juga dipakai oleh analysis.py."""
import os
import pandas as pd

INPUT = "variabel fix.xlsx"   # ganti bila nama file Excel berbeda
SHEET = 0                     # sheet pertama (KabupatenKota)
OUT_DIR = "data_processed"

RENAME = {
    "Kode Wilayah": "kode",
    "Provinsi": "provinsi",
    "Kabupaten/Kota": "kabkota",
    "Kepadatan Penduduk": "kepadatan",
    "PDRB per Kapita": "pdrb_miliar",
    "Indeks Pembangunan Manusia (IPM) 2024": "ipm",
    "TPT": "tpt",
    "Penduduk usia produktif": "produktif_jiwa",   # jumlah jiwa usia 15-64
    "Jumlah Penduduk": "penduduk",                 # total penduduk (jiwa), tahun yang sama
    "Persentase Kemiskinan": "kemiskinan",
    "Indeks Kualitas Lahan": "iklh_lahan",
    "Indeks Kualitas Udara": "iklh_udara",
    "Indeks Kualitas Air": "iklh_air",
}
KOL_ANGKA = ["kepadatan", "pdrb_miliar", "ipm", "tpt", "produktif_jiwa", "penduduk",
             "kemiskinan", "iklh_lahan", "iklh_udara", "iklh_air"]
VARS = ["kepadatan", "pdrb_juta", "ipm", "tpt", "usia_produktif",
        "kemiskinan", "iklh_lahan", "iklh_udara", "iklh_air"]

# Rentang wajar (batas bawah, batas atas); di luar ini dianggap salah data
RENTANG = {
    "kepadatan": (0.01, 100000), "pdrb_juta": (0.1, 5000), "ipm": (30, 95),
    "tpt": (0, 30), "usia_produktif": (30, 90), "kemiskinan": (0, 60),
    "iklh_lahan": (0, 100), "iklh_udara": (0, 100), "iklh_air": (0, 100),
}


def ke_angka(s):
    """Ubah kolom ke angka. Menghapus semua spasi (termasuk spasi non-breaking),
    mengganti koma desimal; teks seperti '-' menjadi NaN."""
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    t = (s.astype(str).str.replace(r"\s+", "", regex=True)
          .str.replace(",", ".", regex=False))
    return pd.to_numeric(t, errors="coerce")


def muat_data(verbose=False):
    raw = pd.read_excel(INPUT, sheet_name=SHEET)
    raw.columns = [str(c).strip() for c in raw.columns]
    hilang = [c for c in RENAME if c not in raw.columns]
    if hilang:
        raise KeyError(f"Kolom tidak ditemukan di Excel: {hilang}\nKolom yang ada: {list(raw.columns)}")

    df = raw[list(RENAME)].rename(columns=RENAME).copy()
    df["kode"] = df["kode"].astype(str).str.replace(r"\D", "", regex=True)

    for kol in KOL_ANGKA:
        asli = df[kol]
        baru = ke_angka(asli)
        gagal = asli.notna() & baru.isna()
        if verbose:
            print(f"{kol:15s} gagal diparse: {gagal.sum():3d}", end="")
            print(f"   nilai asli: {sorted(set(asli[gagal].astype(str)))}" if gagal.any() else "")
        df[kol] = baru

    df["pdrb_juta"] = df["pdrb_miliar"] * 1000   # miliar Rp/jiwa -> juta Rp/jiwa (ADHK)
    # jumlah jiwa usia produktif -> persentase terhadap total penduduk
    if (df["produktif_jiwa"] > df["penduduk"]).any():
        raise ValueError("Ada daerah dengan penduduk usia produktif > total penduduk (cek kolom di Excel)")
    df["usia_produktif"] = df["produktif_jiwa"] / df["penduduk"] * 100

    # ---- pemeriksaan ----
    if len(df) != 514:
        print(f"PERINGATAN: jumlah baris {len(df)} (diharapkan 514)")
    if df["kode"].duplicated().any():
        raise ValueError("Ada kode wilayah duplikat")
    if df[VARS].T.duplicated().any():
        raise ValueError("Ada dua kolom variabel yang isinya sama persis (cek Excel)")
    for kol, (lo, hi) in RENTANG.items():
        v = df[kol].dropna()
        buruk = v[(v < lo) | (v > hi)]
        if len(buruk):
            raise ValueError(f"{kol}: {len(buruk)} nilai di luar rentang {lo}-{hi}, "
                             f"contoh: {df.loc[buruk.index[:3], ['kabkota', kol]].values.tolist()}")

    df["data_lengkap"] = df[VARS].notna().all(axis=1)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print("=== PARSING ===")
    df = muat_data(verbose=True)

    print(f"\nBaris: {len(df)} | kode unik: {df['kode'].nunique()}")
    print("\n=== MISSING PER VARIABEL ===")
    print(df[VARS].isna().sum().to_string())
    print(f"\nData lengkap: {df['data_lengkap'].sum()} | Tidak lengkap: {(~df['data_lengkap']).sum()}")
    print("\n=== DAERAH TIDAK LENGKAP ===")
    tdk = df[~df["data_lengkap"]]
    print(tdk[["kode", "provinsi", "kabkota"]].assign(
        kosong=tdk[VARS].isna().apply(lambda r: ",".join(r.index[r]), axis=1)).to_string())
    print("\n=== RENTANG ===")
    print(df[VARS].describe().T[["count", "min", "50%", "max", "mean"]].round(3).to_string())

    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(f"{OUT_DIR}/data_bersih.csv", index=False)
    print(f"\nTersimpan: {OUT_DIR}/data_bersih.csv")