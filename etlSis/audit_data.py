"""Auditoria de calidad de datos de Data_base.mdb (previa al ETL)."""
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

from access_parser import AccessParser

db = AccessParser("Data_base.mdb")


def load(name):
    table = db.get_table(name)
    return table.primary_keys, table.parse()


def norm(v):
    """Normaliza para comparar: minusculas, sin acentos, sin espacios duplicados."""
    if v is None:
        return None
    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def fill(data, label=""):
    n = len(next(iter(data.values())))
    print(f"  {'campo':<26} {'vacios':>8} {'nulos':>7} {'distintos':>10}")
    for f, vals in data.items():
        none = sum(1 for v in vals if v is None)
        empty = sum(1 for v in vals if isinstance(v, str) and not v.strip())
        uniq = len({v for v in vals if v not in (None, "") and not (isinstance(v, str) and not v.strip())})
        flag = ""
        if none + empty == n:
            flag = "  <== SIEMPRE VACIO"
        elif none + empty > n * 0.9:
            flag = "  <== ~vacio"
        print(f"  {f:<26} {empty:>8} {none:>7} {uniq:>10}{flag}")
    print()


def dup_report(data, keys, label):
    idx = defaultdict(list)
    for i in range(len(next(iter(data.values())))):
        idx[tuple(norm(data[k][i]) for k in keys)].append(i)
    dups = {k: v for k, v in idx.items() if len(v) > 1 and any(k)}
    print(f"  {label}: {len(idx)} grupos / {len(dups)} con duplicado")
    for k, v in list(sorted(dups.items(), key=lambda x: -len(x[1])))[:5]:
        print(f"      x{len(v)} -> {k}  (filas {v[:6]})")


# ============================ PACIENTES ============================
print("=" * 78)
print("PACIENTES / Pacientes_ref")
print("=" * 78)
pk, pac = load("Pacientes")
n = len(pac["Codclie"])
print(f"filas={n}  PK={pk}\n")
fill(pac)

print("  -- llaves de negocio --")
for k in ("Codclie", "Historia_Clinica", "N°_DNI", "Historia_Familiar"):
    vals = pac[k]
    nonempty = [v for v in vals if v not in (None, "") and str(v).strip()]
    print(f"  {k:<20} con dato={len(nonempty):<7} distintos={len(set(map(norm, nonempty)))}")
dup_report(pac, ["N°_DNI"], "  duplicados por DNI")
dup_report(pac, ["Historia_Clinica"], "  duplicados por Historia_Clinica")
dup_report(pac, ["Apellido_Paterno", "Apellido_Materno", "Primer_Nombre", "Fecha_nacimiento"],
           "  duplicados por nombre+fecha_nac")

print("\n  -- distribuciones --")
for f in ("Sexo", "Seguro", "Condicion", "Establecimiento", "Distrito", "Tipo"):
    if f in pac:
        c = Counter(norm(v) for v in pac[f] if v not in (None, "") and str(v).strip())
        print(f"  {f} ({len(c)} distintos): {c.most_common(8)}")

print("\n  -- fechas --")
hoy = datetime(2026, 9, 21)
for campo in ("Fecha_nacimiento", "Fecha_inscripcion"):
    malas = [f for f in pac[campo] if not isinstance(f, datetime)]
    fechas = [f for f in pac[campo] if isinstance(f, datetime)]
    print(f"  {campo}: {len(fechas)} fechas validas, {len(malas)} invalidas/no-fecha")
    if malas:
        print(f"      ejemplos de valor invalido: {Counter(map(repr, malas)).most_common(4)}")
    if fechas:
        print(f"      min={min(fechas)} max={max(fechas)}")
        print(f"      futuras (> hoy)={sum(1 for f in fechas if f > hoy)}"
              f"  antes de 1900={sum(1 for f in fechas if f.year < 1900)}"
              f"  antes de 2000={sum(1 for f in fechas if f.year < 2000)}")

print("\n  -- campos Anexo: se usan? --")
anexos = {f: sum(1 for v in pac[f] if v not in (None, "") and str(v).strip())
          for f in pac if f.startswith("Anexo")}
print(f"  total campos Anexo: {len(anexos)}  con algun dato: {sum(1 for v in anexos.values() if v)}")
print(f"  {anexos}")
ej = [i for i, v in enumerate(pac["Anexo1"]) if v not in (None, "")][:5]
for i in ej:
    print(f"    fila {i}: Anexo1..6 = {[pac[f'Anexo{j}'][i] for j in range(1, 7)]}")

