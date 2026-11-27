"""Priorización por episodios contiguos y registro transaccional de atención."""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

import pandas as pd


def agrupar(segmentos, maximo):
    altos = segmentos.loc[segmentos.nivel.eq("alto")].sort_values("segmento").copy()
    grupo = altos.segmento.diff().ne(1).cumsum()
    candidatos = []
    for _, bloque in altos.groupby(grupo, sort=False):
        representativo = bloque.sort_values(["desvio_p90", "segmento"], ascending=[False, True]).iloc[0]
        primero, ultimo = bloque.iloc[0], bloque.iloc[-1]
        survey = str(primero.survey_id)
        clave = hashlib.sha256(f"{survey}|{primero.segmento}|revision_gpr".encode()).hexdigest()
        candidatos.append({
            "alerta_id": clave[:24], "survey_id": survey,
            "primer_segmento": int(primero.segmento), "ultimo_segmento": int(ultimo.segmento),
            "desde_m": float(primero.desde_m), "hasta_m": float(ultimo.hasta_m),
            "corte_utc": str(ultimo.corte_utc), "tipo": "anomalia_gpr_para_revision",
            "horizonte_dias": None, "probabilidad_socavacion": None,
            "puntuacion_0_100": float(representativo.puntuacion_0_100),
            "desvio_p90": float(representativo.desvio_p90),
            "nivel": "alto", "factor_principal": str(representativo.factor_principal),
            "longitude": float(representativo.longitude), "latitude": float(representativo.latitude),
            "justificacion": "Exceso persistente del umbral alto de referencia.",
            "accion": "Revisar radargrama, acoplamiento y redes. Si persiste, solicitar verificación de campo.",
            "id_modelo": str(representativo.id_modelo),
        })
    candidatos.sort(key=lambda a: (-a["desvio_p90"], a["primer_segmento"]))
    for orden, candidato in enumerate(candidatos, 1):
        candidato["prioridad"] = orden
    return candidatos[:maximo], len(candidatos)


def conectar(db):
    con = sqlite3.connect(db, timeout=30)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS alertas (
            alerta_id TEXT PRIMARY KEY, survey_id TEXT NOT NULL,
            creada_utc TEXT NOT NULL, estado TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS historial (
            evento_id TEXT PRIMARY KEY, alerta_id TEXT NOT NULL REFERENCES alertas(alerta_id),
            fecha_utc TEXT NOT NULL, estado TEXT NOT NULL, nota TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS nivel_segmento (
            survey_id TEXT NOT NULL, segmento INTEGER NOT NULL, nivel TEXT NOT NULL,
            PRIMARY KEY (survey_id, segmento)
        );
        CREATE TABLE IF NOT EXISTS cambios_nivel (
            id INTEGER PRIMARY KEY, survey_id TEXT NOT NULL, segmento INTEGER NOT NULL,
            fecha_utc TEXT NOT NULL, nivel_anterior TEXT NOT NULL, nivel_nuevo TEXT NOT NULL,
            id_modelo TEXT NOT NULL
        );
    """)
    return con


def registrar(db, candidatos, segmentos=None):
    filas = []
    ahora = datetime.now(timezone.utc).isoformat()
    with closing(conectar(db)) as con, con:
        con.execute("BEGIN IMMEDIATE")
        if segmentos is not None:
            for fila in segmentos.itertuples():
                clave = (str(fila.survey_id), int(fila.segmento))
                anterior = con.execute("SELECT nivel FROM nivel_segmento WHERE survey_id=? AND segmento=?",
                                       clave).fetchone()
                if anterior and anterior[0] != fila.nivel:
                    con.execute("INSERT INTO cambios_nivel (survey_id,segmento,fecha_utc,nivel_anterior,"
                                "nivel_nuevo,id_modelo) VALUES (?,?,?,?,?,?)",
                                (*clave, ahora, anterior[0], fila.nivel, fila.id_modelo))
                con.execute("INSERT INTO nivel_segmento VALUES (?,?,?) "
                            "ON CONFLICT(survey_id,segmento) DO UPDATE SET nivel=excluded.nivel",
                            (*clave, fila.nivel))
        for alerta in candidatos:
            alerta_id = alerta["alerta_id"]
            payload = json.dumps(alerta, ensure_ascii=False, sort_keys=True)
            previa = con.execute("SELECT creada_utc, estado, payload FROM alertas WHERE alerta_id=?",
                                 (alerta_id,)).fetchone()
            if previa is None:
                creada, estado = ahora, "pendiente"
                con.execute("INSERT INTO alertas VALUES (?,?,?,?,?)",
                            (alerta_id, alerta["survey_id"], creada, estado, payload))
                evento, nota = f"alta:{alerta_id}", "Emisión en piloto."
            else:
                creada, estado, anterior = previa
                evento = hashlib.sha256(f"{alerta_id}|{anterior}|{payload}".encode()).hexdigest()
                nota = "Actualización de evidencia y prioridad."
                if anterior != payload:
                    con.execute("UPDATE alertas SET payload=? WHERE alerta_id=?", (payload, alerta_id))
            if previa is None or previa[2] != payload:
                con.execute("INSERT OR IGNORE INTO historial VALUES (?,?,?,?,?)",
                            (evento, alerta_id, ahora, estado, nota))
            filas.append({**alerta, "generada_utc": creada, "estado": estado})
    return filas


def retroalimentar(db, alerta_id, estado, nota, evento_id):
    with closing(conectar(db)) as con, con:
        con.execute("BEGIN IMMEDIATE")
        actual = con.execute("SELECT estado FROM alertas WHERE alerta_id=?", (alerta_id,)).fetchone()
        if actual is None:
            raise ValueError("Identificador de alerta desconocido")
        previo = con.execute("SELECT alerta_id, estado, nota FROM historial WHERE evento_id=?",
                             (evento_id,)).fetchone()
        if previo:
            if previo != (alerta_id, estado, nota):
                raise ValueError("El identificador del evento ya tiene otros datos")
            return
        if estado not in {"en_revision", "cerrada", "descartada"} or not nota.strip():
            raise ValueError("Estado de atención o nota inválidos")
        if actual[0] in {"cerrada", "descartada"}:
            raise ValueError("La alerta ya tiene un estado final")
        con.execute("UPDATE alertas SET estado=? WHERE alerta_id=?", (estado, alerta_id))
        con.execute("INSERT INTO historial VALUES (?,?,?,?,?)",
                    (evento_id, alerta_id, datetime.now(timezone.utc).isoformat(), estado, nota))


def historico(db):
    with closing(conectar(db)) as con:
        return pd.read_sql_query("SELECT * FROM historial ORDER BY fecha_utc, evento_id", con)


def cambios_nivel(db):
    with closing(conectar(db)) as con:
        return pd.read_sql_query("SELECT * FROM cambios_nivel ORDER BY id", con)
