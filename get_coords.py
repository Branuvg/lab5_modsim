import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import shapely
import pyproj
from scipy import stats
from scipy.spatial import cKDTree
from matplotlib_scalebar.scalebar import ScaleBar

warnings.filterwarnings("ignore", category=UserWarning)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 100)

print("geopandas :", gpd.__version__)
print("shapely   :", shapely.__version__)
print("pandas    :", pd.__version__)
print("numpy     :", np.__version__)
print("matplotlib:", matplotlib.__version__)
print("pyproj    :", pyproj.__version__)
# ---------------- Parámetros globales del análisis ----------------
STATE = "AL"              # código postal del estado (columna `estado` de hospitales)
STATE_FIPS = "01"         # código FIPS del estado (columna `cod_estado` de condados)
STATE_NAME = "Alabama"
CRS_PROJ = "EPSG:32616"   # WGS 84 / UTM zona 16N (metros) -> justificación en Task 1.1d
RADII_KM = [10, 25, 50]   # radios de buffer del Task 1.3
R_MAP = 25                # radio del mapa de cobertura y del MCLP

# Paleta (categórica en orden fijo; diverging azul<->rojo con gris neutro)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
NEUTRAL = "#f0efec"
TIPO_ES = {"GENERAL ACUTE CARE": "Cuidados agudos generales", "CRITICAL ACCESS": "Acceso crítico",
           "PSYCHIATRIC": "Psiquiátrico", "LONG TERM CARE": "Cuidados a largo plazo",
           "REHABILITATION": "Rehabilitación", "MILITARY": "Militar", "CHILDREN": "Infantil",
           "SPECIAL": "Especial", "WOMEN": "Mujeres", "CHRONIC DISEASE": "Enfermedad crónica", "OTHER": "Otro"}


def add_north_and_scale(ax, loc="lower left"):
    """Escala gráfica (las coordenadas están en metros) y flecha de norte."""
    ax.add_artist(ScaleBar(1, units="m", location=loc, box_alpha=0.8, length_fraction=0.25))
    ax.annotate("N", xy=(0.95, 0.95), xytext=(0.95, 0.85), xycoords="axes fraction",
                ha="center", va="center", fontsize=14, fontweight="bold",
                arrowprops=dict(facecolor="black", width=4, headwidth=12))
hosp_raw = gpd.read_file("hospitales_eeuu.geojson")
counties_raw = gpd.read_file("condados_eeuu.geojson")
states = gpd.read_file("estados_eeuu.geojson")
pop_raw = pd.read_csv("poblacion_condados.csv")

resumen = pd.DataFrame([
    {"archivo": name, "registros": len(df), "CRS": str(df.crs) if isinstance(df, gpd.GeoDataFrame) else "— (tabla)",
     "columnas": ", ".join(df.columns)}
    for name, df in [("hospitales_eeuu.geojson", hosp_raw), ("condados_eeuu.geojson", counties_raw),
                     ("poblacion_condados.csv", pop_raw), ("estados_eeuu.geojson", states)]])
with pd.option_context("display.max_colwidth", 200):
    print(resumen)
n_fake = (pop_raw["fips"] >= 80000).sum()
pop = pop_raw[pop_raw["fips"] < 80000].copy()
pop["fips"] = pop["fips"].astype(int).astype(str).str.zfill(5)
print(f"Población: {len(pop_raw)} registros -> {len(pop)} (eliminados {n_fake} con FIPS >= 80000)")
print(f"  ¿Todos los FIPS tienen 5 dígitos? {pop['fips'].str.len().eq(5).all()} | ejemplo: {pop['fips'].iloc[0]}")
print(f"  Población nula restante: {pop['poblacion'].isna().sum()}")

pct_null = 100 * hosp_raw["camas_total"].isna().mean()
pct_null_st = 100 * hosp_raw.loc[hosp_raw["estado"] == STATE, "camas_total"].isna().mean()
hosp = hosp_raw[hosp_raw["camas_total"].notna()].copy()
print(f"\nHospitales con camas_total nulo: {hosp_raw['camas_total'].isna().sum()} de {len(hosp_raw)} "
      f"= {pct_null:.2f} % (en {STATE_NAME}: {pct_null_st:.2f} %)")