# ============================ ATENCION ============================
print("\n" + "=" * 78)
print("ATENCION")
print("=" * 78)
pk, ate = load("Atencion")
n = len(ate["Id"])
print(f"filas={n}  PK={pk}\n")
fill(ate)

print("  -- llaves / fechas --")
print(f"  Id distintos        : {len(set(ate['Id']))}")
print(f"  Fecha_atencion min/max: {min(f for f in ate['Fecha_atencion'] if f)} .. {max(f for f in ate['Fecha_atencion'] if f)}")
fa = Counter(str(v) for v in ate["Fecha_atendido"])
print(f"  Fecha_atendido (TEXT) distintos={len(fa)} ejemplo: {fa.most_common(5)}")
print(f"  Hora1 (TEXT) ejemplo: {Counter(str(v) for v in ate['Hora1']).most_common(4)}")
print(f"  Hora2 (INT32) rango: {min(v for v in ate['Hora2'] if v is not None)} .. {max(v for v in ate['Hora2'] if v is not None)}")
dup_report(ate, ["Idcliente", "Fecha_atencion"], "  duplicados por (Idcliente, Fecha_atencion)")
dup_report(ate, ["Id"], "  duplicados por Id")

print("\n  -- medidas como texto: son numericas? --")
for f in ("Edad", "Peso", "Talla", "PE", "TE", "PT", "Sistolica", "Distolica", "Historia_Clinica"):
    vals = [v for v in ate[f] if v not in (None, "") and str(v).strip()]
    malos = [v for v in vals if not re.fullmatch(r"\d{1,3}([.,]\d+)?", str(v).strip())]
    print(f"  {f:<18} con dato={len(vals):<7} no numericos={len(malos):<6} ejemplos={list(Counter(map(str, malos)).items())[:5]}")

print("\n  -- codigos de atencion --")
cod_cols = [f for f in ate if f.startswith("Codigo_")]
usados = {f: sum(1 for v in ate[f] if v not in (None, "") and str(v).strip()) for f in cod_cols}
print(f"  {usados}")
prefijos = Counter()
for f in cod_cols:
    for v in ate[f]:
        if v and str(v).strip():
            m = re.match(r"([A-Za-z_]+)", str(v).strip())
            prefijos[m.group(1).upper() if m else "(sin prefijo)"] += 1
print(f"  prefijos (servicio): {prefijos.most_common(12)}")
print(f"  distintos Codigo_1  : {len({str(v).strip() for v in ate['Codigo_1'] if v and str(v).strip()})}")

print("\n  -- catalogos de atencion --")
for f in ("Consultorio", "Profesional", "Historia_Clinica"):
    c = Counter(norm(v) for v in ate[f] if v not in (None, "") and str(v).strip())
    print(f"  {f}: {len(c)} distintos -> {c.most_common(6)}")

# ============================ CATALOGOS ============================
print("\n" + "=" * 78)
print("CATALOGOS")
print("=" * 78)
for name in ("EESS", "EESS_HF", "EESS_PS", "EESS_PS_SESMA", "EESS_SIS", "Microred", "Provincia",
             "Profesionales", "Operarios", "Especialidades", "Especialidades2", "Especialidades3",
             "Certificado", "Z_01", "Z_02", "Z_08", "Z_29", "Z_01_2018", "Z_01_2019"):
    if name not in db.catalog:
        continue
    pk, d = load(name)
    n = len(next(iter(d.values())))
    print(f"  {name:<16} filas={n:<5} PK={pk or '-'} campos={list(d)}")
    for f, vals in d.items():
        if isinstance(vals[0], str):
            vals_n = [norm(v) for v in vals if v not in (None, "") and str(v).strip()]
            print(f"      {f}: distintos={len(set(vals_n))} de {len(vals)} -> {sorted(set(vals_n))[:4]}")

# ============================ Z_* : son versiones? ============================
print("\n  -- Z_* vs Z_01 (comparacion de contenido) --")
z01 = load("Z_01")[1]
conj01 = {(norm(a), norm(b)) for a, b in zip(z01["Lugar"], z01["Clave"])}
for name in sorted(t for t in db.catalog if t.startswith("Z_")):
    d = load(name)[1]
    c = {(norm(a), norm(b)) for a, b in zip(d["Lugar"], d["Clave"])}
    print(f"    {name:<12} filas={len(d['Lugar']):<5} igual a Z_01: {c == conj01}  solape={len(c & conj01)}")
