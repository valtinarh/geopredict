"""Construye el informe Word desde los resultados efectivamente ejecutados."""

import argparse
import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from plan import CASOS


PRUEBAS = {
    "QA01": ("normal", "puntuaciones_segmento.csv, alertas.csv, segmentos.geojson y etl.json",
             "Los segmentos con cobertura quedaron por debajo de los criterios de revisión. "
             "El primero tuvo 71 % de cobertura por el arranque de la ventana causal."),
    "QA02": ("perturbada", "puntuaciones_segmento.csv y alertas.csv, segmento 80 m",
             "El nivel moderado quedó disponible en el mapa sin consumir capacidad de revisión prioritaria."),
    "QA03": ("perturbada", "puntuaciones_segmento.csv, segmentos 115 m, 135 m y 155 m",
             "El sistema ordenó la respuesta conforme creció la perturbación sintética."),
    "QA04": ("perturbada", "alertas.csv, fila de prioridad 1",
             "La política asignó el primer lugar al retorno más intenso bajo la categoría alta vigente."),
    "QA05": ("perturbada", "cambios_nivel.csv, historial_alertas.csv y alertas.sqlite",
             "La reducción de evidencia se registró sin borrar la historia de revisión."),
    "QA06": ("incompleta", "puntuaciones_segmento.csv y alertas.csv, segmento 300 m",
             "La falta de datos produjo un estado explícito de cobertura insuficiente."),
    "QA07": ("logs", "Registros ETL de las cinco variantes inválidas",
             "El proceso devolvió un error controlado y evitó publicar lotes inválidos."),
    "QA08": ("duplicados", "etl.json, alertas.csv, historial_alertas.csv y SQLite",
             "La repetición de la carga mantuvo datos, salidas y eventos sin duplicación adicional."),
    "QA09": ("evidencias", "QA09_resultados.csv y entradas/bordes_umbral.csv",
             "Los operadores de comparación y los mínimos de cobertura y persistencia se aplicaron en los límites."),
    "QA10": ("discordante", "alertas.csv, CSV y NPZ de entrada y registro discordante_etl.log",
             "La integración verifica ejes y dimensiones. En este control permitió que un atributo discordante "
             "se convirtiera en una alerta de revisión."),
    "QA11": ("normal", "puntuaciones_traza.csv y diferencias del oráculo en evidencias",
             "Las ventanas y puntuaciones coinciden en los puntos comprobados y son causales."),
    "QA12": ("anterior", "anterior_inferir.log, huellas_antes.json y salida normal",
             "La etapa de inferencia cargó el modelo vigente y aplicó su corte temporal."),
    "QA13": ("perturbada", "monitoreo.json, alertas.csv y razón de bloqueo en pytest",
             "Es posible probar la atención de prioridad máxima vigente. Medir anticipación y una categoría "
             "crítica formal queda pendiente de definición y seguimiento."),
}

MATRIZ_ESPERADO = (
    "66 bajos, uno sin cobertura inicial y cero alertas.",
    "Nivel moderado en PK 80 m sin alerta en el intervalo.",
    "Niveles bajo, moderado y alto con desvío creciente.",
    "Prioridad 1 en PK 190 m, con horizonte vacío.",
    "Transición alto a bajo con historial y sin emisión.",
    "PK 300 m sin cobertura, puntuación o alerta.",
    "Código 1, causa registrada y cero lotes publicados.",
    "352 copias retiradas y salidas idénticas al repetir.",
    "Niveles correctos en seis límites de entrada.",
    "Rechazo o cuarentena del intervalo discordante.",
    "Valores iguales al cálculo independiente y causal.",
    "Aceptar el reloj posterior, rechazar el anterior.",
    "Categoría crítica y seguimiento de campo disponibles.",
)


def leer(p):
    return json.loads(p.read_text(encoding="utf-8"))


def observacion(texto):
    return (texto.replace("1 alerta(s)", "una alerta")
            .replace("eventos absorbidos en el historial", "eventos conservados en el historial")
            .replace("Seis medianas por ventana verificadas", "Seis ventanas verificadas")
            .replace(": True.", ": sí.").replace(": False.", ": no."))