print(f"Hospitales con datos de camas (EE.UU.): {len(hosp)}")
print(f"Hospitales en {STATE_NAME}: {(hosp_raw.estado == STATE).sum()} antes -> {(hosp.estado == STATE).sum()} "
      "después de la limpieza")
hosp_st = hosp[hosp["estado"] == STATE].reset_index(drop=True)
cty_geo = counties_raw[counties_raw["cod_estado"] == STATE_FIPS]
pop_st = pop[pop["fips"].str[:2] == STATE_FIPS]
state_geo = states[states["codigo"] == STATE]

# unión 1:1 por la llave FIPS
cty = cty_geo.merge(pop_st[["fips", "poblacion"]], on="fips", how="left", validate="1:1").reset_index(drop=True)
print(f"Condados con geometría : {len(cty_geo)}")
print(f"Condados con población : {len(pop_st)}")
print(f"Condados unidos        : {cty['poblacion'].notna().sum()}  -> ¿coinciden? "
      f"{len(cty_geo) == len(pop_st) == cty['poblacion'].notna().sum()}")
print(f"Población total de {STATE_NAME}: {cty['poblacion'].sum():,.0f}")

# verificación espacial: ¿todos los hospitales caen dentro del límite estatal?
inside_state = hosp_st.within(state_geo.geometry.iloc[0])
print(f"\nHospitales del estado: {len(hosp_st)} | dentro del polígono estatal: {inside_state.sum()}")
print(hosp_st["tipo"].value_counts().rename(index=TIPO_ES).to_string())
cty_p0 = cty.to_crs(CRS_PROJ)
gx, gy = np.meshgrid(np.linspace(*cty_p0.total_bounds[[0, 2]], 60), np.linspace(*cty_p0.total_bounds[[1, 3]], 60))
grid_pts = gpd.GeoSeries(gpd.points_from_xy(gx.ravel(), gy.ravel()), crs=CRS_PROJ)
grid_pts = grid_pts[grid_pts.within(cty_p0.union_all())].to_crs("EPSG:4326")
cent_ll = cty_p0.geometry.centroid.to_crs("EPSG:4326")

rows = []
for epsg, desc in [(32616, "UTM 16N (WGS84)"), (26929, "State Plane Alabama Este"),
                   (26930, "State Plane Alabama Oeste"), (5070, "Albers EE.UU. contiguo")]:
    proj = pyproj.Proj(f"EPSG:{epsg}")
    def err(lon, lat):
        f = proj.get_factors(lon, lat)
        return 100 * np.maximum(np.abs(f.meridional_scale - 1), np.abs(f.parallel_scale - 1))
    rows.append({"CRS": f"EPSG:{epsg}", "descripción": desc,
                 "error escala máx (%)": err(grid_pts.x.values, grid_pts.y.values).max(),
                 "error medio ponderado por población (%)": np.average(err(cent_ll.x.values, cent_ll.y.values),
                                                                       weights=cty["poblacion"])})
pd.DataFrame(rows).set_index("CRS")
hosp_p = hosp_st.to_crs(CRS_PROJ)
cty_p = cty.to_crs(CRS_PROJ)
state_p = state_geo.to_crs(CRS_PROJ)
state_poly = state_p.geometry.iloc[0]
for name, g in [("hospitales", hosp_p), ("condados", cty_p), ("estado", state_p)]:
    print(f"{name:<11} -> {g.crs}")
cty_p["area_km2"] = cty_p.area / 1e6
print(f"Área total de los condados: {cty_p['area_km2'].sum():,.0f} km²")
tipos_orden = hosp_p["tipo"].value_counts().index.tolist()
markers = ["o", "s", "^", "D", "v", "P", "X", "*"]
fig, ax = plt.subplots(figsize=(10, 12))
cty_p.plot(ax=ax, color="#dcdcdc", edgecolor="white", linewidth=0.6)
for i, t in enumerate(tipos_orden):
    sub = hosp_p[hosp_p["tipo"] == t]
    sub.plot(ax=ax, color=CAT[i], marker=markers[i], markersize=45, edgecolor="white", linewidth=0.5,
             label=f"{TIPO_ES.get(t, t)} ({len(sub)})", zorder=3)
