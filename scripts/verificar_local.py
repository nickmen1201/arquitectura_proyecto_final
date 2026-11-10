"""Aplica localmente la misma lógica del job a un CSV y muestra los conteos.

No usa Spark ni AWS. Sirve para:
- confirmar los resultados esperados antes de gastar créditos del laboratorio;
- comparar después con la línea METRICAS de CloudWatch.

Usa una clave de prueba fija: los paciente_hash NO coinciden con los de AWS
(allá la clave está en Secrets Manager), pero los conteos sí.

Uso (desde la raíz del repositorio):
    python scripts/verificar_local.py data/COIL_dataset_glosas_salud_1_2M.csv
    python scripts/verificar_local.py data/muestras/muestra_danada.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_cobertura import (  # noqa: E402
    cargar_catalogo_perfiles,
    cargar_catalogo_servicios,
    contar_resultados,
    procesar_registro,
    verificar_invariante,
)

CLAVE_PRUEBA = b"clave-local-de-prueba-no-usar-en-aws-0000"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv_entrada", type=Path)
    parser.add_argument(
        "--servicios", default="data/COIL_catalogo_servicios_cubiertos.csv", type=Path
    )
    parser.add_argument(
        "--perfiles", default="data/COIL_catalogo_perfiles_cobertura.csv", type=Path
    )
    parser.add_argument(
        "--mostrar-cuarentena", action="store_true", help="lista cada error"
    )
    args = parser.parse_args()

    servicios = cargar_catalogo_servicios(args.servicios.read_text(encoding="utf-8"))
    perfiles = cargar_catalogo_perfiles(args.perfiles.read_text(encoding="utf-8"))

    inicio = time.time()
    resultados = []
    with args.csv_entrada.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            registro = procesar_registro(
                fila, servicios, perfiles, CLAVE_PRUEBA, "verificacion-local"
            )
            resultados.append({"tipo": registro["tipo"], "cubre": registro["cubre"]})
            if args.mostrar_cuarentena and registro["tipo"] == "cuarentena":
                print(f"  {registro['id_solicitud']:10} {registro['cubre']:13} {registro['detalle']}")
    duracion = time.time() - inicio

    conteo = contar_resultados(resultados)
    verificar_invariante(conteo)
    print(json.dumps(conteo, indent=2))
    tasa = conteo["records_input"] / duracion if duracion else 0
    print(f"Tiempo local (1 proceso, sin Spark): {duracion:.1f} s ({tasa:,.0f} órdenes/s)")


if __name__ == "__main__":
    main()
