#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL  Data_base.mdb (Microsoft Access / Jet 4)  ->  MySQL 8
==========================================================
Genera un dump SQL ejecutable (no necesita driver de MySQL ni servidor en esta
maquina). Fases:

  0) recon      : lee Access, detecta valores sucios/duplicados y decide catalogos
  1) staging    : copia 1:1 de las tablas de origen (auditoria, nada se pierde)
  2) catalogos  : dimensiones normalizadas (distrito, eess, especialidad, lugar...)
  3) pacientes  : padron unico con documento/fechas normalizados + EAV de anexos
  4) atenciones : una fila por atencion + explosion de Codigo_1..15
  5) formatos   : fua / certificado / referencia
  6) config     : configuracion heredada y plantillas (JSON)
  7) calidad    : dq_rechazo, paciente_duplicado, etl_run

Reglas de limpieza (nada se descarta en silencio, todo lo dudoso va a dq_rechazo):
  R1_CELDA_CORRUPTA   bytes rotos (CJK/PUA/BOM) -> NULL + registro
  R2_DNI_CENTINELA    NN/nnnnnnnn/XXX...        -> NULL + registro
  R3_DOCUMENTO_FORMATO no tiene 6-8 digitos     -> NULL + registro
  R4_HC_DUPLICADA     Historia_Clinica repetida -> paciente_duplicado
  R5_CODCLIE_DUPLICADO/ R6_DNI_DUPLICADO/ R7_NOMBRE_FECHA_DUPLICADO
  R8_FECHA_INVALIDA   (Empty/Invalid Date)      -> NULL + registro
  R9_MEDIDA_FUERA_RANGO peso/talla/presion      -> NULL + registro
  R10_SEXO_NO_MAPEABLE / R11_ETAPA_DESCONOCIDA
  R12_FECHA_INSCRIPCION_PLACEHOLDER (2016-01-01, 62% del padron) -> se conserva marcada
  R13_ATENCION_HUERFANA paciente inexistente    -> se carga con paciente_id NULL
  R14_CATALOGO_NO_RESUELTO nombre no matchea    -> se guarda el texto crudo
  R15_LEGADO_ERROR_EXPORTACION (tabla Access Pacientes_ErroresDeExportacion)

Uso:
  python etl_mysql.py --mdb Data_base.mdb --out dump [--staging core|all|none] [--limit N]