state_p.boundary.plot(ax=ax, color="#222222", linewidth=1.2, zorder=4)
ax.legend(title="Tipo de hospital", loc="lower right", frameon=True)
add_north_and_scale(ax)
ax.set_title(f"{STATE_NAME}: hospitales con datos de camas ({len(hosp_p)}), condados y límite estatal\n"
             f"{CRS_PROJ}", fontsize=12)
ax.set_axis_off()
plt.tight_layout()
plt.show()
hj = gpd.sjoin(hosp_p, cty_p[["fips", "geometry"]], how="left", predicate="within")
print(f"Hospitales asignados a un condado: {hj['fips'].notna().sum()} de {len(hj)} | "
      f"coinciden con la columna fips_condado: {(hj['fips'] == hj['fips_condado']).mean():.1%}")

agg = hj.groupby("fips").agg(hospitales=("nombre", "size"), camas_total=("camas_total", "sum"),
                             camas_uci=("camas_icu", lambda s: s.fillna(0).sum()))
stats_cty = cty_p[["fips", "nombre", "poblacion", "area_km2"]].merge(agg, on="fips", how="left")
stats_cty[["hospitales", "camas_total", "camas_uci"]] = stats_cty[["hospitales", "camas_total", "camas_uci"]].fillna(0)
stats_cty["hospitales"] = stats_cty["hospitales"].astype(int)
stats_cty["camas_10k"] = 1e4 * stats_cty["camas_total"] / stats_cty["poblacion"]
stats_cty["uci_10k"] = 1e4 * stats_cty["camas_uci"] / stats_cty["poblacion"]
tabla_12 = stats_cty.drop(columns="area_km2").sort_values("nombre").reset_index(drop=True)
tabla_12.index += 1
print(f"Condados sin hospital: {(stats_cty.hospitales == 0).sum()} de {len(stats_cty)}")
tabla_12
big = stats_cty[stats_cty["poblacion"] > 10_000]
print(f"Condados con > 10,000 hab.: {len(big)} | de ellos con 0 camas: {(big.camas_total == 0).sum()}")
low5 = big.sort_values(["camas_10k", "poblacion"], ascending=[True, False]).head(5).reset_index(drop=True)
low5.index += 1
low5[["nombre", "poblacion", "hospitales", "camas_total", "camas_uci", "camas_10k", "uci_10k"]]
top5c = stats_cty.sort_values("camas_10k", ascending=False).head(5).copy()
geo_idx = cty_p.set_index("fips").geometry
rows = []
for _, r in top5c.iterrows():
    neigh = cty_p[cty_p.geometry.touches(geo_idx[r.fips])]["fips"]
    nb = stats_cty[stats_cty["fips"].isin(neigh)]
    big_h = hosp_p[hosp_p["fips_condado"] == r.fips].sort_values("camas_total", ascending=False).iloc[0]
    rows.append({"condado": r.nombre, "poblacion": r.poblacion, "camas_total": r.camas_total,
                 "camas_10k": r.camas_10k, "vecinos": len(nb), "vecinos_sin_hospital": int((nb.hospitales == 0).sum()),
                 "camas_10k_vecinos": 1e4 * nb.camas_total.sum() / nb.poblacion.sum(),
                 "camas_10k_regional": 1e4 * (r.camas_total + nb.camas_total.sum()) / (r.poblacion + nb.poblacion.sum()),
                 "hospital_principal": f"{big_h.nombre.title()} ({big_h.camas_total:.0f} camas)"})
top5_tbl = pd.DataFrame(rows)
top5_tbl.index += 1
print(f"Promedio estatal: {1e4 * stats_cty.camas_total.sum() / stats_cty.poblacion.sum():.1f} camas por 10,000 hab.")
with pd.option_context("display.max_colwidth", 60):
    print(top5_tbl)
camas_h = hosp_p["camas_total"]
camas_c = stats_cty["camas_10k"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5))
a1.hist(camas_h, bins=25, color=CAT[0], edgecolor="white")
a1.axvline(camas_h.mean(), color=CAT[1], ls="--", lw=1.5, label=f"Media = {camas_h.mean():.0f}")
a1.axvline(camas_h.median(), color="#222222", ls=":", lw=1.5, label=f"Mediana = {camas_h.median():.0f}")
a1.set(title="Camas totales por hospital", xlabel="Camas totales", ylabel="Número de hospitales")
a1.legend()
a1.grid(alpha=0.3, axis="y")
a2.hist(camas_c, bins=25, color=CAT[0], edgecolor="white")
a2.axvline(camas_c.mean(), color=CAT[1], ls="--", lw=1.5, label=f"Media = {camas_c.mean():.1f}")
a2.axvline(camas_c.median(), color="#222222", ls=":", lw=1.5, label=f"Mediana = {camas_c.median():.1f}")
a2.set(title="Camas por cada 10,000 habitantes por condado", xlabel="Camas por 10,000 hab.",
       ylabel="Número de condados")
