"""Cuantifica corrupcion de texto, valores centinela y solapamiento de catalogos."""
import re
import unicodedata
from collections import Counter, defaultdict

from access_parser import AccessParser

db = AccessParser("Data_base.mdb")

SOSPECHOSOS = ("Co", "Cc", "Cs", "Cf")  # uso privado, control, surrogates, formato


def scan(name):
    t = db.get_table(name)
    d = t.parse()
    n = len(next(iter(d.values())))
    print(f"--- {name} ({n} filas)")
    for f, vals in d.items():
        tipos = Counter()
        ejemplos = {}
        for v in vals:
            if not isinstance(v, str) or not v.strip():
                continue
            if any(unicodedata.category(c) in SOSPECHOSOS for c in v):
                tipos["control/uso-privado/BOM"] += 1
                ejemplos.setdefault("control/uso-privado/BOM", repr(v))
            if "\ufffd" in v:
                tipos["char reemplazo U+FFFD"] += 1
                ejemplos.setdefault("char reemplazo U+FFFD", repr(v))
            if re.search(r"[^\x00-\x7f]{3,}", v) is None and re.search(r"[\u00c2-\u00c3][\u0080-\u00bf]", v):
                tipos["posible mojibake UTF8->latin1"] += 1
                ejemplos.setdefault("posible mojibake", repr(v))
            if re.search(r"[^\w\s\.,;:\-\(\)/°'\"#%&+*=<>\[\]{}$@!?¡¿ñÑáéíóúÁÉÍÓÚüÜ]", v):
                tipos["otros no imprimibles"] += 1
                ejemplos.setdefault("otros no imprimibles", repr(v))
        if tipos:
            print(f"    {f}: {dict(tipos)}")
            for k, v in ejemplos.items():
                print(f"        {k}: {v}")
        # valores centinela repetidos
        c = Counter(v.strip() for v in vals if isinstance(v, str) and v.strip())
        cent = {k: v for k, v in c.items() if len(k) <= 3 and k.upper() in
                ("NN", "XXX", "XX", "X", "-", ".", "0", "NNN", "NNNNNNNN", "S/N", "NINGUNO", "NINGUNA") and v > 5}
        if cent:
            print(f"    {f}: centinelas {cent}")


for t in ("Pacientes", "Pacientes_ref", "Atencion", "Profesionales", "Operarios", "EESS", "Microred"):
    scan(t)

# ---------- DNI ----------
print("\n=== DNI en Pacientes ===")
pac = db.get_table("Pacientes").parse()
dnis = [v.strip() for v in pac["N°_DNI"] if isinstance(v, str) and v.strip()]
malos = [d for d in dnis if not re.fullmatch(r"\d{8}", d)]
print(f"  con dato={len(dnis)}  formato != 8 digitos={len(malos)}")
print(f"  mas repetidos (basura): {Counter(malos).most_common(8)}")
print(f"  LEN invalido: {Counter(len(d) for d in malos).most_common(8)}")

print("\n=== DNI en Profesionales ===")
pro = db.get_table("Profesionales").parse()
dnis_p = [v.strip() for v in pro["DNI"] if isinstance(v, str) and v.strip()]
print(f"  {sum(1 for d in dnis_p if not re.fullmatch(r'\\d{8}', d))} de {len(dnis_p)} con formato invalido")

# ---------- fechas ----------
print("\n=== Fechas (llegan como texto desde Access) ===")


def parse_fecha(v):
    if not isinstance(v, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    return tuple(map(int, m.groups())) if m else None


for f in ("Fecha_nacimiento", "Fecha_inscripcion"):
    vals = pac[f]
    sin = sum(1 for v in vals if v in ("(Empty Date)", "(Invalid Date)", None, ""))
    fech = [x for x in map(parse_fecha, vals) if x]
    y1 = sum(1 for a, m, d in fech if m == 1 and d == 1)
    fut = sum(1 for a, m, d in fech if (a, m, d) > (2026, 9, 21))
    viejos = sum(1 for a, m, d in fech if a < 1900)
    print(f"  {f}: total={len(vals)} sin fecha={sin} 1-enero={y1} ({y1*100//max(len(fech),1)}%) futuras={fut} antes1900={viejos}")

print("\n=== Edad (Atencion) es texto libre ===")
ate = db.get_table("Atencion").parse()
print(f"  {Counter(ate['Edad']).most_common(3)}")

# ---------- catalogos Z_* ----------
print("\n=== Catalogos Z_* : Clave (ubigeo) util o rota? ===")
utiles = rotas = 0
for name in sorted(t for t in db.catalog if t.startswith("Z_")):
    d = db.get_table(name).parse()
    claves = [str(v).strip() for v in d["Clave"] if v not in (None, "")]
    reales = sum(1 for c in claves if re.fullmatch(r"\d{6,8}", c) and c not in ("00000001", "000001"))
    print(f"  {name:<12} filas={len(claves):<4} claves distintas={len(set(claves)):<4} ubigeo real={reales:<4} ejemplo={claves[:2]}")
    if reales:
        utiles += 1
    else:
        rotas += 1
print(f"  -> tablas con ubigeo real: {utiles}, con clave rota/constante: {rotas}")

# ---------- Localidad de Pacientes existe en los Z_*? ----------
print("\n=== Pacientes.Localidad vs catalogos Z_* ===")
lugares = set()
for name in sorted(t for t in db.catalog if t.startswith("Z_")):
    d = db.get_table(name).parse()
    lugares.update(str(v).strip().lower() for v in d["Lugar"] if v)
loc = Counter(str(v).strip().lower() for v in pac["Localidad"] if isinstance(v, str) and v.strip())
fuera = {k: v for k, v in loc.items() if k not in lugares}
print(f"  lugares en Z_*: {len(lugares)}   localidades distintas en Pacientes: {len(loc)}")
print(f"  localidades que NO existen en ningun Z_*: {len(fuera)} ({sum(fuera.values())} filas)")
print(f"  ejemplos: {list(fuera.items())[:6]}")