Luego:
  cat dump/*.sql | mysql -u root -p
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime

from access_parser import AccessParser

ETL_VERSION = "1.0.0"
ORIGEN = "Data_base.mdb"

# --------------------------------------------------------------------------
# utilidades de texto
# --------------------------------------------------------------------------
def kkey(name):
    """Nombre de columna comparable: sin acentos, sin simbolos, en minusculas.
    'N°_DNI' -> 'ndni' ; 'Dirección' -> 'direccion'"""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def norm(v):
    """Normaliza un valor para comparar/unificar catalogos."""
    if v is None:
        return None
    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u00a0", " ").replace("\ufeff", "")
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).strip().lower()
    return re.sub(r"\s+", " ", s)


CAT_PERMITIDAS = {"Po", "Pd", "Pi", "Pf", "Ps", "Pe", "Sm", "Sc", "So", "Zs"}


def corrupto(v):
    """Heuristica de celdas con bytes rotos (se ve como texto CJK/PUA/BOM)."""
    if not isinstance(v, str):
        return False
    for ch in v:
        cat = unicodedata.category(ch)
        if cat in ("Co", "Cs", "Cf"):
            return True
        if ord(ch) >= 0x2000 and cat not in CAT_PERMITIDAS:
            return True
    return False


def limpio(v):
    """Devuelve (valor_limpio, estaba_corrupto). Corrupto -> None."""
    if v is None:
        return None, False
    if not isinstance(v, str):
        return v, False
    if corrupto(v):
        return None, True
    s = v.replace("\ufeff", "").strip()
    return (s if s else None), False


def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (datetime, date)):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    s = str(v)
    s = (s.replace("\\", "\\\\").replace("'", "''")
          .replace("\n", "\\n").replace("\r", "\\r").replace("\x00", "").replace("\x1a", ""))
    return "'" + s + "'"


def json_val(obj):
    return sql_val(json.dumps(obj, ensure_ascii=False, default=str))


def parse_fecha(v):
    """'(Empty Date)' / '(Invalid Date)' / '2001-01-01 00:00:00' -> (date|None, motivo)"""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, "vacio"
    if isinstance(v, (datetime, date)):
        return (v.date() if isinstance(v, datetime) else v), None
    s = str(v).strip()
    if s.startswith("("):
        return None, s
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None, "formato:" + s[:20]
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), None
    except ValueError:
        return None, "fecha inexistente:" + s[:20]


def parse_fecha_hora(fecha_str, hora_str, hora_int):
    d, _ = parse_fecha(fecha_str)
    if d is None:
        return None
    hh, mm, ss = 0, 0, 0
    if isinstance(hora_str, str):
        m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", hora_str.strip())
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            ss = int(m.group(3) or 0)
    if hh == 0 and isinstance(hora_int, int) and 0 <= hora_int <= 23:
        hh = hora_int
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return datetime(d.year, d.month, d.day)
    return datetime(d.year, d.month, d.day, hh, mm, ss)


def parse_num(v, lo, hi, dec=None):
    """Numero dentro de rango, o None. '0147'->147 ; '30.'->30 ; '215,018.86'->None"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        n = float(v)
    else:
        s = str(v).strip().replace("\\", "")
        if not re.fullmatch(r"-?\d+(?:[.,]\d+)?", s):
            return None
        s = s.replace(",", ".")
        try:
            n = float(s)
        except ValueError:
            return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    if not (lo <= n <= hi):
        return None
    return round(n, dec) if dec is not None else n


EDAD_RE = re.compile(r"(\d+)\s*a[nñ]os?\s*,\s*(\d+)\s*mes(?:es)?\s*y\s*(\d+)\s*d[ií]as?", re.I)


def parse_edad(v):
    if isinstance(v, str):
        m = EDAD_RE.search(v)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None, None, None


SEXO_MAP = {"femenino": "F", "f": "F", "femenina": "F", "mujer": "F",
            "masculino": "M", "m": "M", "masculino ": "M", "hombre": "M", "varon": "M"}


def parse_sexo(v):
    if not isinstance(v, str):
        return None
    return SEXO_MAP.get(norm(v))


CENTINELAS_DOC = {"nn", "nnn", "nnnnnn", "nnnnnnnn", "nnnnnnnnn", "x", "xx", "xxx",
                  "xxxx", "xxxxxx", "xxxxxxxx", "xxxxxxx", "sn", "s n", "sin documento",
                  "0", "0000", "00000000", "-", ".", "no", "si"}


def parse_documento(v):
    """-> (tipo, numero)  DNI=8 digitos, LIBRETA=6-7 (carnes/libretas antiguas)"""
    if not isinstance(v, str) or not v.strip():
        return "SIN_DOCUMENTO", None
    s = v.strip().replace(" ", "").replace("-", "")
    if norm(s) in CENTINELAS_DOC or not s.isdigit():
        return "SIN_DOCUMENTO", None
    if len(s) == 8:
        return "DNI", s
    if 6 <= len(s) <= 7:
        return "LIBRETA", s
    return "SIN_DOCUMENTO", None


# etapa de vida / estado gestacional derivados de Condicion
ETAPA_MAP = [
    (re.compile(r"reci[eé]n nacido|neonat", re.I), "NINO"),
    (re.compile(r"ni[nñ]o|infante|menor de", re.I), "NINO"),
    (re.compile(r"adolescente", re.I), "ADOLESCENTE"),
    (re.compile(r"joven", re.I), "JOVEN"),
    (re.compile(r"adulto mayor|anciano|geronte", re.I), "ADULTO_MAYOR"),
    (re.compile(r"adulto", re.I), "ADULTO"),
]
GEST_MAP = [
    (re.compile(r"puerper", re.I), "PUERPERA"),
    (re.compile(r"lactan", re.I), "LACTANTE"),
    (re.compile(r"no gestante|no embarazada", re.I), "NO_GESTANTE"),
    (re.compile(r"gestante|embaraz", re.I), "GESTANTE"),
]


def deriva_condicion(nombre):
    etapa = gest = None
    if nombre:
        for rx, v in ETAPA_MAP:
            if rx.search(nombre):
                etapa = v
                break
        for rx, v in GEST_MAP:
            if rx.search(nombre):
                gest = v
                break
    return etapa, gest


# --------------------------------------------------------------------------
# escritores de SQL
# --------------------------------------------------------------------------
class SqlFile:
    """Acumula INSERTs y escribe el archivo al final (permite ordenar por FKs)."""

    def __init__(self, path, cabecera=None):
        self.path = path
        self.buf = []
        self.rows = Counter()
        if cabecera:
            self.buf.append(cabecera)

    def insert(self, tabla, cols, filas, batch=400):
        filas = list(filas)
        if not filas:
            return
        col_sql = ", ".join("`" + c + "`" for c in cols)
        for i in range(0, len(filas), batch):
            trozo = filas[i:i + batch]
            vals = ",\n  ".join("(" + ", ".join(sql_val(v) for v in fila) + ")" for fila in trozo)
            self.buf.append(f"INSERT INTO `{tabla}` ({col_sql}) VALUES\n  {vals};")
        self.rows[tabla] += len(filas)

    def raw(self, texto):
        self.buf.append(texto)

    def flush(self):
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write("SET NAMES utf8mb4;\nSET SESSION sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION';\n")
            f.write("\n".join(self.buf))
            f.write("\n")
        return sum(self.rows.values())


class Dq:
    """Registro de todo lo dudoso."""

    def __init__(self, sqlfile):
        self.file = sqlfile
        self.rows = []
        self.reglas = Counter()
        self.por_tabla = Counter()

    def add(self, tabla, fila, clave, regla, detalle="", raw=None):
        self.reglas[regla] += 1
        self.por_tabla[tabla] += 1
        self.rows.append((tabla, fila, clave, regla, detalle[:250], (str(raw)[:200] if raw is not None else None)))

    def flush(self):
        self.file.insert("dq_rechazo",
                         ["origen_tabla", "origen_fila", "clave_negocio", "regla", "detalle", "valor_raw"],
                         self.rows, batch=500)


# --------------------------------------------------------------------------
# acceso a Access
# --------------------------------------------------------------------------
class Tabla:
    def __init__(self, db, nombre):
        self.nombre = nombre
        t = db.get_table(nombre)
        self.data = t.parse() if t is not None else {}
        self.cmap = {kkey(c): c for c in self.data}
        self.n = len(next(iter(self.data.values()))) if self.data else 0

    def get(self, i, *alias):
        """get(fila, 'fecha_atencion') es tolerante: normaliza el alias a kkey."""
        for a in alias:
            c = self.cmap.get(kkey(a))
            if c is not None:
                return self.data[c][i]
        return None

    def col(self, *alias):
        for a in alias:
            c = self.cmap.get(kkey(a))
            if c is not None:
                return self.data[c]
        return []


# --------------------------------------------------------------------------
# ETL
# --------------------------------------------------------------------------
class Etl:
    def __init__(self, mdb, outdir, staging="core", limite=None):
        self.mdb = mdb
        self.out = outdir
        self.staging = staging
        self.limite = limite or 10 ** 9
        os.makedirs(outdir, exist_ok=True)
        self.db = AccessParser(mdb)

        self.f = {
            "staging": SqlFile(os.path.join(outdir, "10_staging.sql")),
            "cat": SqlFile(os.path.join(outdir, "20_catalogos.sql")),
            "pac": SqlFile(os.path.join(outdir, "30_pacientes.sql")),
            "ate": SqlFile(os.path.join(outdir, "40_atenciones.sql")),
            "fmt": SqlFile(os.path.join(outdir, "50_formatos.sql")),
            "cfg": SqlFile(os.path.join(outdir, "60_config.sql")),
            "dup": SqlFile(os.path.join(outdir, "70_duplicados.sql")),
            "dq": SqlFile(os.path.join(outdir, "80_dq_rechazo.sql")),
            "run": SqlFile(os.path.join(outdir, "90_etl_run.sql")),
        }
        self.dq = Dq(self.f["dq"])
        self.avisos = []

        # mapas de catalogo (valor normalizado -> id)
        self.id_distrito = {}
        self.id_microred = {}
        self.id_eess = {}
        self.id_especialidad = {}
        self.id_profesional = {}
        self.id_consultorio = {}
        self.id_seguro = {}
        self.id_condicion = {}
        self.id_lugar = {}
        self.id_prestacion = {}
        self.id_tipo_cert = {}
        self.paciente_por_codclie = {}
        self.seq = defaultdict(int)

    def next_id(self, entidad):
        self.seq[entidad] += 1
        return self.seq[entidad]

    # ---------------- FASE 0: reconocimiento ----------------
    def recon(self):
        pac = Tabla(self.db, "Pacientes")
        ref = Tabla(self.db, "Pacientes_ref")
        ate = Tabla(self.db, "Atencion")

        self.distintos = {
            "distrito": Counter(), "localidad": Counter(), "establecimiento": Counter(),
            "seguro": Counter(), "condicion": Counter(), "consultorio": Counter(),
        }
        for t in (pac, ref):
            for fld, campo in (("distrito", ("distrito",)), ("localidad", ("localidad",)),
                               ("establecimiento", ("establecimiento",)),
                               ("seguro", ("seguro",)), ("condicion", ("condicion",))):
                for v in t.col(*campo):
                    v, _ = limpio(v)
                    if v:
                        self.distintos[fld][v] += 1
        for v in ate.col("consultorio"):
            v, _ = limpio(v)
            if v:
                self.distintos["consultorio"][v] += 1

        # columnas Codigo_N: cuales son catalogos (baja cardinalidad) y cuales texto libre
        self.cod_cols = [k for k in ate.cmap if re.fullmatch(r"codigo\d+", k)]
        self.cod_cols.sort(key=lambda k: int(re.search(r"\d+", k).group()))
        self.cod_catalogo, self.cod_libre = {}, {}
        for k in self.cod_cols:
            vals = {v for v in (limpio(x)[0] for x in ate.data[ate.cmap[k]]) if v}
            (self.cod_catalogo if len(vals) <= 200 else self.cod_libre)[k] = vals

        # llaves para duplicados
        self.hc_grupos = defaultdict(list)
        self.doc_grupos = defaultdict(list)
        self.nombre_fecha = defaultdict(list)
        self.codclie_vistos = Counter()
        for i in range(min(pac.n, self.limite)):
            cod = pac.get(i, "codclie")
            hc, _ = limpio(pac.get(i, "historiaclinica"))
            if hc:
                self.hc_grupos[hc].append(cod)
            tipo, num = parse_documento(limpio(pac.get(i, "ndni", "dni"))[0])
            if tipo == "DNI":
                self.doc_grupos[num].append(cod)
            fn, _ = parse_fecha(pac.get(i, "fechanacimiento"))
            nom = norm(" ".join(str(x) for x in (
                pac.get(i, "apellidopaterno") or "", pac.get(i, "apellidomaterno") or "",
                pac.get(i, "primernombre") or "") if x))
            if fn and nom.strip():
                self.nombre_fecha[(nom, fn.isoformat())].append(cod)
            if cod is not None:
                self.codclie_vistos[cod] += 1
        return pac.n, ref.n, ate.n

    # ---------------- FASE 1: staging ----------------
    def staging_todo(self):
        tablas = ["Pacientes", "Pacientes_ref", "Atencion"] if self.staging == "core" else []
        if self.staging == "all":
            tablas = sorted(self.db.catalog)
        if self.staging == "none" or not tablas:
            return
        for nombre in tablas:
            t = Tabla(self.db, nombre)
            tabla = "stg_" + re.sub(r"\W+", "_", unicodedata.normalize("NFKD", nombre)
                                    .encode("ascii", "ignore").decode()).lower().strip("_")
            cols, usados = [], set()
            for c in t.data:
                cc = re.sub(r"[`]", "", c)[:60]
                base = cc
                n = 2
                while cc.lower() in usados:
                    cc = f"{base[:56]}_{n}"
                    n += 1
                usados.add(cc.lower())
                cols.append(cc)
            self.f["staging"].raw(
                f"CREATE TABLE IF NOT EXISTS `{tabla}` (_src_row INT NOT NULL PRIMARY KEY, "
                + ", ".join(f"`{c}` LONGTEXT" for c in cols)
                + ", cargado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB;")
            filas = []
            for i in range(min(t.n, self.limite)):
                filas.append([i] + [t.data[orig][i] if t.data[orig][i] is not None else None
                                    for orig in t.data])
            self.f["staging"].insert(tabla, ["_src_row"] + cols, filas, batch=200)

    # ---------------- FASE 2: catalogos ----------------
    def catalogos(self):
        f = self.f["cat"]

        # --- distrito (Provincia) ---
        prov = Tabla(self.db, "Provincia")
        filas = []
        for i in range(prov.n):
            nombre, _ = limpio(prov.get(i, "distrito"))
            if not nombre:
                continue
            iid = self.next_id("distrito")
            self.id_distrito[norm(nombre)] = iid
            filas.append([iid, prov.get(i, "codigo"), nombre, norm(nombre),
                          limpio(prov.get(i, "ubigeo"))[0], limpio(prov.get(i, "iddpto"))[0],
                          limpio(prov.get(i, "idprovincia"))[0], limpio(prov.get(i, "iddistrito"))[0],
                          parse_num(prov.get(i, "altitudmsnm"), 0, 6000), 
                          parse_num(prov.get(i, "quintil"), 1, 5)])
        f.insert("cat_distrito", ["id", "codigo_legacy", "distrito", "nombre_norm", "ubigeo",
                                  "id_dpto", "id_provincia", "id_distrito", "altitud_msnm", "quintil"], filas)

        # --- microred ---
        mr = Tabla(self.db, "Microred")
        filas = []
        for i in range(mr.n):
            nombre, _ = limpio(mr.get(i, "descripcion"))
            if not nombre:
                continue
            iid = self.next_id("microred")
            self.id_microred[norm(nombre)] = iid
            filas.append([iid, mr.get(i, "codigo"), nombre, norm(nombre), limpio(mr.get(i, "iddisa"))[0],
                          limpio(mr.get(i, "idred"))[0], limpio(mr.get(i, "idmicrored"))[0]])
        f.insert("cat_microred", ["id", "codigo_legacy", "descripcion", "nombre_norm",
                                  "id_disa", "id_red", "id_microred"], filas)

        # --- establecimiento (EESS + EESS_PS + nombres libres) ---
        filas = []
        for tabla, origen, campo in (("EESS", "EESS", "eess"), ("EESS_PS", "EESS_PS", "eess")):
            t = Tabla(self.db, tabla)
            for i in range(t.n):
                nombre, _ = limpio(t.get(i, campo))
                if not nombre:
                    continue
                if norm(nombre) in self.id_eess:
                    continue
                iid = self.next_id("eess")
                self.id_eess[norm(nombre)] = iid
                filas.append([iid, t.get(i, "codigo"), nombre, norm(nombre),
                              limpio(t.get(i, "renaes"))[0], limpio(t.get(i, "clave"))[0],
                              limpio(t.get(i, "sien"))[0], origen, None])
        for nombre in self.distintos["establecimiento"]:
            if norm(nombre) in self.id_eess:
                continue
            iid = self.next_id("eess")
            self.id_eess[norm(nombre)] = iid
            filas.append([iid, None, nombre, norm(nombre), None, None, None, "texto_libre", None])

        # --- padron nacional (EESS_PS_SESMA) para resolver nombres ---
        sesma = Tabla(self.db, "EESS_PS_SESMA")
        filas_sesma, vistos = [], set()
        for i in range(sesma.n):
            nombre, _ = limpio(sesma.get(i, "eess"))
            if not nombre or norm(nombre) in vistos:
                continue
            vistos.add(norm(nombre))
            iid = self.next_id("sesma")
            filas_sesma.append([iid, sesma.get(i, "codigo"), nombre, norm(nombre), limpio(sesma.get(i, "renaes"))[0]])
        f.insert("cat_eess_sesma", ["id", "codigo_legacy", "nombre", "nombre_norm", "renaes"], filas_sesma)
        f.insert("cat_establecimiento", ["id", "codigo_legacy", "nombre", "nombre_norm", "renaes",
                                         "clave", "sien", "origen", "microred_id"], filas)

        # --- especialidades (4 catalogos + 8 tablas Esp_*) ---
        filas, vistos = [], set()
        for tabla in ("Especialidades", "Especialidades2", "Especialidades3", "Certificado"):
            t = Tabla(self.db, tabla)
            for i in range(t.n):
                nombre, _ = limpio(t.get(i, "especialidad"))
                if not nombre or norm(nombre) in vistos:
                    continue
                vistos.add(norm(nombre))
                iid = self.next_id("especialidad")
                self.id_especialidad[norm(nombre)] = iid
                filas.append([iid, limpio(t.get(i, "codigo"))[0], nombre, norm(nombre), tabla])
        for tabla in sorted(t for t in self.db.catalog if t.startswith("Esp_")):
            t = Tabla(self.db, tabla)
            for i in range(t.n):
                nombre, _ = limpio(t.get(i, "especialidad"))
                if not nombre or norm(nombre) in vistos:
                    continue
                vistos.add(norm(nombre))
                iid = self.next_id("especialidad")
                self.id_especialidad[norm(nombre)] = iid
                filas.append([iid, limpio(t.get(i, "codigo"))[0], nombre, norm(nombre), tabla])
        f.insert("cat_especialidad", ["id", "codigo", "nombre", "nombre_norm", "origen"], filas)

        # --- profesionales (Profesionales + Prof_*) ---
        filas, vistos_dni, vistos_nom = [], set(), set()
        for tabla in ["Profesionales"] + sorted(t for t in self.db.catalog if t.startswith("Prof_")):
            if tabla not in self.db.catalog:
                continue
            t = Tabla(self.db, tabla)
            for i in range(t.n):
                nombre, _ = limpio(t.get(i, "profesional"))
                if not nombre:
                    continue
                dni = limpio(t.get(i, "dni"))[0]
                dni = dni if (dni and dni.isdigit() and len(dni) == 8) else None
                nrm = norm(nombre)
                if (dni and dni in vistos_dni) or (not dni and nrm in vistos_nom):
                    continue
                if dni:
                    vistos_dni.add(dni)
                vistos_nom.add(nrm)
                iid = self.next_id("profesional")
                self.id_profesional[nrm] = iid
                if dni:
                    self.id_profesional["dni:" + dni] = iid
                filas.append([iid, t.get(i, "codigo"), nombre, nrm, dni,
                              limpio(t.get(i, "profesion"))[0], limpio(t.get(i, "especialidad"))[0],
                              limpio(t.get(i, "colegiatura"))[0], limpio(t.get(i, "atencion"))[0], tabla])
        f.insert("cat_profesional", ["id", "codigo_legacy", "nombre", "nombre_norm", "dni",
                                     "profesion", "especialidad", "colegiatura", "atencion_codigo", "origen"],
                 filas)

        # --- consultorio ---
        filas, vistos = [], set()
        esp2 = Tabla(self.db, "Especialidades2")
        candidatos = list(self.distintos["consultorio"]) + [
            limpio(v)[0] for v in esp2.col("especialidad") if limpio(v)[0]]
        for nombre in candidatos:
            if norm(nombre) in vistos:
                continue
            vistos.add(norm(nombre))
            iid = self.next_id("consultorio")
            self.id_consultorio[norm(nombre)] = iid
            filas.append([iid, nombre, norm(nombre)])
        f.insert("cat_consultorio", ["id", "nombre", "nombre_norm"], filas)

        # --- seguro (EESS_SIS esta mal nombrada: es el catalogo de seguros) ---
        filas, vistos = [], set()
        sis = Tabla(self.db, "EESS_SIS")
        for i in range(sis.n):
            nombre, _ = limpio(sis.get(i, "especialidad"))
            if not nombre or norm(nombre) in vistos:
                continue
            vistos.add(norm(nombre))
            iid = self.next_id("seguro")
            self.id_seguro[norm(nombre)] = iid
            filas.append([iid, limpio(sis.get(i, "codigo"))[0], nombre, norm(nombre)])
        for nombre in self.distintos["seguro"]:
            if norm(nombre) in vistos:
                continue
            vistos.add(norm(nombre))
            iid = self.next_id("seguro")
            self.id_seguro[norm(nombre)] = iid
            filas.append([iid, None, nombre, norm(nombre)])
        f.insert("cat_seguro", ["id", "codigo_legacy", "nombre", "nombre_norm"], filas)

        # --- condicion ---
        filas, vistos = [], set()
        for nombre in self.distintos["condicion"]:
            if norm(nombre) in vistos:
                continue
            vistos.add(norm(nombre))
            etapa, gest = deriva_condicion(nombre)
            iid = self.next_id("condicion")
            self.id_condicion[norm(nombre)] = iid
            filas.append([iid, nombre, norm(nombre), etapa, gest])
        f.insert("cat_condicion", ["id", "nombre", "nombre_norm", "etapa_vida", "estado_gestacional"], filas)

        # --- lugar: union de los 29 catalogos Z_* + localidades libres ---
        filas, vistos = [], set()
        z_tablas = sorted(t for t in self.db.catalog if re.fullmatch(r"Z_\d+(?:_\d{4})?", t))
        for tabla in z_tablas:
            t = Tabla(self.db, tabla)
            m = re.search(r"_(\d{4})$", tabla)
            anio = int(m.group(1)) if m else None
            for i in range(t.n):
                nombre, _ = limpio(t.get(i, "lugar"))
                if not nombre or (tabla, norm(nombre)) in vistos:
                    continue
                vistos.add((tabla, norm(nombre)))
                clave = limpio(t.get(i, "clave"))[0]
                ubigeo = clave if (clave and re.fullmatch(r"\d{6,8}", clave)
                                   and clave not in ("000001", "00000001")) else None
                iid = self.next_id("lugar")
                self.id_lugar.setdefault(norm(nombre), iid)
                filas.append([iid, tabla, anio, t.get(i, "codigo"), nombre, norm(nombre), clave, ubigeo])
        for nombre in self.distintos["localidad"]:
            if norm(nombre) in self.id_lugar:
                continue
            iid = self.next_id("lugar")
            self.id_lugar[norm(nombre)] = iid
            filas.append([iid, "texto_libre", None, None, nombre, norm(nombre), None, None])
        f.insert("cat_lugar", ["id", "tabla_origen", "anio", "codigo_legacy", "nombre",
                               "nombre_norm", "clave_texto", "ubigeo"], filas)

        # --- tipo de certificado ---
        cert = Tabla(self.db, "Certificado")
        filas = []
        for i in range(cert.n):
            nombre, _ = limpio(cert.get(i, "especialidad"))
            if not nombre:
                continue
            iid = self.next_id("tipocert")
            self.id_tipo_cert[norm(nombre)] = iid
            filas.append([iid, limpio(cert.get(i, "codigo"))[0], nombre])
        f.insert("cat_tipo_certificado", ["id", "codigo", "nombre"], filas)

        # --- prestaciones: valores reutilizables de Codigo_N ---
        filas, vistos = [], set()
        for col, vals in self.cod_catalogo.items():
            for v in sorted(vals):
                if v in vistos:
                    continue
                vistos.add(v)
                m = re.match(r"([A-Za-z_]+)", v)
                pref = m.group(1).upper() if m else None
                item = v[len(pref):] if pref else v
                iid = self.next_id("prestacion")
                self.id_prestacion[v] = iid
                filas.append([iid, v, pref, item, 1])
        f.insert("cat_prestacion", ["id", "codigo", "servicio_prefijo", "item_numero", "en_catalogo"], filas)

        # --- instituciones ---
        inst = Tabla(self.db, "Instituciones")
        filas = []
        for i in range(inst.n):
            nombre, _ = limpio(inst.get(i, "instituciones"))
            if not nombre:
                continue
            filas.append([self.next_id("institucion"), inst.get(i, "codigo"), nombre])
        f.insert("cat_institucion", ["id", "codigo_legacy", "nombre"], filas)

    # ---------------- FASE 3: pacientes ----------------
    def pacientes(self):
        f = self.f["pac"]
        pac = Tabla(self.db, "Pacientes")
        ANEXO_EXTRA = ["Arequipa_040", "Arequipa_2", "Arequipa_SIS", "Peso_PG", "Talla_PG",
                       "Sistolica", "Diastolica", "Temperatura", "Peso_AG", "Semana", "Parto"]
        columnas_anexo = [(c, c) for c in pac.data if re.fullmatch(r"Anexo\d+", kkey(c) or "")
                          or re.fullmatch(r"anexo\d+", kkey(c))]
        columnas_anexo = [(c, kkey(c)) for c in pac.data if kkey(c).startswith("anexo")]
        columnas_extra = [(c, kkey(c)) for c in pac.data if kkey(c) in {kkey(x) for x in ANEXO_EXTRA}]

        filas, anexos = [], []
        n_placeholder = 0
        for i in range(min(pac.n, self.limite)):
            cod = pac.get(i, "codclie")
            hubo_corrupto = False

            def g(*alias):
                nonlocal hubo_corrupto
                val, mal = limpio(pac.get(i, *alias))
                if mal:
                    hubo_corrupto = True
                    self.dq.add("Pacientes", i, cod, "R1_CELDA_CORRUPTA",
                                f"campo {alias[0]}", pac.get(i, *alias))
                return val

            hc = g("historiaclinica")
            hf = g("historiafamiliar")
            hf_ph = 1 if (hf == "-") else 0
            tipo_doc, num_doc = parse_documento(g("ndni", "dni"))
            raw_doc = pac.get(i, "ndni") or pac.get(i, "dni")
            if tipo_doc == "SIN_DOCUMENTO" and isinstance(raw_doc, str) and raw_doc.strip():
                regla = "R2_DNI_CENTINELA" if norm(raw_doc) in CENTINELAS_DOC else "R3_DOCUMENTO_FORMATO"
                self.dq.add("Pacientes", i, cod, regla, "documento descartado", raw_doc)
            sexo = parse_sexo(g("sexo"))
            if sexo is None and pac.get(i, "sexo") not in (None, ""):
                self.dq.add("Pacientes", i, cod, "R10_SEXO_NO_MAPEABLE", "sexo descartado", pac.get(i, "sexo"))

            fn, motivo_fn = parse_fecha(pac.get(i, "fechanacimiento"))
            if fn is None and motivo_fn:
                self.dq.add("Pacientes", i, cod, "R8_FECHA_INVALIDA",
                            "fecha_nacimiento " + motivo_fn, pac.get(i, "fechanacimiento"))
            fi, motivo_fi = parse_fecha(pac.get(i, "fecha_inscripcion") or pac.get(i, "fechainscripcion"))
            if fi is None and motivo_fi:
                self.dq.add("Pacientes", i, cod, "R8_FECHA_INVALIDA",
                            "fecha_inscripcion " + motivo_fi, pac.get(i, "fechainscripcion"))
            ph_inscripcion = 1 if (fi and fi.year == 2016 and fi.month == 1 and fi.day == 1) else 0
            if ph_inscripcion:
                n_placeholder += 1
            if fn and fn > date(2026, 9, 21):
                self.dq.add("Pacientes", i, cod, "R8_FECHA_INVALIDA", "fecha_nacimiento futura", str(fn))
                fn = None

            distrito_txt = g("distrito")
            localidad_txt = g("localidad")
            eess_txt = g("establecimiento")
            seguro_txt = g("seguro")
            cond_txt = g("condicion")
            etapa, gest = deriva_condicion(cond_txt)
            if cond_txt and etapa is None and gest is None:
                self.dq.add("Pacientes", i, cod, "R11_ETAPA_DESCONOCIDA", "condicion sin clasificar", cond_txt)

            def ref(mapa, texto, campo):
                if not texto:
                    return None
                iid = mapa.get(norm(texto))
                if iid is None:
                    self.dq.add("Pacientes", i, cod, "R14_CATALOGO_NO_RESUELTO", f"{campo}: {texto}", texto)
                return iid

            pid = self.next_id("paciente")
            self.paciente_por_codclie[cod] = pid
            filas.append([
                pid, cod, "Pacientes", hc, hf, hf_ph, tipo_doc, num_doc,
                g("apellidopaterno"), g("apellidomaterno"), g("primernombre"), g("otrosnombres"),
                sexo, fn, (str(pac.get(i, "fechanacimiento"))[:24] if fn is None else None),
                fi, ph_inscripcion,
                ref(self.id_distrito, distrito_txt, "distrito"),
                ref(self.id_lugar, localidad_txt, "localidad"),
                ref(self.id_eess, eess_txt, "establecimiento"),
                ref(self.id_seguro, seguro_txt, "seguro"),
                ref(self.id_condicion, cond_txt, "condicion"),
                etapa, gest, g("direccion"), distrito_txt, localidad_txt, eess_txt, seguro_txt,
                1 if hubo_corrupto else 0,
                1 if (hc and len(self.hc_grupos.get(hc, [])) > 1) else 0,
            ])
            for col, ck in columnas_anexo + columnas_extra:
                val, mal = limpio(pac.data[col][i])
                if mal:
                    hubo_corrupto = True
                    self.dq.add("Pacientes", i, cod, "R1_CELDA_CORRUPTA", f"campo {col}", pac.data[col][i])
                    continue
                if val not in (None, ""):
                    anexos.append([pid, col, str(val), "Pacientes"])

        f.insert("paciente", [
            "id", "legacy_codclie", "origen_tabla", "historia_clinica", "historia_familiar",
            "historia_familiar_placeholder", "tipo_documento", "numero_documento",
            "apellido_paterno", "apellido_materno", "primer_nombre", "otros_nombres",
            "sexo", "fecha_nacimiento", "fecha_nacimiento_texto", "fecha_inscripcion",
            "fecha_inscripcion_placeholder", "distrito_id", "lugar_id", "establecimiento_id",
            "seguro_id", "condicion_id", "etapa_vida", "estado_gestacional", "direccion",
            "distrito_texto", "localidad_texto", "establecimiento_texto", "seguro_texto",
            "tiene_celda_corrupta", "es_duplicado_sospechoso"], filas)

        # resumen del placeholder masivo de fecha_inscripcion (una fila, no 45.891)
        if n_placeholder:
            self.dq.add("Pacientes", None, None, "R12_FECHA_INSCRIPCION_PLACEHOLDER",
                        f"{n_placeholder} pacientes con 2016-01-01 (carga masiva): se conserva marcado", "2016-01-01")

        # duplicado de Codclie en el origen
        for cod, n in self.codclie_vistos.items():
            if n > 1:
                self.dq.add("Pacientes", None, cod, "R5_CODCLIE_DUPLICADO",
                            f"Codclie repetido {n} veces en el origen", cod)

        # --- pacientes que solo existen en Pacientes_ref ---
        ref = Tabla(self.db, "Pacientes_ref")
        filas_ref_pac, anexos_ref = [], []
        nuevos = 0
        for i in range(min(ref.n, self.limite)):
            cod = ref.get(i, "codclie")
            if cod in self.paciente_por_codclie:
                continue
            tipo_doc, num_doc = parse_documento(limpio(ref.get(i, "ndni", "dni"))[0])
            fn, _ = parse_fecha(ref.get(i, "fechanacimiento"))
            hc = limpio(ref.get(i, "historiaclinica"))[0]
            pid = self.next_id("paciente")
            self.paciente_por_codclie[cod] = pid
            nuevos += 1
            self.dq.add("Pacientes_ref", i, cod, "R13_PACIENTE_SOLO_EN_REF",
                        "paciente no existe en Pacientes, se crea desde Pacientes_ref", cod)
            filas_ref_pac.append([
                pid, cod, "Pacientes_ref", hc, None, 0, tipo_doc, num_doc,
                limpio(ref.get(i, "apellidopaterno"))[0], limpio(ref.get(i, "apellidomaterno"))[0],
                limpio(ref.get(i, "primernombre"))[0], limpio(ref.get(i, "otrosnombres"))[0],
                parse_sexo(limpio(ref.get(i, "sexo"))[0]), fn, None, None, 0,
                self.id_distrito.get(norm(limpio(ref.get(i, "distrito"))[0] or "")),
                self.id_lugar.get(norm(limpio(ref.get(i, "localidad"))[0] or "")),
                self.id_eess.get(norm(limpio(ref.get(i, "establecimiento"))[0] or "")),
                self.id_seguro.get(norm(limpio(ref.get(i, "seguro"))[0] or "")),
                None, *deriva_condicion(None),
                limpio(ref.get(i, "direccion"))[0],
                limpio(ref.get(i, "distrito"))[0], limpio(ref.get(i, "localidad"))[0],
                limpio(ref.get(i, "establecimiento"))[0], limpio(ref.get(i, "seguro"))[0], 0, 0])
        if filas_ref_pac:
            self.f["pac"].insert("paciente", [
                "id", "legacy_codclie", "origen_tabla", "historia_clinica", "historia_familiar",
                "historia_familiar_placeholder", "tipo_documento", "numero_documento",
                "apellido_paterno", "apellido_materno", "primer_nombre", "otros_nombres",
                "sexo", "fecha_nacimiento", "fecha_nacimiento_texto", "fecha_inscripcion",
                "fecha_inscripcion_placeholder", "distrito_id", "lugar_id", "establecimiento_id",
                "seguro_id", "condicion_id", "etapa_vida", "estado_gestacional", "direccion",
                "distrito_texto", "localidad_texto", "establecimiento_texto", "seguro_texto",
                "tiene_celda_corrupta", "es_duplicado_sospechoso"], filas_ref_pac)
        self.f["pac"].insert("paciente_anexo", ["paciente_id", "campo", "valor", "origen_tabla"],
                             anexos + anexos_ref, batch=500)
        return len(filas), nuevos

    # ---------------- FASE 4: atenciones ----------------
    def atenciones(self):
        ate = Tabla(self.db, "Atencion")
        filas_ate, filas_cod = [], []
        huerfanas = 0
        for i in range(min(ate.n, self.limite)):
            aid = self.next_id("atencion")
            legacy = ate.get(i, "id")
            idclie = ate.get(i, "idcliente")
            pid = self.paciente_por_codclie.get(idclie)
            if pid is None:
                huerfanas += 1
                self.dq.add("Atencion", i, legacy, "R13_ATENCION_HUERFANA",
                            f"Idcliente {idclie} no existe en Pacientes", idclie)
            fecha = parse_fecha_hora(ate.get(i, "fecha_atencion"), ate.get(i, "hora1"), ate.get(i, "hora2"))
            anios, meses, dias = parse_edad(ate.get(i, "edad"))
            if anios is None and ate.get(i, "edad") not in (None, ""):
                self.dq.add("Atencion", i, legacy, "R16_EDAD_NO_PARSEABLE", "edad cruda", ate.get(i, "edad"))
            if fecha is None:
                self.dq.add("Atencion", i, legacy, "R8_FECHA_INVALIDA", "Fecha_atencion", ate.get(i, "fecha_atencion"))

            def medida(campo, lo, hi, dec, acepta_etiqueta=False):
                """lo/ceiling None = sin rango (columnas de semantica mixta, p.ej. PE/TE/PT)."""
                v = limpio(ate.get(i, campo))[0]
                if v is None:
                    return None, None
                if lo is None:
                    txt = str(v).strip().replace(",", ".")
                    n = round(float(txt), dec) if re.fullmatch(r"-?\d+(?:\.\d+)?", txt) else None
                else:
                    n = parse_num(v, lo, hi, dec)
                if n is None:
                    if acepta_etiqueta or lo is None:
                        return None, str(v)[:60]
                    self.dq.add("Atencion", i, legacy, "R9_MEDIDA_FUERA_RANGO",
                                f"{campo}={v} fuera de [{lo},{hi}]", v)
                    return None, None
                return n, None

            peso, _ = medida("peso", 0.2, 300, 2)
            talla, _ = medida("talla", 20, 250, 1)
            peso_pg, _ = medida("pesopg", 0.2, 300, 2)
            talla_pg, _ = medida("tallapg", 20, 250, 1)
            sis, _ = medida("sistolica", 30, 300, 0)
            dia, _ = medida("distolica", 20, 200, 0)
            # PE/TE/PT: mezclan z-score, kg y diagnostico nutricional -> valor + etiqueta, sin rango
            pe_v, pe_e = medida("pe", None, None, 2, acepta_etiqueta=True)
            te_v, te_e = medida("te", None, None, 2, acepta_etiqueta=True)
            pt_v, pt_e = medida("pt", None, None, 2, acepta_etiqueta=True)

            consultorio = limpio(ate.get(i, "consultorio"))[0]
            profesional = limpio(ate.get(i, "profesional"))[0]
            filas_ate.append([
                aid, legacy, pid, None,
                self.id_consultorio.get(norm(consultorio) if consultorio else ""),
                self.id_profesional.get(norm(profesional) if profesional else ""),
                fecha, limpio(ate.get(i, "fecha_atendido"))[0] if isinstance(ate.get(i, "fecha_atendido"), str) else None,
                parse_num(ate.get(i, "hora2"), 0, 23),
                limpio(ate.get(i, "historiaclinica"))[0],
                limpio(ate.get(i, "edad"))[0], anios, meses, dias,
                peso, talla, peso_pg, talla_pg, sis, dia,
                pe_v, pe_e, te_v, te_e, pt_v, pt_e, 0,
            ])
            for k in self.cod_cols:
                v = limpio(ate.data[ate.cmap[k]][i])[0] if ate.cmap.get(k) else None
                if v is None:
                    continue
                pos = int(re.search(r"\d+", k).group())
                es_libre = 1 if k in self.cod_libre else 0
                pid_prest = None if es_libre else self.id_prestacion.get(v)
                m = re.match(r"([A-Za-z_]+)", v)
                filas_cod.append([aid, pos, v, pid_prest, (m.group(1).upper() if m else None), es_libre])
        self.f["ate"].insert("atencion", [
            "id", "legacy_id", "paciente_id", "establecimiento_id", "consultorio_id", "profesional_id",
            "fecha_atencion", "fecha_atendido_texto", "hora_rango", "historia_clinica", "edad_texto",
            "edad_anios", "edad_meses", "edad_dias", "peso_kg", "talla_cm", "peso_pg_kg", "talla_pg_cm",
            "sistolica", "diastolica", "peso_edad_valor", "peso_edad_etiqueta", "talla_edad_valor",
            "talla_edad_etiqueta", "peso_talla_valor", "peso_talla_etiqueta", "tiene_celda_corrupta"], filas_ate)
        self.f["ate"].insert("atencion_codigo", [
            "atencion_id", "posicion", "valor", "prestacion_id", "servicio_prefijo", "es_texto_libre"], filas_cod)
        return len(filas_ate), len(filas_cod), huerfanas

    # ---------------- FASE 5: formatos ----------------
    def formatos(self):
        ref = Tabla(self.db, "Pacientes_ref")
        filas, cods = [], []
        for i in range(min(ref.n, self.limite)):
            cod = ref.get(i, "codclie")
            rid = self.next_id("referencia")
            fecha, _ = parse_fecha(ref.get(i, "fecha_atencion"))
            consultorio = limpio(ref.get(i, "consultorio"))[0]
            profesional = limpio(ref.get(i, "profesional"))[0]
            eess = limpio(ref.get(i, "establecimiento"))[0]
            filas.append([
                rid, cod, self.paciente_por_codclie.get(cod), fecha,
                limpio(ref.get(i, "historiaclinica"))[0], limpio(ref.get(i, "ndni", "dni"))[0],
                limpio(ref.get(i, "apellidosnombres"))[0] or " ".join(
                    str(x) for x in (limpio(ref.get(i, "apellidopaterno"))[0],
                                     limpio(ref.get(i, "apellidomaterno"))[0],
                                     limpio(ref.get(i, "primernombre"))[0]) if x),
                parse_sexo(limpio(ref.get(i, "sexo"))[0]), limpio(ref.get(i, "edad"))[0],
                limpio(ref.get(i, "distrito"))[0], limpio(ref.get(i, "localidad"))[0],
                limpio(ref.get(i, "direccion"))[0],
                self.id_eess.get(norm(eess) if eess else ""),
                limpio(ref.get(i, "seguro"))[0], limpio(ref.get(i, "grupo"))[0],
                limpio(ref.get(i, "referencia"))[0], limpio(ref.get(i, "contrareferencia"))[0],
                self.id_consultorio.get(norm(consultorio) if consultorio else ""),
                self.id_profesional.get(norm(profesional) if profesional else ""),
                limpio(ref.get(i, "admision"))[0], limpio(ref.get(i, "hora1"))[0]])
            for k in sorted((c for c in ref.cmap if re.fullmatch(r"codigo\d+", c)),
                            key=lambda c: int(re.search(r"\d+", c).group())):
                v = limpio(ref.data[ref.cmap[k]][i])[0]
                if v:
                    cods.append([rid, int(re.search(r"\d+", k).group()), v])
        self.f["fmt"].insert("referencia", [
            "id", "legacy_codclie", "paciente_id", "fecha_atencion", "historia_clinica",
            "numero_documento", "apellidos_nombres", "sexo", "edad_texto", "distrito_texto",
            "localidad_texto", "direccion", "establecimiento_id", "seguro_texto", "grupo",
            "referencia", "contrareferencia", "consultorio_id", "profesional_id", "admision", "hora"], filas)
        self.f["fmt"].insert("referencia_codigo", ["referencia_id", "posicion", "valor"], cods)

        # fua / certificado (hoy vacios en Access, se dejan cargados si aparecen filas)
        fua = Tabla(self.db, "Atencion_fua")
        filas = []
        for i in range(fua.n):
            filas.append([self.next_id("fua"), fua.get(i, "codclie"), limpio(fua.get(i, "historiaclinica"))[0],
                          parse_fecha(fua.get(i, "fecha_atencion"))[0], limpio(fua.get(i, "dni"))[0],
                          limpio(fua.get(i, "apellidos"))[0], parse_sexo(limpio(fua.get(i, "sexo"))[0]),
                          limpio(fua.get(i, "grupo"))[0],
                          self.id_consultorio.get(norm(limpio(fua.get(i, "consultorio"))[0] or "")),
                          limpio(fua.get(i, "profesional"))[0], limpio(fua.get(i, "admision"))[0],
                          limpio(fua.get(i, "fua"))[0], limpio(fua.get(i, "referencia"))[0],
                          limpio(fua.get(i, "contrareferencia"))[0]])
        self.f["fmt"].insert("atencion_fua", [
            "id", "legacy_codclie", "historia_clinica", "fecha_atencion", "numero_documento",
            "apellidos", "sexo", "grupo", "consultorio_id", "profesional", "admision", "fua",
            "referencia", "contrareferencia"], filas)

        cert = Tabla(self.db, "Atencion_certificado")
        filas, cods = [], []
        for i in range(cert.n):
            cid = self.next_id("cert")
            tipo = limpio(cert.get(i, "tipo"))[0]
            filas.append([cid, cert.get(i, "id"), cert.get(i, "idcliente"),
                          limpio(cert.get(i, "nrocertificado"))[0],
                          parse_fecha(cert.get(i, "fecha_atencion"))[0],
                          limpio(cert.get(i, "dni"))[0], limpio(cert.get(i, "apellidosnombres"))[0],
                          self.id_tipo_cert.get(norm(tipo) if tipo else None),
                          self.id_consultorio.get(norm(limpio(cert.get(i, "consultorio"))[0] or "")),
                          limpio(cert.get(i, "profesional"))[0], limpio(cert.get(i, "admision"))[0]])
            for k in sorted((c for c in cert.cmap if re.fullmatch(r"codigo\d+", c)),
                            key=lambda c: int(re.search(r"\d+", c).group())):
                v = limpio(cert.data[cert.cmap[k]][i])[0]
                if v:
                    cods.append([cid, int(re.search(r"\d+", k).group()), v])
        self.f["fmt"].insert("atencion_certificado", [
            "id", "legacy_id", "legacy_codclie", "nro_certificado", "fecha_atencion",
            "numero_documento", "apellidos_nombres", "tipo_certificado_id", "consultorio_id",
            "profesional", "admision"], filas)
        self.f["fmt"].insert("atencion_certificado_codigo", ["certificado_id", "posicion", "valor"], cods)

        cn = Tabla(self.db, "Certificado_Nro")
        filas = [[self.next_id("certnro"), cn.get(i, "codclie"), limpio(cn.get(i, "numero"))[0],
                  limpio(cn.get(i, "codigo"))[0]] for i in range(cn.n)]
        self.f["fmt"].insert("certificado_correlativo", ["id", "legacy_codclie", "numero", "codigo"], filas)

    # ---------------- FASE 6: configuracion heredada ----------------
    def configuracion(self):
        CONFIG = ["fua", "fua2", "fua3", "Impresion", "Impresora", "Paginas_web",
                  "Instituciones", "Responsable", "EESS_HF", "EESS_Padron"]
        filas = []
        for nombre in CONFIG:
            if nombre not in self.db.catalog:
                continue
            t = Tabla(self.db, nombre)
            for i in range(t.n):
                payload = {c: t.data[c][i] for c in t.data}
                filas.append([self.next_id("config"), nombre, i, None, json.dumps(payload, ensure_ascii=False, default=str)])
        self.f["cfg"].insert("config_legado", ["id", "tabla_origen", "fila_legacy", "descripcion", "payload_json"],
                             filas, batch=200)

        filas = []
        for nombre in ("Calibrar", "Calibrar_2", "Calibrar_3"):
            if nombre not in self.db.catalog:
                continue
            t = Tabla(self.db, nombre)
            for i in range(t.n):
                payload = {c: t.data[c][i] for c in t.data}
                filas.append([self.next_id("plantilla"), nombre, t.get(i, "codclie"),
                              json.dumps(payload, ensure_ascii=False, default=str)])
        self.f["cfg"].insert("plantilla_impresion", ["id", "nombre", "codigo_legacy", "payload_json"],
                             filas, batch=200)

        filas = []
        for nombre in ("Detalle_Adultos", "Detalle_Mujeres_Gestantes", "Detalle_Niños", "Detalle_Ninos"):
            if nombre not in self.db.catalog:
                continue
            t = Tabla(self.db, nombre)
            for i in range(t.n):
                payload = {c: t.data[c][i] for c in t.data}
                filas.append([self.next_id("formato"), nombre, i,
                              json.dumps(payload, ensure_ascii=False, default=str)])
        self.f["cfg"].insert("formato_exportacion", ["id", "nombre", "fila_legacy", "payload_json"],
                             filas, batch=200)

        # errores de exportacion que ya venian en la base Access
        err = Tabla(self.db, "Pacientes_ErroresDeExportación")
        for i in range(err.n):
            self.dq.add("Pacientes_ErroresDeExportacion", i, None, "R15_LEGADO_ERROR_EXPORTACION",
                        f"{limpio(err.get(i, 'campo'))[0]}: {limpio(err.get(i, 'error'))[0]}",
                        err.get(i, "fila"))

    # ---------------- FASE 7: duplicados ----------------
    def duplicados(self):
        filas = []
        grupos = [
            ("HISTORIA_CLINICA", self.hc_grupos, lambda c: None),
            ("DNI", self.doc_grupos, lambda c: c),
        ]
        for criterio, mapa, _ in grupos:
            for clave, cods in mapa.items():
                if len(cods) < 2:
                    continue
                for n, cod in enumerate(cods):
                    pid = self.paciente_por_codclie.get(cod)
                    filas.append([self.next_id("dupgrupo"), f"{criterio}:{clave}", criterio, pid, cod,
                                  clave if criterio == "HISTORIA_CLINICA" else None,
                                  clave if criterio == "DNI" else None, None, None,
                                  1 if n == 0 else 0, "PENDIENTE"])
                self.dq.add("Pacientes", None, clave, f"R4_{criterio}_DUPLICADO"
                            if criterio == "HISTORIA_CLINICA" else "R6_DNI_DUPLICADO",
                            f"{len(cods)} filas comparten {criterio}", clave)
        for (nom, f), cods in self.nombre_fecha.items():
            if len(cods) < 2:
                continue
            for n, cod in enumerate(cods):
                filas.append([self.next_id("dupgrupo"), f"NOMBRE_FECHA:{nom}|{f}", "NOMBRE_FECHA_NAC",
                              self.paciente_por_codclie.get(cod), cod, None, None, nom, f,
                              1 if n == 0 else 0, "PENDIENTE"])
        self.f["dup"].insert("paciente_duplicado",
                             ["id", "grupo", "criterio", "paciente_id", "legacy_codclie",
                              "historia_clinica", "numero_documento", "nombre_completo",
                              "fecha_nacimiento", "es_maestro", "decision"], filas, batch=300)

    # ---------------- ejecucion ----------------
    def run(self):
        t0 = datetime.now()
        print(f"[1/8] recon  {self.mdb}")
        n_pac, n_ref, n_ate = self.recon()
        print(f"      Pacientes={n_pac}  Pacientes_ref={n_ref}  Atencion={n_ate}")
        print(f"      columnas Codigo_N: {len(self.cod_catalogo)} catalogo / {len(self.cod_libre)} texto libre")

        print(f"[2/8] staging ({self.staging})")
        self.staging_todo()
        print("[3/8] catalogos")
        self.catalogos()
        print("[4/8] pacientes")
        n, nuevos = self.pacientes()
        print(f"      {n} pacientes + {nuevos} solo en Pacientes_ref")
        print("[5/8] atenciones")
        na, nc, huer = self.atenciones()
        print(f"      {na} atenciones, {nc} codigos, {huer} huerfanas")
        print("[6/8] formatos")
        self.formatos()
        print("[7/8] configuracion heredada")
        self.configuracion()
        print("[8/8] duplicados y calidad")
        self.duplicados()
        self.f["run"].insert("etl_run", ["id", "iniciado_at", "terminado_at", "origen", "version_etl", "resumen_json"],
                             [[1, t0, datetime.now(), ORIGEN, ETL_VERSION,
                               json.dumps({"staging": self.staging, "reglas_dq": dict(self.dq.reglas),
                                           "avisos": self.avisos}, ensure_ascii=False)]])

        if os.path.exists("schema.sql"):
            with open("schema.sql", encoding="utf-8") as src, \
                 open(os.path.join(self.out, "00_schema.sql"), "w", encoding="utf-8", newline="\n") as dst:
                dst.write(src.read())

        self.dq.flush()
        total = 0
        print("\nArchivos generados:")
        for nombre, f in self.f.items():
            n = f.flush()
            total += n
            print(f"  {f.path:<32} {n:>8} filas")
        print(f"\nTotal filas cargadas: {total}")
        print(f"Registros en cuarentena: {len(self.dq.rows)}")
        for regla, cnt in self.dq.reglas.most_common():
            print(f"  {regla:<34} {cnt}")

        with open(os.path.join(self.out, "resumen_etl.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"ETL {ETL_VERSION}  {t0:%Y-%m-%d %H:%M:%S}\n")
            fh.write(f"Origen: {self.mdb}\n\nFilas por tabla:\n")
            for nombre, f in self.f.items():
                for tabla, n in sorted(f.rows.items()):
                    fh.write(f"  {tabla:<34} {n}\n")
            fh.write("\nCuarentena por regla:\n")
            for regla, cnt in self.dq.reglas.most_common():
                fh.write(f"  {regla:<34} {cnt}\n")
            fh.write("\nCuarentena por tabla origen:\n")
            for tabla, cnt in self.dq.por_tabla.most_common():
                fh.write(f"  {tabla:<34} {cnt}\n")


def main():
    ap = argparse.ArgumentParser(description="ETL Access (mdb) -> MySQL (dump SQL)")
    ap.add_argument("--mdb", default="Data_base.mdb")
    ap.add_argument("--out", default="dump")
    ap.add_argument("--staging", choices=["none", "core", "all"], default="core",
                    help="core = Pacientes/Atencion/Pacientes_ref (por defecto), all = las 88 tablas")
    ap.add_argument("--limit", type=int, default=None, help="limitar filas por tabla (pruebas)")
    args = ap.parse_args()
    Etl(args.mdb, args.out, args.staging, args.limit).run()


if __name__ == "__main__":
    main()
