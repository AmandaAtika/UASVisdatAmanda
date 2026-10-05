"""Analisis multivariat. Jalankan: python analysis.py  (di folder yang sama dengan cleaning.py)"""
import os
import numpy as np
import pandas as pd
from scipy.stats import skew, chi2
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score

from cleaning import muat_data, VARS as VARS_ALL, OUT_DIR

K = 3                  # jumlah klaster
SEED = 42
BATASI_LAJU = False    # True = laju penduduk dibatasi di persentil ke-99 (hanya untuk PCA/klaster)
DROP = ["laju_penduduk"]   # variabel yang TIDAK dipakai di PCA/klaster; [] = pakai semua 9
VARS = [v for v in VARS_ALL if v not in DROP]

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- 1. Data ----------
df = muat_data()
lengkap = df["data_lengkap"]
print(f"Data lengkap: {lengkap.sum()} | Tidak lengkap: {(~lengkap).sum()}")

X = df.loc[lengkap, VARS].copy()
X_t = X.copy()
X_t["kepadatan"] = np.log10(X_t["kepadatan"])      # kepadatan & PDRB sangat miring (log10)
X_t["pdrb_juta"] = np.log10(X_t["pdrb_juta"])
X_t["kemiskinan"] = np.log10(X_t["kemiskinan"])    # kemiskinan miring ke kanan
if BATASI_LAJU and "laju_penduduk" in X_t:
    X_t["laju_penduduk"] = X_t["laju_penduduk"].clip(upper=X_t["laju_penduduk"].quantile(0.99))
Z = StandardScaler().fit_transform(X_t)

print("\n=== Skewness ===")
print(pd.DataFrame({"mentah": X.apply(skew), "setelah_olah": X_t.apply(skew)}).round(2).to_string())

# ---------- 2. PCA ----------
pca = PCA().fit(Z)
ev = pca.explained_variance_ratio_ * 100
print("\n=== Varians per PC ===")
for i, v in enumerate(ev, 1):
    print(f"PC{i}: {v:.1f}% (kumulatif {ev[:i].sum():.1f}%)")
skor = pca.transform(Z)
loadings = pd.DataFrame(pca.components_[:3].T, index=VARS, columns=["PC1", "PC2", "PC3"])
print("\n=== Loadings ===")
print(loadings.round(3).to_string())

# ---------- 3. Pilih K ----------
print("\n=== Evaluasi K ===")
baris = []
for k in range(2, 9):
    m = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(Z)
    baris.append((k, m.inertia_, silhouette_score(Z, m.labels_)))
    print(f"K={k} inertia={m.inertia_:.1f} silhouette={baris[-1][2]:.3f}")
pd.DataFrame(baris, columns=["k", "inertia", "silhouette"]).to_csv(f"{OUT_DIR}/evaluasi_k.csv", index=False)

# ---------- 4. Klaster (1 = paling padat) ----------
km = KMeans(n_clusters=K, n_init=20, random_state=SEED).fit(Z)
urut = X["kepadatan"].groupby(km.labels_).mean().sort_values(ascending=False).index
peta = {lama: baru + 1 for baru, lama in enumerate(urut)}
label = np.array([peta[l] for l in km.labels_])

prof = X.groupby(label).mean().round(2)
print("\n=== Profil klaster (nilai asli) ===")
print(prof.T.to_string())
print("\nUkuran klaster:\n", pd.Series(label).value_counts().sort_index().to_string())
prof.to_csv(f"{OUT_DIR}/profil_cluster.csv")

# ---------- 5. Korelasi ----------
sp = X.corr(method="spearman")
soc = ["kepadatan", "pdrb_juta", "ipm", "laju_penduduk", "tpt", "kemiskinan"]
env = ["iklh_lahan", "iklh_udara", "iklh_air"]
soc = [v for v in soc if v in VARS]
print("\n=== Spearman: sosial-ekonomi (baris) vs lingkungan (kolom) ===")
print(sp.loc[soc, env].round(3).to_string())
sp.to_csv(f"{OUT_DIR}/korelasi_spearman.csv")

# ---------- 6. Pencilan (jarak Mahalanobis di ruang PCA) ----------
ok = pca.explained_variance_ > 1e-12
d2 = (skor[:, ok] ** 2 / pca.explained_variance_[ok]).sum(axis=1)
batas = chi2.ppf(0.999, df=len(VARS))
pencilan = d2 > batas
zs = pd.DataFrame(Z, index=X.index, columns=VARS)

hasil = df.loc[lengkap, ["kode", "provinsi", "kabkota"]].copy()
hasil["d2"] = d2
hasil["cluster"] = label
hasil["variabel_paling_ekstrem"] = zs.abs().idxmax(axis=1)
hasil = hasil.sort_values("d2", ascending=False)
print(f"\n=== Pencilan (d2 > {batas:.2f}): {pencilan.sum()} daerah ===")
print(hasil.head(12).round(1).to_string())
hasil[hasil["d2"] > batas].to_csv(f"{OUT_DIR}/daerah_pencilan.csv", index=False)

# ---------- 7. Kekokohan: tanpa transformasi ----------
Z2 = StandardScaler().fit_transform(X)
pca2 = PCA().fit(Z2)
km2 = KMeans(n_clusters=K, n_init=20, random_state=SEED).fit(Z2)
print("\n=== Kekokohan (tanpa log) ===")
print(f"Varians PC1 tanpa olah: {pca2.explained_variance_ratio_[0]*100:.1f}%")
print(f"|korelasi| PC1: {abs(np.corrcoef(skor[:, 0], pca2.transform(Z2)[:, 0])[0, 1]):.3f}")
print(f"ARI klaster: {adjusted_rand_score(km.labels_, km2.labels_):.3f}")

# ---------- 8. Simpan ----------
df["PC1"] = np.nan; df["PC2"] = np.nan; df["PC3"] = np.nan
df["cluster"] = np.nan; df["d2"] = np.nan; df["pencilan"] = False
df.loc[lengkap, ["PC1", "PC2", "PC3"]] = skor[:, :3]
df.loc[lengkap, "cluster"] = label
df.loc[lengkap, "d2"] = d2
df.loc[lengkap, "pencilan"] = pencilan
df.to_csv(f"{OUT_DIR}/data_master_2024.csv", index=False)
loadings.to_csv(f"{OUT_DIR}/pca_loadings.csv")
pd.DataFrame({"pc": [f"PC{i}" for i in range(1, len(ev) + 1)], "varians_pct": ev}).to_csv(
    f"{OUT_DIR}/pca_variance.csv", index=False)

print(f"\nSelesai. Daerah dianalisis: {lengkap.sum()} | variabel: {len(VARS)} | klaster: {K}")
print("File: data_master_2024, pca_loadings, pca_variance, profil_cluster, evaluasi_k, korelasi_spearman, daerah_pencilan")