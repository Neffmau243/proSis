# -*- coding: utf-8 -*-
"""Informe: (A) estado real del seguro de los pacientes y (B) que quedo sin limpiar.

Usa los mismos primitivos del ETL (etl_mysql) y los catalogos ya generados en dump/,
para que los numeros correspondan exactamente a la base que se entrega.
"""
import re
from collections import Counter

from access_parser import AccessParser
from validate_dump import split_tuples
import etl_mysql as E

# ---------------------------------------------------------------- catalogos del dump
def unq(lit):
    lit = lit.strip()
    if lit == "NULL":
        return None
    if lit.startswith("'") and lit.endswith("'"):
        lit = lit[1:-1]
    return (lit.replace("\\\\", "\\").replace("\\n", "\n").replace("\\r", "\r").replace("''", "'"))


def catalogo(tabla, idx_norm):
    texto = open("dump/20_catalogos.sql", encoding="utf-8").read()
    mapa = {}
    for m in re.finditer(r"INSERT INTO `" + tabla + r"` \(([^)]*)\) VALUES\s*", texto):
        fin = texto.find(";\n", m.end())
        for t in split_tuples(texto[m.end():fin]):
            vals = [unq(v) for v in t]
            if len(vals) > idx_norm and vals[idx_norm]:
                mapa[vals[idx_norm]] = int(vals[0])
    return mapa


id_distrito = catalogo("cat_distrito", 3)
id_lugar = catalogo("cat_lugar", 5)
id_eess = catalogo("cat_establecimiento", 3)
id_seguro = catalogo("cat_seguro", 3)
id_cond = catalogo("cat_condicion", 2)

db = AccessParser("Data_base.mdb")
pac = db.get_table("Pacientes").parse()
cm = {E.kkey(c): c for c in pac}
col = lambda *a: next(pac[cm[E.kkey(x)]] for x in a if E.kkey(x) in cm)

seguro = col("Seguro")
sis_af = col("Arequipa_SIS")
areq2 = col("Arequipa_2")
anexo1 = col("Anexo1")
dni = col("N°_DNI")
sexo = col("Sexo")
hc = col("Historia_Clinica")
fnac = col("Fecha_nacimiento")
distrito = col("Distrito")
localidad = col("Localidad")
eess = col("Establecimiento")
cond = col("Condicion")
direccion = col("Dirección")
HF = col("Historia_Familiar")
n = len(hc)

print("=" * 78)
print("A) SEGURO DE LOS PACIENTES (Pacientes.Seguro, 73.209 filas)")
print("=" * 78)
grupos = {"SIS": 0, "SIN SEGURO": 0, "ESSALUD": 0, "SANIDAD/FFAA": 0, "OTROS": 0}
detalle = Counter()
for s in seguro:
    v = E.norm(s) or "(vacio)"
    detalle[v] += 1
    if v.startswith("s i s") or v.startswith("sis"):
        grupos["SIS"] += 1
    elif v in ("sin seguro", "ninguno"):
        grupos["SIN SEGURO"] += 1
    elif "essalud" in v:
        grupos["ESSALUD"] += 1
    elif "sanidad" in v or "ff aa" in v or "policia" in v or "militar" in v or "eps" in v:
        grupos["SANIDAD/FFAA"] += 1
    else:
        grupos["OTROS"] += 1
for k, v in sorted(grupos.items(), key=lambda x: -x[1]):
    print(f"  {k:<16} {v:>7}  ({v*100/n:.1f}%)")
print(f"\n  valores distintos en el origen: {len(detalle)}")
for v, c in detalle.most_common():
    print(f"    {v:<34} {c:>6}")

print("\n  -- coherencia: n de afiliacion SIS (Arequipa_SIS) --")
cross = Counter()
for s, a in zip(seguro, sis_af):
    es_sis = (E.norm(s) or "").startswith("s i s") or (E.norm(s) or "").startswith("sis")
    tiene = bool(a and str(a).strip())
    cross[("SIS" if es_sis else "NO SIS", "con n afiliacion" if tiene else "sin n afiliacion")] += 1
for k, v in cross.most_common():
    print(f"    {k[0]:<8} {k[1]:<20} {v:>6}")
print("    => SIS sin numero de afiliacion (dato incompleto):", cross[("SIS", "sin n afiliacion")])
print("    => con numero pero sin plan SIS (contradiccion):", cross[("NO SIS", "con n afiliacion")])
af = [str(a).strip() for a in sis_af if a and str(a).strip()]
print(f"    numeros de afiliacion: {len(af)} | distintos: {len(set(af))} | invalidos(no 8 digitos): "
      f"{sum(1 for a in af if not re.fullmatch(r'[0-9]{8}', a))}")