def texto_con_etiqueta(doc, etiqueta, texto):
    par = doc.add_paragraph(style="Ficha")
    par.add_run(etiqueta + "  ").bold = True
    par.add_run(texto)
    return par


def tabla(doc, cabeceras, filas, anchos, fuente=9.5):
    t = doc.add_table(rows=1, cols=len(cabeceras))
    t.autofit = False
    props = t._tbl.tblPr
    bordes = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        linea = OxmlElement(f"w:{lado}")
        for k, v in {"val": "single", "sz": "5", "color": "D9D9D9"}.items():
            linea.set(qn(f"w:{k}"), v)
        bordes.append(linea)
    props.append(bordes)
    margenes = OxmlElement("w:tblCellMar")
    for lado in ("top", "left", "bottom", "right"):
        elemento = OxmlElement(f"w:{lado}")
        elemento.set(qn("w:w"), "44" if lado in ("top", "bottom") else "100")
        elemento.set(qn("w:type"), "dxa")
        margenes.append(elemento)
    props.append(margenes)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for i, ancho in enumerate(anchos):
        t.columns[i].width = Inches(ancho)
    for n, fila in enumerate([cabeceras, *filas]):
        row = t.rows[0] if n == 0 else t.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i, valor in enumerate(fila):
            celda = row.cells[i]
            celda.width = Inches(anchos[i])
            celda.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            relleno = OxmlElement("w:shd")
            relleno.set(qn("w:fill"), "E9EEF4" if n == 0 else ("F6F8FA" if n % 2 == 0 else "FFFFFF"))
            celda._tc.get_or_add_tcPr().append(relleno)
            p = celda.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            r = p.add_run(str(valor))
            r.bold = n == 0
            r.font.size = Pt(fuente)
    return t


