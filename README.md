# Menjelajahi Karakteristik Indonesia

Webstory visualisasi data tentang pembangunan manusia, kondisi ekonomi, dan kualitas lingkungan hidup di 514 kabupaten/kota Indonesia tahun 2024. Proyek UAS Visualisasi Data dan Informasi 2026.

Laman publik: (isi link GitHub Pages)
Repositori: (isi link repo)

## Topik Visualisasi

Proyek ini memuat tiga topik visualisasi data.

Data geospasial ditampilkan pada bagian Peta Persebaran dalam bentuk peta choropleth (5 kuantil berimbang) dan simbol proporsional. Peta dapat dilihat pada tingkat kabupaten/kota, provinsi, dan pulau, dilengkapi filter pulau, tooltip, zoom/pan, dan legenda.

Data berdimensi tinggi (multivariat) ditampilkan pada bagian Tipe Daerah melalui biplot PCA, parallel coordinates, dan heatmap. Daerah dikelompokkan ke dalam tiga klaster, dan 13 daerah pencilan diidentifikasi dengan jarak Mahalanobis (p < 0,001). Pemilihan daerah saling terhubung antartampilan (brushing dan linking).

Data berhierarki ditampilkan pada bagian Struktur Wilayah melalui treemap, sunburst, dan icicle dengan jenjang Indonesia, pulau, provinsi, dan kabupaten/kota. Ukuran kotak menunjukkan jumlah penduduk dan warna menunjukkan persentase kemiskinan, dengan fitur drill-down.

Bagian pendukung berupa diagram tebaran IPM terhadap kemiskinan, PDRB per kapita terhadap IPM, dan perbandingan IKLH antarpulau.

## Sumber Data

Data utama bersumber dari BPS tahun 2024, meliputi IPM, persentase penduduk miskin, PDRB per kapita ADHK, jumlah dan kepadatan penduduk, persentase penduduk usia produktif, dan tingkat pengangguran terbuka. Indeks Kualitas Lingkungan Hidup (lahan, air, udara) bersumber dari KLHK tahun 2024. Batas wilayah kabupaten/kota menggunakan data Alf-Anas (Juni 2023).

(Isi judul tabel/publikasi, URL, dan tanggal akses untuk setiap data.)

## Data Terolah

Folder data berisi data hasil pengolahan dalam format JSON/GeoJSON, yaitu batas 514 kabupaten/kota beserta atributnya, batas provinsi dan pulau, batas kelas kuantil, skor dan loading PCA, data parallel coordinates dan heatmap, daftar daerah pencilan, struktur hierarki wilayah, serta data diagram pendukung. Seluruh data juga tertanam di index.html sehingga laman dapat dibuka tanpa server.

Folder scripts berisi skrip Python untuk membuat batas provinsi dan pulau dari gabungan batas kabupaten/kota. Nilai provinsi dan pulau merupakan rata-rata nilai kabupaten/kota di dalamnya.

## Teknologi

Laman dibuat dengan HTML, CSS, dan JavaScript tanpa proses build, menggunakan Leaflet.js 1.9.4 untuk peta, Plotly.js 2.35.2 untuk grafik, dan Canvas 2D untuk visual narasi. Peta dasar menggunakan Esri World Dark Gray Canvas. Laman di-deploy melalui GitHub Pages.

## Cara Menjalankan

Buka index.html langsung di peramban, atau jalankan perintah `python -m http.server 8000` di folder proyek lalu buka http://localhost:8000. Gambar halaman pembuka (landing_page.jpg) harus berada di folder yang sama dengan index.html.