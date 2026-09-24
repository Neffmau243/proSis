"""Analiza un archivo .mdb (Microsoft Access / Jet) y reporta tipo, estructura y relaciones.

Uso:  python analyze_mdb.py [archivo.mdb]
Genera: esquema_completo.txt  (esquema tabla por tabla)
Requiere: pip install access_parser
"""
import io
import sys
import time
from collections import Counter, defaultdict

from access_parser import AccessParser, utils
from access_parser.parsing_primitives import parse_data_page_header

# --- nombres legibles para los tipos de dato de Jet ---
TYPE_NAMES = {}
for _name in dir(utils):
    if _name.startswith("TYPE_") and isinstance(getattr(utils, _name), int):
        TYPE_NAMES.setdefault(getattr(utils, _name), _name.replace("TYPE_", ""))

OBJ_TYPES = {
    1: "Tabla local", 2: "Relacion", 3: "Objeto", 4: "Tabla vinculada",
    5: "Consulta", 6: "Base de datos", 8: "Relacion", -32768: "Formulario",
    -32766: "Informe", -32764: "Macro", -32761: "Modulo", -32758: "Modulo de clase",
}

JET_NAMES = {3: "Jet 3 (Access 97)", 4: "Jet 4 (Access 2000-2003)",
             5: "Jet 4 / ACE (Access 2007)", 2010: "ACE (Access 2010+)"}


def dump(path):
    db = AccessParser(path)
    out = io.StringIO()

    out.write("TIPO DE ARCHIVO\n")
    out.write("  Formato          : Microsoft Access, contenedor Jet (familia .mdb)\n")
    out.write(f"  Version JET      : {JET_NAMES.get(db.version, 'desconocida')}\n")
    out.write(f"  Tamano de pagina : {db.page_size} bytes (las paginas 4096 = Jet 4)\n")
    out.write(f"  Tamano archivo   : {len(db.db_data)} bytes ({len(db.db_data)/1048576:.1f} MiB)\n")
    out.write(f"  Paginas totales  : {len(db.db_data)//db.page_size}\n\n")

    # --- inventario de objetos segun MSysObjects ---
    msys = db.parse_table("MSysObjects")
    kinds = Counter()
    names_by_kind = defaultdict(list)
    if msys and msys.get("Name"):
        for name, typ in zip(msys["Name"], msys["Type"]):
            if name.startswith("MSys"):
                kinds["(sistema) MSys*"] += 1
                continue
            kind = OBJ_TYPES.get(typ, f"otro({typ})")
            kinds[kind] += 1
            names_by_kind[kind].append(name)

    out.write("CONTENIDO DEL CONTENEDOR (MSysObjects)\n")
    for kind, n in kinds.most_common():
        out.write(f"  {kind:<22}: {n}\n")
    for kind, names in names_by_kind.items():
        if kind != "Tabla local":
            out.write(f"  -- {kind}: {', '.join(sorted(names))}\n")
    out.write("\n")

    # --- esquema de cada tabla ---
    summary = []
    out.write("=" * 78 + "\nESQUEMA DETALLADO\n" + "=" * 78 + "\n\n")
    total_rows = 0
    for table_name in sorted(db.catalog):
        table = db.get_table(table_name)
        if table is None or table.columns is None:
            out.write(f"== {table_name}: no se pudo leer la definicion\n\n")
            continue
        pages = getattr(table.table, "linked_pages", [])
        rows = 0
        for page in pages:
            try:
                rows += parse_data_page_header(page, version=db.version).record_count
            except Exception:
                pass
        total_rows += rows
        summary.append((table_name, rows, len(table.columns), table.primary_keys))

        out.write(f"== {table_name}   filas={rows}  paginas={len(pages)}  campos={len(table.columns)}\n")
        if table.primary_keys:
            out.write(f"   PK: {', '.join(table.primary_keys)}\n")
        for _i, col in sorted(table.columns.items()):
            tname = TYPE_NAMES.get(col.type, f"TIPO_{col.type}")
            size = getattr(col.various, "col_size", None)
            flags = []
            fixed = getattr(col.various, "fixed_length", None)
            if fixed is not None:
                flags.append("fijo" if fixed else "var")
            if size:
                flags.append(f"size={size}")
            out.write(f"   - {col.col_name_str}: {tname}{'  [' + ', '.join(flags) + ']' if flags else ''}\n")
        out.write("\n")
    out.write(f"TOTAL filas aprox (todas las tablas): {total_rows}\n")

    with open("esquema_completo.txt", "w", encoding="utf-8") as f:
        f.write(out.getvalue())

    # --- resumen por consola ---
    print(out.getvalue().split("=" * 78)[0])
    print("Tablas por volumen:")
    for name, rows, ncols, pk in sorted(summary, key=lambda x: -x[1])[:20]:
        print(f"  {name:<32} filas={rows:<7} campos={ncols:<4} PK={','.join(pk) or '-'}")
    print(f"\ntablas: {len(summary)}   filas totales ~ {total_rows}")
    print("esquema completo escrito en esquema_completo.txt")
    return db, summary


def relations(db, base_table, base_key, child_table, child_key):
    """Comprueba integridad referencial entre dos tablas."""
    data = {}
    for name in (base_table, child_table):
        t0 = time.time()
        data[name] = db.get_table(name).parse()
        print(f"{name}: {len(next(iter(data[name].values())))} filas en {time.time()-t0:.0f}s")

    ids = {x for x in data[base_table][base_key] if x is not None}
    children = {x for x in data[child_table][child_key] if x is not None}
    print(f"{child_table}.{child_key} distintos : {len(children)}")
    print(f"  huerfanos (no existen en {base_table}.{base_key}): {len(children - ids)}")
    print(f"  {base_table} sin hijos: {len(ids - children)}")
    return data[child_table]


if __name__ == "__main__":
    db, _ = dump(sys.argv[1] if len(sys.argv) > 1 else "Data_base.mdb")

    for name in ("EESS", "Z_01", "Especialidades"):
        if name in db.catalog:
            data = db.get_table(name).parse()
            keys = list(data)
            print(f"\n--- muestra de {name}: {keys}")
            for i in range(min(3, len(data[keys[0]]))):
                print("   ", {k: data[k][i] for k in keys})

    if "Pacientes" in db.catalog and "Atencion" in db.catalog:
        print()
        ate = relations(db, "Pacientes", "Codclie", "Atencion", "Idcliente")
        fechas = sorted(f for f in ate["Fecha_atencion"] if f)
        print(f"\nAtenciones con fecha: {len(fechas)}  rango: {fechas[0]} .. {fechas[-1]}")
        print("Codigo_1 mas frecuentes:")
        for code, n in Counter(c for c in ate["Codigo_1"] if c).most_common(10):
            print(f"   {code}: {n}")