a2.legend()
a2.grid(alpha=0.3, axis="y")
plt.tight_layout()
plt.show()

desc = pd.DataFrame({
    "camas por hospital": [len(camas_h), camas_h.mean(), camas_h.median(), camas_h.min(), camas_h.max(),
                           stats.skew(camas_h), (camas_h > camas_h.quantile(0.75) + 1.5 * stats.iqr(camas_h)).sum()],
    "camas por 10k hab. (condado)": [len(camas_c), camas_c.mean(), camas_c.median(), camas_c.min(), camas_c.max(),
                                    stats.skew(camas_c), (camas_c > camas_c.quantile(0.75) + 1.5 * stats.iqr(camas_c)).sum()]},
    index=["n", "media", "mediana", "mínimo", "máximo", "asimetría g1", "valores extremos (> Q3 + 1.5·IQR)"])
print(f"Condados con 0 camas: {(camas_c == 0).sum()} de {len(camas_c)}")
desc
from shapely.ops import unary_union

coverage = {}
for r in RADII_KM:
    buffers = hosp_p.geometry.buffer(r * 1000, resolution=32)        # metros, porque el CRS es UTM
    coverage[r] = unary_union(buffers.values)
    a_in = coverage[r].intersection(state_poly).area / 1e6
    print(f"r = {r:>2} km: {len(buffers)} buffers -> 1 polígono ({coverage[r].geom_type}), área cubierta dentro "
          f"del estado = {a_in:,.0f} km² ({100 * a_in / (state_poly.area / 1e6):.1f} %)")
P_TOTAL = cty_p["poblacion"].sum()


def frac_covered(cov_geom):
    """Fracción del área de cada condado dentro del polígono de cobertura."""
    return (cty_p.geometry.intersection(cov_geom).area / cty_p.area).clip(0, 1).values


cov_rows = []
for r in RADII_KM:
    pc = (cty_p["poblacion"] * frac_covered(coverage[r])).sum()
    cov_rows.append({"radio_km": r, "poblacion_cubierta_estimada": pc, "poblacion_total": P_TOTAL,
                     "pct_cobertura": 100 * pc / P_TOTAL})
cov_tbl = pd.DataFrame(cov_rows)
cov_tbl
cov25 = coverage[R_MAP]
cty_p["frac_cub25"] = frac_covered(cov25)
cty_p["cobertura25"] = pd.cut(cty_p["frac_cub25"], [-0.01, 0.005, 0.995, 1.01],
                              labels=["No cubierto", "Parcialmente cubierto", "Completamente cubierto"])
DIV = {"No cubierto": "#c0392b", "Parcialmente cubierto": NEUTRAL, "Completamente cubierto": "#2a78d6"}

fig, ax = plt.subplots(figsize=(10, 12))
cty_p.plot(ax=ax, color=cty_p["cobertura25"].map(DIV).astype(str), edgecolor="#9a9a9a", linewidth=0.5)
gpd.GeoSeries([cov25.intersection(state_poly)], crs=CRS_PROJ).boundary.plot(ax=ax, color="#1c5cab",
                                                                             linewidth=0.8, linestyle="--")
hosp_p.plot(ax=ax, color="black", markersize=10, zorder=4)
state_p.boundary.plot(ax=ax, color="#222222", linewidth=1.0)
counts = cty_p["cobertura25"].value_counts()
handles = [Patch(facecolor=c, edgecolor="#9a9a9a", label=f"{k} ({counts.get(k, 0)})") for k, c in DIV.items()]
handles += [Line2D([], [], color="#1c5cab", ls="--", label=f"Límite del área cubierta ({R_MAP} km)"),
            Line2D([], [], marker="o", color="black", ls="", markersize=4, label="Hospital")]
