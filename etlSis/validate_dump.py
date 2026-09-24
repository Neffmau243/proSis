"""Valida el dump: cada INSERT debe tener la misma cantidad de columnas y valores."""
import glob
import re
import sys
from collections import Counter

RE_INSERT = re.compile(r"INSERT INTO `([^`]+)` \(([^)]*)\) VALUES\s*", re.S)


def split_tuples(texto):
    """Devuelve la lista de tuplas de valores respetando comillas escapadas."""
    tuplas, campos, campo = [], None, None
    profundidad, i, n = 0, 0, len(texto)
    while i < n:
        c = texto[i]
        if c == "(":
            profundidad += 1
            if profundidad == 1:
                campos, campo = [], None
            i += 1
            continue
        if c == ")":
            profundidad -= 1
            if profundidad == 0:
                campos.append(campo if campo is not None else "")
                tuplas.append(campos)
                campos, campo = None, None
            i += 1
            continue
        if profundidad != 1:
            i += 1
            continue
        if c == "'":
            j = i + 1
            while j < n:
                if texto[j] == "\\":
                    j += 2
                    continue
                if texto[j] == "'":
                    if j + 1 < n and texto[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            campo = texto[i:j + 1]
            i = j + 1
            continue
        if c == ",":
            campos.append(campo if campo is not None else "")
            campo = None
            i += 1
            continue
        campo = (campo or "") + c
        i += 1
    return tuplas


def main():
    totales = Counter()
    errores = []
    sentencias = 0
    for ruta in sorted(glob.glob("dump/*.sql")):
        texto = open(ruta, encoding="utf-8").read()
        pos = 0
        while True:
            m = RE_INSERT.search(texto, pos)
            if not m:
                break
            tabla = m.group(1)
            ncols = len([c for c in m.group(2).split(",") if c.strip()])
            fin = texto.find(";\n", m.end())
            if fin == -1:
                fin = len(texto)
            cuerpo = texto[m.end():fin]
            tuplas = split_tuples(cuerpo)
            sentencias += 1
            for k, t in enumerate(tuplas):
                totales[tabla] += 1
                if len(t) != ncols:
                    errores.append(f"{ruta} {tabla}: fila {k} tiene {len(t)} valores, se esperaban {ncols}")
            pos = fin
        if texto.count("CREATE TABLE") and "stg_" in ruta:
            totales["(CREATE TABLE staging)"] = texto.count("CREATE TABLE")

    print(f"sentencias INSERT revisadas: {sentencias}")
    print(f"tablas destino: {len([t for t in totales if not t.startswith('(')])}")
    print(f"filas totales: {sum(v for t, v in totales.items() if not t.startswith('('))}")
    for t, n in sorted(totales.items()):
        print(f"  {t:<34} {n}")
    if errores:
        print(f"\nERRORES ({len(errores)}):")
        for e in errores[:20]:
            print("  " + e)
        return 1
    print("\nOK: todas las sentencias INSERT tienen aridad consistente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
