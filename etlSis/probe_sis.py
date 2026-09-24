# -*- coding: utf-8 -*-
"""Rastrea que campos de Data_base.mdb corresponden al mundo SIS y como se enlazan."""
import re
import unicodedata
from collections import Counter

from access_parser import AccessParser

db = AccessParser("Data_base.mdb")


def kk(n):
    s = unicodedata.normalize("NFKD", str(n))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def t(nombre):
    return db.get_table(nombre).parse()


print("=" * 78)
print("1) CATALOGO DE PRESTACIONES SIS: valores de Atencion.Codigo_1 / 2 / 4 / 8")
print("=" * 78)
ate = t("Atencion")
cm = {kk(c): c for c in ate}
for campo in ("codigo1", "codigo2", "codigo4", "codigo8"):
    c = cm[campo]
    vals = Counter(v.strip() for v in ate[c] if isinstance(v, str) and v.strip())
    print(f"\n-- {c}  ({len(vals)} valores distintos, {sum(vals.values())} usos)")
    for v, n in vals.most_common(30):
        print(f"   {v:<28} {n}")

print()
print("=" * 78)
print("2) CAMPOS 'SIS' DENTRO DE Pacientes")
print("=" * 78)
pac = t("Pacientes")
cpm = {kk(c): c for c in pac}
for campo in ("arequipa040", "arequipa2", "arequipasis", "anexo1", "anexo2", "anexo3",
              "anexo4", "anexo5", "anexo6", "anexo7", "anexo17", "anexo18"):
    c = cpm.get(campo)
    if not c:
        print(f"  {campo}: (no existe)")
        continue
    vals = Counter(v for v in pac[c] if isinstance(v, str) and v.strip())
    print(f"\n-- {c}  ({len(vals)} distintos de {len(pac[c])} filas)")
    for v, n in vals.most_common(8):
        print(f"   {v[:70]!r:<60} {n}")

print()
print("=" * 78)
print("3) ESTRUCTURAS DE EXPORTACION AL SIS (Detalle_*)")
print("=" * 78)
for tabla in ("Detalle_Adultos", "Detalle_Niños", "Detalle_Mujeres_Gestantes"):
    if tabla not in db.catalog:
        continue
    d = t(tabla)
    n = len(next(iter(d.values())))
    print(f"\n-- {tabla} ({n} filas)")
    for i in range(n):
        fila = {c: d[c][i] for c in d}
        print("   " + " | ".join(f"{c}={v}" for c, v in fila.items() if v not in (None, "")))

print()
print("=" * 78)
print("4) CREDENCIALES Y CERTIFICADOS (puertas al SIS)")
print("=" * 78)
for tabla in ("EESS_Padron", "Certificado", "Certificado_Nro", "Atencion_certificado",
              "Pacientes_ErroresDeExportación", "EESS_HF", "Operarios"):
    if tabla not in db.catalog:
        continue
    d = t(tabla)
    n = len(next(iter(d.values())))
    print(f"\n-- {tabla} ({n} filas) campos={list(d)}")
    for i in range(min(n, 4)):
        print("   " + " | ".join(f"{c}={d[c][i]}" for c in d if d[c][i] not in (None, "")))

print()
print("=" * 78)
print("5) Z_01..Z_29 vs Provincia: son las localidades de cada distrito?")
print("=" * 78)
prov = t("Provincia")
pm = {kk(c): c for c in prov}
orden = [(prov[pm["codigo"]][i], prov[pm["distrito"]][i]) for i in range(len(prov[pm["codigo"]]))]
print(f"  Provincia tiene {len(orden)} distritos")
zs = sorted((x for x in db.catalog if re.fullmatch(r"Z_\d+", x)), key=lambda x: int(x[2:]))
ok = 0
for tabla in zs:
    d = t(tabla)
    dm = {kk(c): c for c in d}
    lugares = [v for v in d[dm["lugar"]] if v]
    num = int(tabla[2:])
    distrito = dict(orden).get(num, "?")
    coincide = any(str(distrito).upper()[:12] in str(l).upper() for l in lugares) if distrito != "?" else False
    ok += 1 if coincide else 0
    print(f"  {tabla:<7} codigo_legacy_vs_distrito={num:<3} distrito={str(distrito)[:26]:<28} "
          f"n_lugares={len(lugares):<4} coincide_nombre={coincide}")
print(f"  -> {ok}/{len(zs)} catalogos Z_* contienen un lugar con el nombre de su distrito")