ax.legend(handles=handles, loc="lower right", title=f"Condados — cobertura a {R_MAP} km")
add_north_and_scale(ax)
ax.set_title(f"Cobertura hospitalaria con buffer de {R_MAP} km — "
             f"{cov_tbl.loc[cov_tbl.radio_km == R_MAP, 'pct_cobertura'].item():.1f} % de la población cubierta")
ax.set_axis_off()
plt.tight_layout()
plt.show()
print(counts.to_frame("condados"))
print("\nCondados NO cubiertos:", ", ".join(cty_p.loc[cty_p.cobertura25 == "No cubierto", "nombre"]) or "ninguno")
hosp_xy = np.column_stack([hosp_p.geometry.x, hosp_p.geometry.y])
tree = cKDTree(hosp_xy)
cent = cty_p.geometry.centroid
d, j = tree.query(np.column_stack([cent.x, cent.y]))
cty_p["dist_km"] = d / 1000
cty_p["hosp_cercano"] = hosp_p["nombre"].str.title().values[j]
cty_p["tipo_cercano"] = hosp_p["tipo"].values[j]
cty_p["camas_cercano"] = hosp_p["camas_total"].values[j]

far10 = cty_p.sort_values("dist_km", ascending=False).head(10)
far10_tbl = far10[["nombre", "poblacion", "dist_km", "hosp_cercano"]].reset_index(drop=True)
far10_tbl.index += 1
print(f"Distancia media centroide–hospital: {cty_p.dist_km.mean():.1f} km (mediana {cty_p.dist_km.median():.1f} km)")
far10_tbl
hosp_all_p = hosp.to_crs(CRS_PROJ)
d_all, j_all = cKDTree(np.column_stack([hosp_all_p.geometry.x, hosp_all_p.geometry.y])).query(
    np.column_stack([cent.x, cent.y]))
cty_p["dist_km_todos"] = d_all / 1000
cty_p["estado_cercano_todos"] = hosp_all_p["estado"].values[j_all]
borde = cty_p.loc[far10.index, ["nombre", "dist_km", "dist_km_todos", "estado_cercano_todos"]].reset_index(drop=True)
borde.index += 1
borde
radii = np.arange(5, 101, 5)
curve = np.array([100 * (cty_p["poblacion"] * frac_covered(unary_union(hosp_p.geometry.buffer(r * 1000).values))).sum()
                  / P_TOTAL for r in radii])
marg = np.diff(np.concatenate([[0], curve]))

xn = (radii - radii.min()) / (radii.max() - radii.min())
yn = (curve - curve.min()) / (curve.max() - curve.min())
r_knee = radii[np.argmax(yn - xn)]
c_knee = curve[radii == r_knee].item()
r_1pp = radii[np.argmax(marg < 1)]

fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5))
a1.plot(radii, curve, color=CAT[0], lw=2, marker="o", markersize=4)
a1.plot([radii[0], radii[-1]], [curve[0], curve[-1]], color="#9a9a9a", lw=1, ls=":", label="Recta entre extremos (Kneedle)")
a1.scatter([r_knee], [c_knee], color=CAT[1], s=80, zorder=3, label=f"Codo (Kneedle): {r_knee} km → {c_knee:.1f} %")
a1.axvline(R_MAP, color="#9a9a9a", lw=1, ls="--")
a1.text(R_MAP + 1, curve.min() + 2, f"{R_MAP} km", color="#52514e")
a1.set(xlabel="Radio del buffer (km)", ylabel="Población cubierta (%)", title="Curva de cobertura acumulada",
       xlim=(0, 103), ylim=(curve.min() - 3, 101))
a1.grid(alpha=0.3)
a1.legend(loc="lower right")
a2.bar(radii, marg, color=CAT[0], width=3.5)
a2.axhline(1, color=CAT[1], lw=1.5, ls="--", label="1 p.p. por cada 5 km")
a2.axvline(r_knee, color="#9a9a9a", lw=1, ls=":")
a2.set(xlabel="Radio del buffer (km)", ylabel="Ganancia marginal (p.p.)", title="Ganancia marginal por cada 5 km")
a2.grid(alpha=0.3, axis="y")
a2.legend()
plt.tight_layout()
plt.show()