def estilo(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.12
    for nombre, tam in (("Title", 30), ("Heading 1", 20), ("Heading 2", 15)):
        st = doc.styles[nombre]
        st.font.name = "Calibri"
        st.font.size = Pt(tam)
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.font.bold = True
        st.paragraph_format.space_before = Pt(14)
        st.paragraph_format.space_after = Pt(7)
        ppr = st._element.get_or_add_pPr()
        for previo in ppr.findall(qn("w:pBdr")):
            ppr.remove(previo)
    ficha = doc.styles.add_style("Ficha", 1)
    ficha.base_style = normal
    ficha.font.size = Pt(10.5)
    ficha.paragraph_format.space_after = Pt(4)
    ficha.paragraph_format.line_spacing = 1.1
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(.84)
    sec.top_margin = Inches(.78)
    sec.bottom_margin = Inches(.75)
    pie = sec.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = pie.add_run("GEOPREDICT  ·  Validación funcional  |  ")
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor.from_string("4B5563")
    c = OxmlElement("w:fldSimple")
    c.set(qn("w:instr"), "PAGE")
    pie._p.append(c)
    doc.core_properties.title = "Validación funcional del piloto de alertas GEOPREDICT"
    doc.core_properties.subject = "Campaña reproducible de pruebas funcionales"
    doc.core_properties.author = "GEOPREDICT"


def construir(resultados, salida):
    res = leer(resultados/"resumen.json")
    with (resultados/"matriz_resultados.csv").open(encoding="utf-8-sig", newline="") as flujo:
        matriz = list(csv.DictReader(flujo))
    ok, fallo, bloqueo = [res["estados"][k] for k in ("Aprobado", "Fallido", "Bloqueado")]
    ejecutadas = ok + fallo
    tasa = f"{100*ok/ejecutadas:.1f}".replace(".", ",")
    doc = Document()
    estilo(doc)
    doc.add_paragraph("Validación funcional del piloto de alertas GEOPREDICT", style="Title")
    doc.add_heading("Introducción", 1)
    doc.add_paragraph(
        "GEOPREDICT procesa trazas de georradar de una pasada virtual por la Avenida Regional de Medellín. "
        "La ETL integra el CSV con las matrices de señal y la trayectoria. El calibrador compara atributos "
        "locales con una referencia y ordena segmentos de 5 m. Los episodios altos se agrupan en alertas "
        "para revisión técnica y se registran en SQLite.")
    doc.add_paragraph(
        f"La campaña abarcó {len(matriz)} casos. De los {ejecutadas} casos evaluables se registraron "
        f"{ok} aprobaciones y {fallo} fallos. Los bloqueos sumaron {bloqueo}. "
        f"La aprobación sobre casos ejecutados fue {tasa} %. El dictamen funcional es de cumplimiento parcial.")
    doc.add_paragraph(
        "El alcance cubre extracción, reglas de integridad, preprocesamiento causal, carga del calibrador, "
        "puntuación, niveles, alertas, reintentos y persistencia. La puntuación indica desviación de la "
        "referencia GPR. El piloto disponible carece de un horizonte predictivo y de eventos de campo "
        "confirmados para medir anticipación.")
    doc.add_heading("Metodología", 1)
    doc.add_paragraph(
        f"Las pruebas se ejecutaron en {res['entorno']} con Python {res['python']}, pytest, NumPy, "
        "pandas y SQLite. Se usaron verificaciones unitarias de umbral y ventanas, pruebas de integración "
        "entre CSV y NPZ y ejecuciones de extremo a extremo a través de la interfaz de línea de comandos.")
    doc.add_paragraph(
        "Cada pasada de control conserva 334,52 m de recorrido cartográfico, 6.691 trazas a 5 cm y 512 "
        "muestras por traza. Los escenarios usan una forma de onda sintética de referencia con ruido bajo "
        "y perturbaciones reproducibles de amplitud entre 12 y 30 ns, con semilla 42. Los nueve atributos "
        "se recalculan desde la señal salvo en la prueba de discordancia deliberada. Estas perturbaciones "
        "son estímulos funcionales y su posición no representa infraestructura real.")
    doc.add_paragraph(
        "La aceptación se fijó antes de ejecutar cada caso. Se conservaron entradas, salidas, registros de "
        "comandos, huellas y resultados pytest. Las pruebas cargaron el JSON entregado. "
        f"La comparación SHA-256 confirmó la integridad del modelo y la configuración: "
        f"{'sí' if res['huellas_preservadas'] else 'no'}.")
    doc.add_paragraph(
        "La primera corrida reveló dos discrepancias en las aserciones de QA. QA01 esperaba puntuación "
        "en el tramo de arranque, cuya cobertura es 71 %, y QA07 exigía un formato de comillas específico "
        "en el error de pandas. Se actualizaron las aserciones al contrato y se repitió la campaña. "
        "El registro inicial se conserva junto al definitivo.")

    for i, r in enumerate(matriz):
        codigo = r["id"]
        if i % 2 == 0:
            doc.add_page_break()
            if i == 0:
                doc.add_heading("Pruebas individuales", 1)
        nombre, componente, objetivo, justificacion, entrada, paso, esperado = CASOS[codigo]
        carpeta, archivos, cierre = PRUEBAS[codigo]
        ev = leer(resultados/"evidencias"/f"{codigo}.json")
        doc.add_heading(f"{codigo}  {nombre}", 2)
        texto_con_etiqueta(doc, "Componente", componente)
        texto_con_etiqueta(doc, "Objetivo", objetivo)
        texto_con_etiqueta(doc, "Justificación", justificacion)
        texto_con_etiqueta(doc, "Datos de entrada", entrada)
        texto_con_etiqueta(doc, "Procedimiento", paso)
        texto_con_etiqueta(doc, "Resultado esperado", esperado)
        texto_con_etiqueta(doc, "Resultado obtenido", observacion(r["obtenido"]))
        texto_con_etiqueta(doc, "Evidencia", f"{codigo}.json y {archivos}. Ruta lógica {carpeta}.")
        texto_con_etiqueta(doc, "Estado", r["estado"])
        if r["estado"] == "Fallido" and codigo != "QA10":
            cierre = "El criterio se incumplió. El registro de evidencias contiene el detalle del fallo."
        texto_con_etiqueta(doc, "Conclusión individual", cierre)
        if codigo == "QA07":
            controles = ev.get("mediciones", {}).get("controles", {})
            tabla(doc, ["Variante", "Código", "Motivo", "Lotes"],
                  [(k.replace("_", " "), v["salida"], v["causa"].split(": ", 1)[-1],
                    v["manifiestos"]) for k, v in controles.items()],
                  [1.30, .60, 4.08, .70], 8.7)
            doc.add_paragraph()

    sec = doc.add_section(WD_SECTION_START.NEW_PAGE)
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Inches(11), Inches(8.5)
    sec.left_margin = sec.right_margin = Inches(.64)
    sec.top_margin = Inches(.65)
    sec.bottom_margin = Inches(.64)
    doc.add_heading("Matriz consolidada", 1)
    doc.add_paragraph(f"{len(matriz)} casos  ·  {ejecutadas} ejecutados  ·  {ok} aprobaciones  ·  "
                      f"{fallo} fallos  ·  {bloqueo} bloqueos  ·  {tasa} % de aprobación")
    tabla(doc, ["ID", "Prueba", "Componente", "Esperado", "Obtenido", "Estado", "Observaciones"],
          [[r["id"], r["nombre"], r["componente"], esperado, observacion(r["obtenido"]),
            r["estado"], {"Aprobado": "Cumple el criterio.", "Fallido": "Incidencia de integridad.",
                           "Bloqueado": "Sin seguimiento."}[r["estado"]]]
           for r, esperado in zip(matriz, MATRIZ_ESPERADO)], [.49, 1.37, 1.03, 2.12, 2.64, .72, 1.32], 8.5)

    ultima = doc.add_section(WD_SECTION_START.NEW_PAGE)
    ultima.orientation = WD_ORIENT.PORTRAIT
    ultima.page_width, ultima.page_height = Inches(8.5), Inches(11)
    ultima.left_margin = ultima.right_margin = Inches(.84)
    ultima.top_margin = Inches(.78)
    ultima.bottom_margin = Inches(.75)
    doc.add_heading("Conclusiones", 1)
    doc.add_paragraph(
        "El flujo aplicó los controles de archivo, esquema, claves y cobertura evaluados. El modelo "
        "serializado aceptó una pasada temporalmente compatible. Las verificaciones de umbral, alerta "
        "de prioridad máxima y registro de una disminución aportan evidencia sobre la integración "
        "del piloto para revisión GPR.")
    doc.add_heading("Incidencia de integridad", 2)
    doc.add_paragraph(observacion(matriz[9]["obtenido"]))
    doc.add_paragraph(
        "Se recomienda validar al menos los atributos utilizados por el calibrador contra los A-scans "
        "observados antes de puntuar. La verificación debe declarar una tolerancia de cálculo y "
        "serialización y registrar los PK afectados. Una discrepancia fuera de tolerancia debería "
        "bloquear el lote o aislar las trazas afectadas y anular sus alertas. Después debe repetirse QA10 "
        "junto con los controles de datos ausentes y reintentos.")
    doc.add_heading("Límites y cumplimiento", 2)
    doc.add_paragraph(
        "La campaña cubre un solo corredor, un canal, una firma instrumental y estímulos sintéticos "
        "controlados. La comparación de RMS comprueba una relación entre artefactos. La respuesta del "
        "piloto a un estímulo extremo demuestra la asignación de máxima prioridad de revisión según la "
        "política vigente. La validación de criticidad real, anticipación y efectividad predictiva "
        "requiere niveles operativos aprobados, inspecciones fechadas y observaciones longitudinales.")
    doc.add_paragraph(
        "El cumplimiento es parcial por la discordancia de atributos aceptada. La corrección y su "
        "prueba de regresión son condiciones para confiar en la trazabilidad de la evidencia "
        "tabular cuando se utiliza para emitir una alerta.")
    doc.save(salida)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resultados", type=Path)
    parser.add_argument("docx", type=Path)
    args = parser.parse_args()
    construir(args.resultados, args.docx)
