"""Interfaz de línea de comandos del piloto local."""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path

from .alertas import retroalimentar
from .datos import huella, json_guardar, json_leer
from .evaluacion import evaluar
from .pipeline import calibrar, etl, inferir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("salidas"))
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1]/"config.json")
    comandos = parser.add_subparsers(dest="comando", required=True)
    for nombre in ("etl", "completo"):
        p = comandos.add_parser(nombre)
        p.add_argument("--fuente", type=Path, required=True)
        if nombre == "completo":
            p.add_argument("--verdad-evaluacion", type=Path)
    p = comandos.add_parser("calibrar")
    p.add_argument("--lote", type=Path, required=True)
    p = comandos.add_parser("inferir")
    p.add_argument("--lote", type=Path, required=True)
    p.add_argument("--modelo", type=Path, required=True)
    p = comandos.add_parser("evaluar")
    p.add_argument("--inferencia", type=Path, required=True)
    p.add_argument("--verdad", type=Path, required=True)
    p = comandos.add_parser("retroalimentar")
    p.add_argument("--alerta", required=True)
    p.add_argument("--estado", required=True, choices=["en_revision", "cerrada", "descartada"])
    p.add_argument("--nota", required=True)
    p.add_argument("--evento-id", required=True)
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)sZ %(levelname)s %(name)s %(message)s")
    formato.converter = lambda segundos: datetime.fromtimestamp(segundos, timezone.utc).timetuple()
    for handler in (logging.StreamHandler(),
                    logging.FileHandler(args.salida/"pipeline.log", encoding="utf-8")):
        handler.setFormatter(formato)
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    try:
        if args.comando == "retroalimentar":
            retroalimentar(args.salida/"alertas.sqlite", args.alerta, args.estado, args.nota, args.evento_id)
            return
        if args.comando == "evaluar":
            evaluar(args.inferencia, args.verdad)
            return
        cfg, firma = json_leer(args.config), huella(args.config)
        if args.comando == "etl":
            ruta = etl(args.fuente, args.salida, cfg, firma)
        elif args.comando == "calibrar":
            ruta = calibrar(args.lote, args.salida, cfg, firma)
        elif args.comando == "inferir":
            ruta = inferir(args.lote, args.modelo, args.salida, cfg, firma)
        else:
            lote = etl(args.fuente, args.salida, cfg, firma)
            modelo = calibrar(lote, args.salida, cfg, firma)
            ruta = inferir(lote, modelo, args.salida, cfg, firma)
            if args.verdad_evaluacion:
                evaluar(ruta, args.verdad_evaluacion)
            json_guardar(args.salida/"entrega.json", {
                k: v.relative_to(args.salida).as_posix()
                for k, v in {"etl": lote, "modelo": modelo, "inferencia": ruta}.items()})
        print(ruta.resolve())
    except Exception:
        logging.getLogger(__name__).exception("Falló la etapa %s", args.comando)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
