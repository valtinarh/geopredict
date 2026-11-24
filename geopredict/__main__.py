"""Comandos de generación y visualización de radargramas."""

import argparse
from pathlib import Path

import numpy as np

from .simulacion import ESCENAS, generar_lote


def _graficar(archivo: Path, png: Path, limpia: bool) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    campo = "amplitud_limpia" if limpia else "amplitud_perturbada"
    with np.load(archivo) as datos:
        amplitud = datos[campo]
        distancia_m = datos["distancia_m"]
        tiempo_ns = datos["tiempo_ns"]

    dx = distancia_m[1] - distancia_m[0]
    dt = tiempo_ns[1] - tiempo_ns[0]
    limite = np.percentile(np.abs(amplitud), 99)
    figura, eje = plt.subplots(figsize=(10, 5), layout="constrained")
    imagen = eje.imshow(
        amplitud.T,
        extent=(
            distancia_m[0] - dx / 2,
            distancia_m[-1] + dx / 2,
            tiempo_ns[-1] + dt / 2,
            tiempo_ns[0] - dt / 2,
        ),
        aspect="auto",
        cmap="RdBu_r",
        vmin=-limite,
        vmax=limite,
    )
    eje.set(
        title=f"Radargrama sintético · {archivo.stem}",
        xlabel="Distancia (m)",
        ylabel="Tiempo de ida y vuelta (ns)",
    )
    figura.colorbar(imagen, ax=eje, label="Amplitud relativa")
    png.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(png, dpi=150)
    plt.close(figura)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)

    generar = comandos.add_parser("generar", help="Genera las cuatro escenas sintéticas.")
    generar.add_argument("--salida", type=Path, default=Path("gpr_sintetico"))
    generar.add_argument("--semilla", type=int, default=42)

    graficar = comandos.add_parser("graficar", help="Exporta un radargrama como PNG.")
    graficar.add_argument("escena", choices=ESCENAS)
    graficar.add_argument("--datos", type=Path, default=Path("gpr_sintetico"))
    graficar.add_argument("--png", type=Path)
    graficar.add_argument("--limpia", action="store_true")

    args = parser.parse_args()
    if args.comando == "generar":
        if args.semilla < 0:
            generar.error("--semilla debe ser un entero no negativo")
        generar_lote(args.salida, args.semilla)
        print(f"Lote generado en {args.salida.resolve()}")
        return

    archivo = args.datos / f"{args.escena}.npz"
    if not archivo.is_file():
        graficar.error(f"No se encontró {archivo}. Ejecuta primero el comando generar.")
    variante = "limpia" if args.limpia else "perturbada"
    png = args.png or args.datos / f"{args.escena}_{variante}.png"
    _graficar(archivo, png, args.limpia)
    print(f"Radargrama guardado en {png.resolve()}")


if __name__ == "__main__":
    main()