print(f"Codo (Kneedle): r = {r_knee} km, cobertura = {c_knee:.1f} %")
print(f"Primer radio con ganancia < 1 p.p.: r = {r_1pp} km, cobertura = {curve[radii == r_1pp].item():.1f} %")
pd.DataFrame({"radio_km": radii, "pct_cobertura": curve, "ganancia_pp": marg}).set_index("radio_km").T.round(1)
far5 = far10.head(5)
far5_tbl = far5[["nombre", "dist_km", "hosp_cercano", "tipo_cercano", "camas_cercano"]].reset_index(drop=True)
far5_tbl["tipo_cercano"] = far5_tbl["tipo_cercano"].map(TIPO_ES)
far5_tbl.index += 1
print(far5_tbl)

rho, pval = stats.spearmanr(cty_p["dist_km"], cty_p["camas_cercano"])
comp = pd.DataFrame({
    "5 condados más alejados": [far5.camas_cercano.median(), far5.camas_cercano.mean(), (far5.camas_cercano < 50).mean() * 100],
    "resto de condados": [cty_p.drop(far5.index).camas_cercano.median(), cty_p.drop(far5.index).camas_cercano.mean(),
                          (cty_p.drop(far5.index).camas_cercano < 50).mean() * 100],
    "todos los hospitales": [hosp_p.camas_total.median(), hosp_p.camas_total.mean(), (hosp_p.camas_total < 50).mean() * 100]},
    index=["mediana de camas", "media de camas", "% con < 50 camas"])
print(f"Correlación de Spearman (distancia vs camas del hospital más cercano): rho = {rho:.2f}, p = {pval:.3f}")
comp
def minmax(s):
    return (s - s.min()) / (s.max() - s.min())


vul = cty_p[["fips", "nombre", "poblacion", "geometry"]].merge(stats_cty[["fips", "camas_total", "hospitales"]], on="fips")
vul["x1_dist_km"] = cty_p["dist_km"].values

# C2: inverso de camas por habitante (habitantes por cama); condados sin camas -> valor máximo observado
inv = vul["poblacion"] / vul["camas_total"].replace(0, np.nan)
vul["x2_hab_por_cama"] = inv.fillna(inv.max())

# C3: ocupación promedio de hospitales dentro de 50 km del centroide; sin hospitales cercanos -> máximo
occ = hosp_p["ocupacion_total"].values
near50 = tree.query_ball_point(np.column_stack([cent.x, cent.y]), r=50_000)
occ_mean = np.array([np.nanmean(occ[m]) if len(m) and np.isfinite(occ[m]).any() else np.nan for m in near50])
vul["n_hosp_50km"] = [len(m) for m in near50]
vul["x3_ocupacion_50km"] = np.where(np.isnan(occ_mean), np.nanmax(occ_mean), occ_mean)

vul["C1"] = minmax(vul["x1_dist_km"])
vul["C2"] = minmax(vul["x2_hab_por_cama"])
vul["C3"] = minmax(vul["x3_ocupacion_50km"])
print(f"Condados sin camas (C2 = máximo): {(vul.camas_total == 0).sum()} | "
      f"sin hospitales a ≤ 50 km (C3 = máximo): {np.isnan(occ_mean).sum()}")
vul[["x1_dist_km", "x2_hab_por_cama", "x3_ocupacion_50km", "C1", "C2", "C3"]].describe().T[["mean", "50%", "min", "max"]]
WEIGHTS = {"C1": 0.45, "C2": 0.35, "C3": 0.20}
vul["V"] = sum(w * vul[c] for c, w in WEIGHTS.items())

LABELS = ["Muy baja", "Baja", "Media", "Alta", "Muy alta"]
vul["V_cat"] = pd.qcut(vul["V"], 5, labels=LABELS)
top10 = vul.sort_values("V", ascending=False).head(10)
top10_tbl = top10[["nombre", "poblacion", "x1_dist_km", "x2_hab_por_cama", "x3_ocupacion_50km",
                   "C1", "C2", "C3", "V"]].reset_index(drop=True)
