"""Membangun peta interaktif: docs/index.html (statis, siap GitHub Pages).
Peta 1: choropleth variabel RASIO (kemiskinan, IPM, usia produktif, kepadatan, klaster), kelas kuantil 5.
Peta 2: simbol proporsional untuk jumlah penduduk (angka absolut -> bukan choropleth).
Jalankan setelah analysis.py dan buat_geojson.py:   python bangun_peta.py
"""
import json
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

GEO, DATA, OUT = "data_processed/kabkota_bps.geojson", "data_processed/data_master_2024.csv", "docs/index.html"

g = gpd.read_file(GEO)
d = pd.read_csv(DATA, dtype={"kode": str})
g = g[["kode", "kabkota", "provinsi", "geometry"]].merge(
    d[["kode", "penduduk", "kepadatan", "ipm", "kemiskinan", "usia_produktif", "cluster"]], on="kode", how="left")
assert g["penduduk"].notna().all(), "Ada kode yang tidak cocok antara GeoJSON dan data"

p = g.geometry.representative_point()
g["lat"], g["lon"] = p.y.round(3), p.x.round(3)
g["geometry"] = shapely.set_precision(g.geometry.values, 0.001)        # kecilkan ukuran berkas
for k, n in [("penduduk", 0), ("kepadatan", 0), ("ipm", 2), ("kemiskinan", 2), ("usia_produktif", 2)]:
    g[k] = g[k].round(n)

edges = {}
for k in ["kemiskinan", "ipm", "usia_produktif", "kepadatan"]:
    q = np.nanquantile(g[k], [0, .2, .4, .6, .8, 1])
    edges[k] = [float(round(x, 2)) for x in q]

geo = json.loads(g.to_json(drop_id=True))
for f in geo["features"]:                      # NaN -> null, klaster -> bilangan bulat
    pr = f["properties"]
    c = pr.get("cluster")
    pr["cluster"] = None if c is None or c != c else int(c)

HTML = r"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Peta Kab/Kota Indonesia 2024</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>html,body,#m{height:100%;margin:0}body{font:14px system-ui,sans-serif}
.box{background:#fff;padding:8px 10px;border-radius:6px;box-shadow:0 1px 5px rgba(0,0,0,.3);line-height:1.5}
.sw{display:inline-block;width:14px;height:14px;margin-right:6px;vertical-align:middle}select{max-width:55vw}</style></head>
<body><div id="m"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const GEO=__GEO__, EDGES=__EDGES__;
const V={
 kemiskinan:{t:"Persentase kemiskinan (%)",pal:["#ffffb2","#fecc5c","#fd8d3c","#f03b20","#bd0026"]},
 ipm:{t:"Indeks Pembangunan Manusia",pal:["#ffffcc","#a1dab4","#41b6c4","#2c7fb8","#253494"]},
 usia_produktif:{t:"Usia produktif (% penduduk)",pal:["#f2f0f7","#cbc9e2","#9e9ac8","#756bb1","#54278f"]},
 kepadatan:{t:"Kepadatan (jiwa/km²)",pal:["#ffffd4","#fed98e","#fe9929","#d95f0e","#993404"]},
 cluster:{t:"Klaster (PCA + k-means)",cat:{1:"#E69F00",2:"#56B4E9",3:"#009E73"},
  lab:{1:"1 (paling padat)",2:"2 (menengah)",3:"3 (paling jarang)"}}};
const NA="#bdbdbd";
const fmt=v=>v==null?"tidak tersedia":Number(v).toLocaleString("id-ID",{maximumFractionDigits:2});
function col(k,v){if(v==null)return NA;const o=V[k];if(o.cat)return o.cat[v]||NA;
 const e=EDGES[k];let i=0;while(i<4&&v>e[i+1])i++;return o.pal[i];}
let cur="kemiskinan";
const tip=p=>`<b>${p.kabkota}</b><br>${p.provinsi}<br>${V[cur].t}: ${cur==="cluster"&&p.cluster?V.cluster.lab[p.cluster]:fmt(p[cur])}<br>Penduduk: ${fmt(p.penduduk)} jiwa`;
const map=L.map("m").setView([-2.5,118],5);
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
 {attribution:"© OpenStreetMap, © CARTO | Sumber: BPS (2024); batas wilayah: Alf-Anas (2023)",maxZoom:10}).addTo(map);
map.createPane("sym").style.zIndex=450;
const poly=L.geoJSON(GEO,{style:f=>({fillColor:col(cur,f.properties[cur]),weight:.4,color:"#fff",fillOpacity:.85}),
 onEachFeature:(f,l)=>{l.bindTooltip(()=>tip(f.properties),{sticky:true});
  l.on({mouseover:e=>e.target.setStyle({weight:2,color:"#222"}),mouseout:e=>poly.resetStyle(e.target)});}}).addTo(map);
const maxP=Math.max(...GEO.features.map(f=>f.properties.penduduk));
const sym=L.layerGroup(GEO.features.map(f=>{const p=f.properties;
 return L.circleMarker([p.lat,p.lon],{pane:"sym",radius:1.5+22*Math.sqrt(p.penduduk/maxP),color:"#222",weight:.6,
  fillColor:"#fff",fillOpacity:.4}).bindTooltip(`<b>${p.kabkota}</b><br>Penduduk: ${fmt(p.penduduk)} jiwa`);}));
L.control.layers(null,{"Peta tematik (choropleth, rasio)":poly,"Simbol proporsional (jumlah penduduk)":sym},{collapsed:false}).addTo(map);
const sel=L.control({position:"topleft"});
sel.onAdd=()=>{const d=L.DomUtil.create("div","box");
 d.innerHTML="<b>Variabel: </b><select>"+Object.keys(V).map(k=>`<option value="${k}">${V[k].t}</option>`).join("")+"</select>";
 L.DomEvent.disableClickPropagation(d);
 d.querySelector("select").onchange=e=>{cur=e.target.value;poly.setStyle(f=>({fillColor:col(cur,f.properties[cur])}));legend();};
 return d;};
sel.addTo(map);
const lg=L.control({position:"bottomright"});lg.onAdd=()=>L.DomUtil.create("div","box");lg.addTo(map);
function legend(){const o=V[cur];let h=`<b>${o.t}</b><br>`;
 if(o.cat)h+=Object.keys(o.cat).map(k=>`<span class="sw" style="background:${o.cat[k]}"></span>${o.lab[k]}<br>`).join("");
 else{const e=EDGES[cur];h+=o.pal.map((c,i)=>`<span class="sw" style="background:${c}"></span>${fmt(e[i])} – ${fmt(e[i+1])}<br>`).join("");}
 h+=`<span class="sw" style="background:${NA}"></span>tidak tersedia<br><small>${o.cat?"":"Kelas: kuantil, 5 kelas<br>"}Sumber: BPS, 2024</small>`;
 lg.getContainer().innerHTML=h;}
legend();
</script></body></html>"""

html = HTML.replace("__GEO__", json.dumps(geo, separators=(",", ":"))).replace("__EDGES__", json.dumps(edges))
os.makedirs("docs", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Tersimpan: {OUT} ({len(html)/1e6:.1f} MB) | fitur: {len(geo['features'])}")