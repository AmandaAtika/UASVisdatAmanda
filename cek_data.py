import pandas as pd

file = "VARIABEL FIX.xlsx"

df = pd.read_excel(file)

print("Ukuran data:")
print(df.shape)

print("\nNama kolom:")
print(df.columns.tolist())

print("\n5 baris pertama:")
print(df.head())

print("\nInfo data:")
print(df.info())

print("\nJumlah missing value:")
print(df.isna().sum())