print(f"    numeros repetidos en varios pacientes: "
      f"{sum(1 for k, c in Counter(af).items() if c > 1)} valores")

print("\n  -- que son Arequipa_2 y Anexo1? (cruce con el seguro) --")
for nombre, serie in (("Arequipa_2", areq2), ("Anexo1", anexo1)):
    print(f"  {nombre}:")
    cruce = Counter()
    for s, v in zip(seguro, serie):
        cruce[((E.norm(s) or "vacio")[:22], (E.norm(v) or "vacio"))] += 1
    for (s, v), c in cruce.most_common(6):
        print(f"    seguro={s:<24} {nombre}={v:<12} {c}")

print()
print("=" * 78)
print("B) QUE QUEDO SIN LIMPIAR EN EL MODELO NUEVO (paciente)")
print("=" * 78)


def cuenta(valores, valido, motivo):
    malos = [v for v in valores if not valido(v)]
    return len(malos), motivo


filas = []
sin_sexo = sum(1 for v in sexo if E.parse_sexo(E.limpio(v)[0]) is None)
sin_doc = sum(1 for v in dni if E.parse_documento(E.limpio(v)[0])[0] == "SIN_DOCUMENTO")
libreta = sum(1 for v in dni if E.parse_documento(E.limpio(v)[0])[0] == "LIBRETA")
sin_hc = sum(1 for v in hc if not E.limpio(v)[0])
sin_fnac = sum(1 for v in fnac if E.parse_fecha(v)[0] is None)
sin_distrito = sum(1 for v in distrito if not E.limpio(v)[0] or E.norm(E.limpio(v)[0]) not in id_distrito)
sin_lugar = sum(1 for v in localidad if not E.limpio(v)[0] or E.norm(E.limpio(v)[0]) not in id_lugar)
sin_eess = sum(1 for v in eess if not E.limpio(v)[0] or E.norm(E.limpio(v)[0]) not in id_eess)
sin_seguro = sum(1 for v in seguro if not E.limpio(v)[0] or E.norm(E.limpio(v)[0]) not in id_seguro)
sin_cond = sum(1 for v in cond if not E.limpio(v)[0] or E.norm(E.limpio(v)[0]) not in id_cond)
sin_dir = sum(1 for v in direccion if not E.limpio(v)[0])
corruptas = sum(1 for v in sexo if E.corrupto(v))
hf_guion = sum(1 for v in HF if E.limpio(v)[0] == "-")
placeholder = sum(1 for v in col("Fecha_inscripcion")
                  if (lambda d: d and (d.year, d.month, d.day) == (2016, 1, 1))(E.parse_fecha(v)[0]))

tabla = [
    ("sexo", sin_sexo, "corrupto (9) o vacio (3): el dato no existe en el origen"),
    ("numero_documento", sin_doc, f"vacio/nulo (18.224) + centinela (583) + formato (967); {libreta} quedan como LIBRETA"),
    ("historia_clinica", sin_hc, "no hay llave de negocio"),
    ("fecha_nacimiento", sin_fnac, "(Empty Date)/(Invalid Date)/futura"),
    ("distrito_id", sin_distrito, "texto vacio o que no matchea el catalogo Provincia"),
    ("lugar_id", sin_lugar, "texto libre que no existe en ningun Z_*"),
    ("establecimiento_id", sin_eess, "nombre no resoluble en EESS/EESS_PS/datos"),
    ("seguro_id", sin_seguro, "vacio o valor fuera de catalogo"),
    ("condicion_id", sin_cond, "vacio o valor fuera de catalogo"),
    ("direccion", sin_dir, "vacia"),
]
print(f"  {'campo':<20} {'sin dato':>9} {'%':>6}  motivo")
for campo, c, motivo in tabla:
    print(f"  {campo:<20} {c:>9} {c*100/n:>5.1f}%  {motivo}")
print(f"\n  Otras marcas de calidad:")
print(f"    fecha_inscripcion_placeholder (2016-01-01)  {placeholder:>9}  {placeholder*100/n:>5.1f}%")
print(f"    historia_familiar = '-' (centinela)        {hf_guion:>9}")
print(f"    filas con alguna celda corrupta            {corruptas:>9}  (solo Sexo)")
