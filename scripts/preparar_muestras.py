"""Genera las muestras que se suben a S3 (raw/muestras/).

- muestra_esqueleto_1000.csv: las primeras 1 000 órdenes del dataset.
- muestra_danada.csv: 20 órdenes válidas + 14 casos construidos a propósito
  (12 deben ir a cuarentena y 2 son válidos con formato irregular).

Uso (desde la raíz del repositorio):
    python scripts/preparar_muestras.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

COLUMNAS = (
    "id_solicitud",
    "fecha_solicitud",
    "glosa",
    "medio_emisor",
    "valor_procedimiento",
    "entidad_emisora",
)
TAMANO_ESQUELETO = 1000
VALIDAS_EN_MUESTRA_DANADA = 20

# (id, descripción, resultado esperado)
CASOS_DANADOS = (
    ("ERR-01", "glosa sin DNO", "ERROR_PARSEO"),
    ("ERR-02", "glosa sin SeguroSocial", "ERROR_PARSEO"),
    ("ERR-03", "glosa sin PerfilCobertura", "ERROR_PARSEO"),
    ("ERR-04", "glosa sin ServicioSolicitado", "ERROR_PARSEO"),
    ("ERR-05", "glosa vacía", "ERROR_PARSEO"),
    ("ERR-06", "glosa en texto libre, sin formato", "ERROR_PARSEO"),
    ("ERR-07", "valor_procedimiento no numérico", "ERROR_PARSEO"),
    ("ERR-08", "valor_procedimiento negativo", "ERROR_PARSEO"),
    ("ERR-09", "fecha_solicitud inválida", "ERROR_PARSEO"),
    ("", "sin id_solicitud (se registra como SIN_ID)", "ERROR_PARSEO"),
    ("ERR-11", "perfil VIP (fuera de catálogo) con servicio cubierto", "ERROR_PERFIL"),
    ("ERR-12", "perfil PREMIUM (fuera de catálogo) con servicio no cubierto", "ERROR_PERFIL"),
    ("OK-13", "glosa sin Medicacion (debe clasificarse normal)", "VALIDA"),
    ("OK-14", "glosa desordenada, con espacios y perfil en minúscula", "VALIDA"),
)


def _glosa(campos: dict[str, str]) -> str:
    return "; ".join(f"{k}: {v}" for k, v in campos.items())


def construir_muestra_danada(validas: list[dict[str, str]]) -> list[dict[str, str]]:
    """Devuelve las filas válidas recibidas + los 14 casos de CASOS_DANADOS."""
    if len(validas) < 1:
        raise ValueError("Se necesita al menos una fila válida como base")
    base = validas[0]
    campos_base = {
        "Paciente": "Ana Prueba Ruiz",
        "DNO": "DNO-12345678",
        "SeguroSocial": "SS-111-22-3333",
        "Edad": "40",
        "PerfilCobertura": "ESTANDAR",
        "ServicioSolicitado": "Consulta de medicina general",
        "Medicacion": "acetaminofén|ibuprofeno",
    }

    def fila(id_solicitud: str, glosa: str, **cambios: str) -> dict[str, str]:
        nueva = {
            "id_solicitud": id_solicitud,
            "fecha_solicitud": base["fecha_solicitud"],
            "glosa": glosa,
            "medio_emisor": base["medio_emisor"],
            "valor_procedimiento": "50000",
            "entidad_emisora": base["entidad_emisora"],
        }
        nueva.update(cambios)
        return nueva

    def sin(campo: str) -> str:
        return _glosa({k: v for k, v in campos_base.items() if k != campo})

    def con(**cambios: str) -> str:
        return _glosa({**campos_base, **cambios})

    casos = [
        fila("ERR-01", sin("DNO")),
        fila("ERR-02", sin("SeguroSocial")),
        fila("ERR-03", sin("PerfilCobertura")),
        fila("ERR-04", sin("ServicioSolicitado")),
        fila("ERR-05", ""),
        fila("ERR-06", "Paciente requiere consulta urgente, sin datos, revisar"),
        fila("ERR-07", con(), valor_procedimiento="no-aplica"),
        fila("ERR-08", con(), valor_procedimiento="-1500"),
        fila("ERR-09", con(), fecha_solicitud="2026-13-45 10:00:00"),
        fila("", con()),
        fila("ERR-11", con(PerfilCobertura="VIP")),
        fila(
            "ERR-12",
            con(PerfilCobertura="PREMIUM", ServicioSolicitado="Implante capilar"),
        ),
        fila("OK-13", sin("Medicacion")),
        fila(
            "OK-14",
            "  ServicioSolicitado :  Consulta de medicina general ;Medicacion: "
            "omeprazol;  perfilcobertura: estandar ; DNO:  dno-87654321 ; "
            "SeguroSocial: ss-999-88-7777 ; Paciente: Luis Prueba; Edad: 33",
        ),
    ]
    return list(validas) + casos


def leer_primeras(ruta: Path, cantidad: int) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        faltantes = [c for c in COLUMNAS if c not in (lector.fieldnames or [])]
        if faltantes:
            raise ValueError(f"{ruta} no tiene las columnas {faltantes}")
        filas = []
        for fila in lector:
            filas.append({c: fila[c] for c in COLUMNAS})
            if len(filas) >= cantidad:
                break
    return filas


def escribir(ruta: Path, filas: list[dict[str, str]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dataset", default="data/COIL_dataset_glosas_salud_1_2M.csv", type=Path
    )
    parser.add_argument("--salida", default="data/muestras", type=Path)
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(f"No existe {args.dataset}. Copie el dataset en data/.")

    esqueleto = leer_primeras(args.dataset, TAMANO_ESQUELETO)
    escribir(args.salida / "muestra_esqueleto_1000.csv", esqueleto)

    danada = construir_muestra_danada(esqueleto[:VALIDAS_EN_MUESTRA_DANADA])
    escribir(args.salida / "muestra_danada.csv", danada)

    print(f"OK {args.salida / 'muestra_esqueleto_1000.csv'}: {len(esqueleto)} filas")
    print(f"OK {args.salida / 'muestra_danada.csv'}: {len(danada)} filas")
    for id_caso, descripcion, esperado in CASOS_DANADOS:
        print(f"   {id_caso or '(vacío)':8} {esperado:13} {descripcion}")


if __name__ == "__main__":
    main()
