"""Membandingkan tiga pilihan variabel pada 499 daerah yang sama.
Jalankan: python bandingkan.py  (tidak mengubah file apa pun)"""
import numpy as np
import pandas as pd
from scipy.stats import chi2, skew
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score

from cleaning import muat_data, VARS

SEED = 42
SPEC = {
    "A: 9 var (laju + TPT)": [],
    "B: tanpa laju (pakai TPT)": ["laju_penduduk"],
    "C: tanpa TPT (pakai laju)": ["tpt"],
}

df = muat_data()
lengkap = df["data_lengkap"]
print(f"Daerah dianalisis: {lengkap.sum()} (sama untuk ketiga pilihan)\n")

baris, label = {}, {}
for nama, drop in SPEC.items():
    V = [v for v in VARS if v not in drop]
    X = df.loc[lengkap, V].copy()
    X["kepadatan"] = np.log10(X["kepadatan"])
    X["pdrb_juta"] = np.log10(X["pdrb_juta"])
    Z = StandardScaler().fit_transform(X)

    pca = PCA().fit(Z)
    ev = pca.explained_variance_ratio_ * 100
    d2 = ((pca.transform(Z) ** 2) / pca.explained_variance_).sum(axis=1)
    urut = np.sort(d2)[::-1]
    batas = chi2.ppf(0.999, df=len(V))

    sil = {}
    for k in range(2, 7):
        sil[k] = silhouette_score(Z, KMeans(k, n_init=20, random_state=SEED).fit(Z).labels_)
    km = KMeans(3, n_init=20, random_state=SEED).fit(Z)
    label[nama] = km.labels_
    # korelasi kedua klaster/PC1 dengan kepadatan: apakah PC1 masih urbanisasi
    pc1 = pca.transform(Z)[:, 0]

    baris[nama] = {
        "jumlah variabel": len(V),
        "PC1 (%)": round(ev[0], 1),
        "PC1+PC2 (%)": round(ev[:2].sum(), 1),
        "PC1-PC3 (%)": round(ev[:3].sum(), 1),
        "skewness terbesar": round(float(pd.DataFrame(Z, columns=V).apply(skew).abs().max()), 2),
        "silhouette K=2": round(sil[2], 3),
        "silhouette K=3": round(sil[3], 3),
        "silhouette K=4": round(sil[4], 3),
        "jumlah pencilan": int((d2 > batas).sum()),
        "d2 terbesar": round(float(urut[0]), 1),
        "d2 kedua": round(float(urut[1]), 1),
        "rasio d2 (1/2)": round(float(urut[0] / urut[1]), 1),
        "ukuran klaster": sorted(np.bincount(km.labels_).tolist(), reverse=True),
        "|r| PC1 vs kepadatan": round(abs(np.corrcoef(pc1, X["kepadatan"])[0, 1]), 2),
    }

pd.set_option("display.width", 250)
print(pd.DataFrame(baris).to_string())

nama = list(SPEC)
ari = pd.DataFrame([[adjusted_rand_score(label[a], label[b]) for b in nama] for a in nama],
                   index=[n[:1] for n in nama], columns=[n[:1] for n in nama]).round(2)
print("\nARI antar-klaster (1 = identik):")
print(ari.to_string())