top10_tbl.index += 1
top10_tbl
SEQ = ["#fde0c5", "#f8b58b", "#f08a5b", "#d95926", "#a33a12"]   # un solo tono (naranja), claro -> oscuro
fig, ax = plt.subplots(figsize=(11, 12))
vul.plot(ax=ax, color=vul["V_cat"].map(dict(zip(LABELS, SEQ))).astype(str), edgecolor="white", linewidth=0.6)
state_p.boundary.plot(ax=ax, color="#222222", linewidth=1.0)
top10.boundary.plot(ax=ax, color="black", linewidth=1.8)
hosp_p.plot(ax=ax, color="black", markersize=6, zorder=4)
names = []
for rank, (_, r) in enumerate(top10.iterrows(), start=1):
    pt = r.geometry.representative_point()
    ax.annotate(f"{rank}. {r.nombre}", xy=(pt.x, pt.y), fontsize=9, fontweight="bold", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")], zorder=5)
    names.append(f"{rank:>2}. {r.nombre} — {r.V:.2f}")
ax.text(1.01, 0.99, "10 condados más vulnerables\n" + "\n".join(names), transform=ax.transAxes,
        va="top", ha="left", fontsize=9, family="monospace",
        bbox=dict(boxstyle="round", facecolor="white", edgecolor="#9a9a9a", alpha=0.92))
bins = vul.groupby("V_cat", observed=True)["V"].agg(["min", "max"])
handles = [Patch(facecolor=c, label=f"{l} ({bins.loc[l, 'min']:.2f}–{bins.loc[l, 'max']:.2f})")
           for l, c in zip(LABELS, SEQ)]
handles += [Patch(facecolor="none", edgecolor="black", linewidth=1.8, label="Top 10 más vulnerables"),
            Line2D([], [], marker="o", color="black", ls="", markersize=3, label="Hospital")]
ax.legend(handles=handles, title="Índice de vulnerabilidad (quintiles)", loc="lower left", bbox_to_anchor=(1.01, 0))
add_north_and_scale(ax)
ax.set_title("Índice compuesto de vulnerabilidad de acceso hospitalario por condado\n"
             f"V = {WEIGHTS['C1']}·distancia + {WEIGHTS['C2']}·habitantes por cama + {WEIGHTS['C3']}·ocupación (50 km)")
ax.set_axis_off()
plt.tight_layout()
plt.show()
SPACING, S, P_NEW = 50_000, R_MAP * 1000, 3
minx, miny, maxx, maxy = state_poly.bounds
gx, gy = np.meshgrid(np.arange(minx + SPACING / 2, maxx, SPACING), np.arange(miny + SPACING / 2, maxy, SPACING))
grid = gpd.GeoDataFrame(geometry=gpd.points_from_xy(gx.ravel(), gy.ravel()), crs=CRS_PROJ)
cand = grid[grid.intersects(state_poly)].reset_index(drop=True)
print(f"Puntos de la grilla: {len(grid)} | fuera del estado: {len(grid) - len(cand)} | candidatos: {len(cand)}")
dens = (cty_p["poblacion"] / cty_p.area).values               # hab/m²
cand_buf = cand.geometry.buffer(S, resolution=32)


def gains(cov_geom):
    """Población no cubierta (bajo cov_geom) dentro del buffer de cada candidato."""
    uncovered = cty_p.geometry.difference(cov_geom)          # A_k \ C
    out = np.zeros(len(cand))
    for i, b in enumerate(cand_buf):
        out[i] = (uncovered.intersection(b).area.values * dens).sum()
    return out


cand["pob_adicional"] = gains(cov25)
print(f"Candidatos con ganancia > 1,000 hab.: {(cand.pob_adicional > 1000).sum()} de {len(cand)}")
cand.sort_values("pob_adicional", ascending=False).head(10).assign(
    x=lambda d: d.geometry.x.round(), y=lambda d: d.geometry.y.round()).drop(columns="geometry")
cov_state = cov25
base_pct = 100 * (cty_p["poblacion"] * frac_covered(cov_state)).sum() / P_TOTAL
selected = []
for it in range(1, P_NEW + 1):
    g = gains(cov_state)
    g[[s["idx"] for s in selected]] = -1                       # no repetir candidatos
    j_best = int(np.argmax(g))
    cov_state = cov_state.union(cand_buf.iloc[j_best])         # actualizar el mapa de cobertura
    selected.append({"idx": j_best, "iteracion": it, "pob_adicional": g[j_best],
                     "pct_cobertura_acumulada": 100 * (cty_p["poblacion"] * frac_covered(cov_state)).sum() / P_TOTAL})

sel = cand.loc[[s["idx"] for s in selected]].copy()
sel = sel.assign(**pd.DataFrame(selected).set_index("idx"))
sel = gpd.sjoin(sel, cty_p[["nombre", "geometry"]], predicate="within", how="left").drop(columns="index_right")
sel_ll = sel.to_crs("EPSG:4326")
sel["lat"], sel["lon"] = sel_ll.geometry.y.round(4), sel_ll.geometry.x.round(4)
greedy_tbl = sel[["iteracion", "nombre", "lat", "lon", "pob_adicional", "pct_cobertura_acumulada"]].set_index("iteracion")
print(f"Cobertura actual ({R_MAP} km): {base_pct:.2f} %")
print(f"Cobertura con {P_NEW} nuevos hospitales: {greedy_tbl.pct_cobertura_acumulada.iloc[-1]:.2f} % "
      f"(+{greedy_tbl.pct_cobertura_acumulada.iloc[-1] - base_pct:.2f} p.p., "
      f"{greedy_tbl.pob_adicional.sum():,.0f} personas adicionales)")
greedy_tbl
cty_p["frac_final"] = frac_covered(cov_state)
fig, ax = plt.subplots(figsize=(10, 12))
cty_p.plot(ax=ax, column="frac_final", cmap="RdBu", vmin=0, vmax=1, edgecolor="#9a9a9a", linewidth=0.5,
           legend=True, legend_kwds={"label": "Fracción del área del condado cubierta", "shrink": 0.5})
gpd.GeoSeries([cov25.intersection(state_poly)], crs=CRS_PROJ).boundary.plot(ax=ax, color="#1c5cab", lw=0.6, ls="--")
cand.plot(ax=ax, color="#555555", markersize=8, zorder=3)
gpd.GeoSeries(sel.geometry.buffer(S), crs=CRS_PROJ).boundary.plot(ax=ax, color=CAT[1], linewidth=2.2, zorder=4)
hosp_p.plot(ax=ax, color="black", markersize=8, zorder=4)
sel.plot(ax=ax, color=CAT[1], marker="*", markersize=380, edgecolor="black", zorder=5)
for _, r in sel.iterrows():
    ax.annotate(f"{r.iteracion}. {r.nombre}\n+{r.pob_adicional:,.0f} hab.", xy=(r.geometry.x, r.geometry.y),
                xytext=(10, 10), textcoords="offset points", fontsize=10, fontweight="bold",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")], zorder=6)
state_p.boundary.plot(ax=ax, color="#222222", linewidth=1.0)
ax.legend(handles=[
    Line2D([], [], color="#1c5cab", ls="--", label=f"Cobertura actual ({R_MAP} km)"),
    Line2D([], [], marker="o", color="black", ls="", markersize=4, label="Hospital existente"),
    Line2D([], [], marker="o", color="#555555", ls="", markersize=4, label=f"Candidatos (grilla 50 km, n={len(cand)})"),
    Line2D([], [], marker="*", color=CAT[1], markeredgecolor="black", ls="", markersize=16,
           label=f"Nuevos hospitales propuestos (buffer {R_MAP} km)")], loc="lower right")
add_north_and_scale(ax)
ax.set_title(f"MCLP voraz: {P_NEW} nuevos hospitales — cobertura {base_pct:.1f} % → "
             f"{greedy_tbl.pct_cobertura_acumulada.iloc[-1]:.1f} %")
ax.set_axis_off()
plt.tight_layout()
plt.show()
import networkx as nx
import osmnx as ox
from pathlib import Path
from IPython.display import Markdown

vul_con_hosp = vul[vul["hospitales"] > 0].nlargest(3, "V")
rows = []
for _, county in vul_con_hosp.iterrows():
    candidates = hosp_p[hosp_p["fips_condado"] == county["fips"]]
    hospital = candidates.loc[[candidates["camas_total"].idxmax()]].copy()
    hospital["condado_vulnerable"] = county["nombre"]
    hospital["indice_vulnerabilidad"] = county["V"]
    rows.append(hospital)

hosp_iso = gpd.GeoDataFrame(pd.concat(rows, ignore_index=True), crs=CRS_PROJ)
hosp_iso[["condado_vulnerable", "nombre", "tipo", "camas_total", "indice_vulnerabilidad"]]

for i, hospital in hosp_ll.iterrows():
    print(f"{hospital['fips_condado']} {hospital.geometry.y} {hospital.geometry.x}")
