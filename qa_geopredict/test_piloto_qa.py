"""Pruebas externas contra el sistema y calibrador congelado."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from conftest import CFG, MODELO, PILOTO, RAIZ, SALIDAS
from fixtures import CAMPOS, guardar_json, leer_json


sys.path.insert(0, str(PILOTO))
from piloto.datos import huella, limpiar
from piloto.modelo import caracteristicas, por_segmento, puntuar


def evidencia(codigo, texto, **datos):
    guardar_json(SALIDAS/"evidencias"/f"{codigo}.json", {"observado": texto, "mediciones": datos})


def cli(destino, etapa, nombre, *args):
    logs = SALIDAS/"logs"
    logs.mkdir(parents=True, exist_ok=True)
    comando = [sys.executable, "-m", "piloto", "--salida", str(destino), etapa, *map(str, args)]
    res = subprocess.run(comando, cwd=PILOTO, capture_output=True, encoding="utf-8", errors="replace",
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    (logs/f"{nombre}.log").write_text(f"Comando: {subprocess.list2cmdline(comando)}\n"
                                     f"Código: {res.returncode}\n{res.stdout}\n{res.stderr}", encoding="utf-8")
    return res


def ultimo_path(res):
    assert res.returncode == 0, res.stderr
    return Path(res.stdout.strip().splitlines()[-1])


def cargar(datos, nombre, salida=None, sufijo=""):
    salida = salida or SALIDAS/"corridas"/nombre
    res = cli(salida, "etl", f"{nombre}_etl{sufijo}", "--fuente", datos/nombre)
    return ultimo_path(res)


def inferir(salida, lote, nombre):
    res = cli(salida, "inferir", f"{nombre}_inferir", "--lote", lote, "--modelo", MODELO)
    return ultimo_path(res)


def corrida(datos, nombre, salida=None, sufijo=""):
    salida = salida or SALIDAS/"corridas"/nombre
    lote = cargar(datos, nombre, salida, sufijo)
    return lote, inferir(salida, lote, nombre+sufijo)


@pytest.fixture(scope="session")
def control(datos):
    return corrida(datos, "normal")


@pytest.fixture(scope="session")
def anomalias(datos):
    return corrida(datos, "perturbada")


def niveles(path):
    return pd.read_csv(path/"puntuaciones_segmento.csv").set_index("desde_m")


def alertas(path):
    return pd.read_csv(path/"alertas.csv")


def test_pasada_normal_qa01(control):
    lote, salida = control
    seg = niveles(salida)
    a = alertas(salida)
    etl = leer_json(lote/"etl.json")
    geo = leer_json(salida/"segmentos.geojson")
    evidencia("QA01", f"{len(seg)} segmentos, {seg.nivel.eq('bajo').sum()} bajos, uno inicial sin "
              f"cobertura ({seg.loc[0].cobertura:.0%}) y {len(a)} alertas.",
              trazas=etl["calidad"]["trazas_unicas"], elementos_geojson=len(geo["features"]))
    assert len(seg) == 67 and seg.loc[0].nivel == "sin_cobertura"
    assert seg.drop(index=0).nivel.eq("bajo").all() and a.empty
    assert len(geo["features"]) == len(seg)


def test_senal_incipiente_qa02(anomalias):
    _, salida = anomalias
    seg = niveles(salida).loc[80]
    a = alertas(salida)
    cruces = a.desde_m.le(80) & a.hasta_m.gt(80)
    evidencia("QA02", f"PK 80 m {seg.nivel}. Alertas que cubren el segmento: {cruces.sum()}.",
              p95=float(seg.fraccion_sobre_umbral_moderado), p99=float(seg.fraccion_sobre_umbral_alto))
    assert seg.nivel == "moderado" and not cruces.any()


def test_progresion_qa03(anomalias):
    _, salida = anomalias
    seg = niveles(salida).loc[[115, 135, 155]]
    secuencia = seg.nivel.tolist()
    desvios = seg.desvio_p90.tolist()
    evidencia("QA03", f"Secuencia observada {', '.join(secuencia)}. Desvíos P90 {np.round(desvios, 3)}.",
              pk_m=[115, 135, 155], niveles=secuencia, desvios=desvios)
    assert secuencia == ["bajo", "moderado", "alto"] and (np.diff(desvios) > 0).all()


def test_prioridad_maxima_qa04(anomalias):
    _, salida = anomalias
    a = alertas(salida)
    primera = a.iloc[0]
    requeridos = ["alerta_id", "survey_id", "generada_utc", "corte_utc", "corte_priorizacion_utc",
                  "tipo", "puntuacion_0_100", "nivel", "factor_principal", "justificacion", "accion",
                  "prioridad", "estado", "id_modelo", "longitude", "latitude"]
    evidencia("QA04", f"{len(a)} alertas. Prioridad 1 en PK {primera.desde_m:g}–{primera.hasta_m:g} m.",
              id=str(primera.alerta_id), desvio_p90=float(primera.desvio_p90), nivel=str(primera.nivel),
              horizonte_vacio=bool(a.horizonte_dias.isna().all()))
    assert len(a) <= leer_json(CFG)["max_alertas_por_recorrido"]
    assert primera.desde_m <= 190 < primera.hasta_m and primera.nivel == "alto" and primera.prioridad == 1
    assert not a[requeridos].isna().any().any() and a.alerta_id.is_unique
    assert a[["horizonte_dias", "probabilidad_socavacion"]].isna().all().all()
    assert (pd.to_datetime(a.corte_utc, utc=True) <= pd.to_datetime(a.corte_priorizacion_utc, utc=True)).all()


def test_disminucion_qa05(datos, anomalias):
    _, previa = anomalias
    salida = SALIDAS/"corridas"/"perturbada"
    _, posterior = corrida(datos, "disminucion", salida)
    cambios = pd.read_csv(posterior/"cambios_nivel.csv")
    historia = pd.read_csv(posterior/"historial_alertas.csv")
    segmento = cambios.loc[cambios.segmento.eq(38)]
    nivel = niveles(posterior).loc[190].nivel
    evidencia("QA05", f"PK 190 m pasó a {nivel}. {len(cambios)} cambios, {len(historia)} eventos "
              f"absorbidos en el historial y {len(alertas(posterior))} alertas en la nueva salida.",
              transicion=segmento[["nivel_anterior", "nivel_nuevo"]].values.tolist())
    assert nivel == "bajo" and alertas(posterior).empty
    assert segmento[["nivel_anterior", "nivel_nuevo"]].values.tolist() == [["alto", "bajo"]]
    assert len(historia) == len(alertas(previa))


def test_incompletitud_qa06(datos):
    _, salida = corrida(datos, "incompleta")
    seg = niveles(salida).loc[300]
    evidencia("QA06", f"PK 300 m {seg.nivel}, cobertura {seg.cobertura:.0%} y "
              f"{len(alertas(salida))} alertas.",
              nulas=bool(pd.isna(seg.puntuacion_0_100)), trazas_puntuadas=int(seg.trazas_puntuadas))
    assert seg.nivel == "sin_cobertura" and pd.isna(seg.puntuacion_0_100) and alertas(salida).empty


def test_entradas_invalidas_qa07(datos):
    pruebas = {"npz_ausente": "Fuente requerida", "npz_corrupto": "File is not a zip file",
               "tipo_invalido": "Unable to parse string", "latitud_invalida": "fuera del CRS",
               "clave_conflictiva": "Clave repetida"}
    resumen = {}
    for nombre, texto in pruebas.items():
        destino = SALIDAS/"corridas"/nombre
        res = cli(destino, "etl", f"{nombre}_etl", "--fuente", datos/nombre)
        resumen[nombre] = {"salida": res.returncode, "causa": res.stderr.splitlines()[-1],
                          "aceptado": texto in res.stderr,
                          "manifiestos": len(list(destino.glob("lotes/*/etl.json")))}
    evidencia("QA07", f"{sum(r['salida']==1 for r in resumen.values())}/5 variantes devolvieron código 1. "
              "Sin publicación de manifiestos ETL.", controles=resumen)
    assert all(r["salida"] == 1 and r["aceptado"] and r["manifiestos"] == 0 for r in resumen.values())


def test_duplicados_y_reintento_qa08(datos):
    destino = SALIDAS/"corridas"/"duplicados"
    lote, salida = corrida(datos, "duplicados")
    digest = {n: huella(salida/n) for n in ("alertas.csv", "historial_alertas.csv", "puntuaciones_segmento.csv")}
    segundo, salida_dos = corrida(datos, "duplicados", destino, "_reintento")
    calidad = leer_json(lote/"etl.json")["calidad"]
    with sqlite3.connect(destino/"alertas.sqlite") as con:
        eventos = con.execute("SELECT COUNT(*) FROM historial").fetchone()[0]
    coincide = all(huella(salida_dos/n) == hash_ for n, hash_ in digest.items())
    evidencia("QA08", f"{calidad['copias_exactas']} copias retiradas, {eventos} eventos SQLite "
              f"y huellas iguales tras el reintento: {coincide}.",
              trazas=calidad["trazas_unicas"], huellas=digest)
    assert lote == segundo and calidad["copias_exactas"] == 352 and calidad["trazas_unicas"] == 6691
    assert coincide and eventos == len(alertas(salida))


def test_bordes_qa09():
    cfg, modelo = leer_json(CFG), leer_json(MODELO)
    umbrales = modelo["enfoques"]["multivariable"]
    m, a = umbrales["moderado"], umbrales["alto"]
    cerca_m, cerca_a = np.nextafter(m, np.inf), np.nextafter(a, np.inf)
    series = [[m]*20+[0]*80, [cerca_m]*10+[a]*10+[0]*80, [cerca_a]*19+[0]*81,
              [cerca_a]*20+[0]*80, [cerca_a]*20+[0]*54+[np.nan]*26,
              [cerca_a]*20+[0]*55+[np.nan]*25]
    df = pd.DataFrame({"segmento": np.repeat(np.arange(6), 100),
                       "desvio": np.concatenate(series), "survey_id": "QA-UMBRALES",
                       "timestamp": pd.Timestamp("2026-11-26T15:00:00Z"), "longitude": -75.57,
                       "latitude": 6.25, "percentil": 99., "factor": CAMPOS[0],
                       "extremo_superficial": False})
    tabla = por_segmento(df, modelo, "multivariable", cfg, 30., .05)
    df.assign(desvio_hex=[v.hex() for v in df.desvio]).to_csv(
        SALIDAS/"entradas"/"bordes_umbral.csv", index=False, float_format="%.17g")
    tabla.to_csv(SALIDAS/"evidencias"/"QA09_resultados.csv", index=False)
    evidencia("QA09", f"Secuencia observada {', '.join(tabla.nivel)}.",
              moderado=m, alto=a, coberturas=tabla.cobertura.tolist())
    assert tabla.nivel.tolist() == ["bajo", "moderado", "bajo", "alto", "sin_cobertura", "alto"]


def test_atributo_incompatible_qa10(datos):
    destino = SALIDAS/"corridas"/"discordante"
    csv = pd.read_csv(datos/"discordante"/"geopredict_regional.csv")
    i = int(csv.trace_id[csv.distance_m.eq(190)].iat[0])
    with np.load(datos/"discordante"/"senales.npz") as archivo:
        t = archivo["tiempo_ns"]
        rms = float(np.sqrt(np.mean(archivo["amplitud_perturbada"][i, (t >= 12) & (t < 30)]**2)))
    tabular = float(csv.rms_middle_au.iat[i])
    res = cli(destino, "etl", "discordante_etl", "--fuente", datos/"discordante")
    rechazado = res.returncode != 0
    alertas_inconsistentes = 0
    if not rechazado:
        lote = ultimo_path(res)
        salida = inferir(destino, lote, "discordante")
        a = alertas(salida)
        alertas_inconsistentes = int((a.desde_m.lt(200) & a.hasta_m.gt(180)).sum())
    evidencia("QA10", f"RMS CSV {tabular:.8f} u.a. frente a RMS NPZ {rms:.8f} u.a. "
              f"ETL {'rechazada' if rechazado else 'aceptada'} y {alertas_inconsistentes} alerta(s) "
              "en el intervalo discordante.",
              cociente=tabular/rms, pk=190, alertas_en_intervalo=alertas_inconsistentes)
    assert abs(tabular-rms) > .005
    assert rechazado or alertas_inconsistentes == 0, "La discordancia produjo una alerta."


def test_oraculo_y_causalidad_qa11(datos, control):
    _, salida = control
    orig, _ = limpiar(RAIZ/"entrega_geopredict")
    normal, _ = limpiar(datos/"normal")
    cfg, modelo = leer_json(CFG), leer_json(MODELO)
    puntuacion = pd.read_csv(salida/"puntuaciones_traza.csv").set_index("trace_id")
    diferencia = []
    referencias = caracteristicas(orig, cfg)
    para_calibrar = puntuar(referencias, modelo, "multivariable")
    for fuente, calculado in ((orig, para_calibrar), (normal, puntuacion)):
        for i in (130, 402, 810):
            ventana = fuente.iloc[i-39:i+1][CAMPOS]
            medianas = ventana.median()
            assert ventana.count().ge(30).all()
            z = max((medianas[k]-modelo["mediana"][k])/modelo["escala"][k] for k in CAMPOS)
            dist = modelo["enfoques"]["multivariable"]["distribucion"]
            percentil = 100*sum(v <= z+1e-10 for v in dist)/len(dist)
            dif = max(abs(float(calculado.loc[i, k])-medianas[k]) for k in CAMPOS)
            diferencia.append(dif)
            assert np.isclose(calculado.loc[i, "desvio"], z, atol=1e-9)
            assert abs(calculado.loc[i, "percentil"]-percentil) <= 100/len(dist)+1e-7
    original = caracteristicas(normal, cfg)
    normal.loc[normal.distance_m.ge(60), CAMPOS] *= 10
    modificado = caracteristicas(normal, cfg)
    anterior = original.distance_m.lt(60)
    iguales = original.loc[anterior].equals(modificado.loc[anterior])
    evidencia("QA11", f"Seis medianas por ventana verificadas. Error máximo {max(diferencia):.3g} u.a. "
              f"Las {anterior.sum()} trazas pasadas permanecieron iguales: {iguales}.",
              error_maximo_ua=max(diferencia), pasado_igual=iguales, trazas_pasadas=int(anterior.sum()))
    assert max(diferencia) < 1e-9 and iguales


def test_modelo_congelado_qa12(datos, control):
    _, futuro = control
    esperado = leer_json(MODELO)["id_modelo"]
    lote = cargar(datos, "anterior")
    salida = SALIDAS/"corridas"/"anterior"
    res = cli(salida, "inferir", "anterior_inferir", "--lote", lote, "--modelo", MODELO)
    congelados = leer_json(SALIDAS/"huellas_antes.json")
    actuales = {"modelo": huella(MODELO), "configuracion": huella(CFG)}
    id_futuro = niveles(futuro).id_modelo.iat[0]
    evidencia("QA12", f"Pasada posterior aceptada. Pasada anterior devolvió {res.returncode}. "
              f"Huellas preservadas: {congelados == actuales}.",
              sha256=actuales, id_modelo=str(id_futuro), causa=res.stderr.splitlines()[-1])
    assert res.returncode == 1 and "anterior al corte" in res.stderr
    assert id_futuro == esperado and congelados == actuales and not (salida/"inferencias").exists()


def test_horizonte_y_critico_qa13(anomalias):
    _, salida = anomalias
    niveles_reales = niveles(salida).nivel.unique().tolist()
    estado = leer_json(salida/"monitoreo.json")
    evidencia("QA13", "La zona extrema produjo nivel alto. El piloto deja los campos de horizonte y "
              "probabilidad vacíos y carece de eventos futuros confirmados.",
              niveles=niveles_reales, anticipacion=estado["metricas_anticipacion"])
    pytest.skip("Sin categoría crítica configurada ni seguimiento temporal de eventos confirmados.")
