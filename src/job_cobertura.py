"""Clasificación batch de órdenes médicas (AWS Glue, PySpark).

El archivo tiene dos partes:

1. Lógica de negocio en Python puro (sin Spark ni AWS), probada con pytest:
   GlosaParser, CatalogRepository, CoverageClassifier, PatientPrivacyService.
2. ``main()``: punto de entrada del Glue Job (BatchPipeline). Solo corre en
   Glue; se valida con la ejecución real (ver docs/arquitectura.md, ADR-006).

Contratos de parámetros, esquemas y métricas: docs/contratos.md.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import math
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, Iterable, Iterator

# ---------------------------------------------------------------------------
# Constantes del contrato
# ---------------------------------------------------------------------------

COLUMNAS_ENTRADA = (
    "id_solicitud",
    "fecha_solicitud",
    "glosa",
    "medio_emisor",
    "valor_procedimiento",
    "entidad_emisora",
)

CAMPOS_GLOSA_OBLIGATORIOS = (
    "DNO",
    "SeguroSocial",
    "PerfilCobertura",
    "ServicioSolicitado",
)

# 14 campos de la decisión (FR7). `fecha` es partición en Parquet.
CAMPOS_SALIDA = (
    "id_solicitud",
    "paciente_hash",
    "cubre",
    "porcentaje_cobertura",
    "perfil_cobertura",
    "servicio_solicitado",
    "entidad_emisora",
    "medio_emisor",
    "valor_procedimiento",
    "valor_cubierto",
    "regla_aplicada",
    "run_id",
    "timestamp_proceso",
    "fecha",
)

CAMPOS_CUARENTENA = (
    "id_solicitud",
    "cubre",
    "detalle",
    "fecha_solicitud",
    "run_id",
    "timestamp_proceso",
)

# Orden de columnas del DataFrame unificado que arma el job.
CAMPOS_UNIFICADOS = ("tipo",) + CAMPOS_SALIDA + ("detalle", "fecha_solicitud")

# Deben coincidir con projection.ejecucion.values de la plantilla.
ETIQUETAS_VALIDAS = (
    "esqueleto",
    "muestra_danada",
    "completo_1_2m",
    "escala_12m",
    "diaria",
)

REGLA_CUBRE = "RG-01"
REGLA_NO_CUBRE = "RG-00"
ERROR_PARSEO = "ERROR_PARSEO"
ERROR_PERFIL = "ERROR_PERFIL"
ID_FALTANTE = "SIN_ID"
LONGITUD_MINIMA_CLAVE = 32
FACTOR_MAXIMO = 100

COLUMNA_SERVICIO = "servicio"
COLUMNA_CUBRE = "cubre_sistema_publico"
COLUMNA_PERFIL = "perfil_cobertura"
COLUMNA_PORCENTAJE = "porcentaje_cobertura_si_el_servicio_esta_cubierto"


class ErrorRegistro(Exception):
    """Error de datos de una orden: la orden va a cuarentena."""

    def __init__(self, codigo: str, detalle: str) -> None:
        super().__init__(f"{codigo}: {detalle}")
        self.codigo = codigo
        self.detalle = detalle


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def normalizar_texto(texto: str) -> str:
    """Normaliza para comparar: NFC, sin espacios extremos, sin mayúsculas."""
    return unicodedata.normalize("NFC", texto).strip().casefold()


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


# ---------------------------------------------------------------------------
# GlosaParser
# ---------------------------------------------------------------------------


def parsear_glosa(glosa: str | None) -> dict[str, str]:
    """Extrae los campos de la glosa ``Clave: valor; Clave: valor; ...``.

    Tolera orden distinto, espacios extra y mayúsculas en las claves.
    Lanza ErrorRegistro(ERROR_PARSEO) si falta un campo obligatorio.
    ``Medicacion`` es opcional: su ausencia no envía la orden a cuarentena.
    """
    texto = _texto(glosa)
    if not texto:
        raise ErrorRegistro(ERROR_PARSEO, "glosa vacía")

    claves_conocidas = {
        normalizar_texto(c): c
        for c in (
            "Paciente",
            "DNO",
            "SeguroSocial",
            "Edad",
            "PerfilCobertura",
            "ServicioSolicitado",
            "Medicacion",
        )
    }
    campos: dict[str, str] = {}
    for parte in texto.split(";"):
        clave, separador, valor = parte.partition(":")
        if not separador:
            continue
        nombre = claves_conocidas.get(normalizar_texto(clave))
        if nombre is not None:
            campos[nombre] = valor.strip()

    for obligatorio in CAMPOS_GLOSA_OBLIGATORIOS:
        if not campos.get(obligatorio):
            raise ErrorRegistro(ERROR_PARSEO, f"falta campo {obligatorio}")
    return campos


def convertir_valor(valor: Any) -> float:
    """Convierte valor_procedimiento a float no negativo y finito."""
    texto = _texto(valor)
    try:
        numero = float(texto)
    except ValueError:
        raise ErrorRegistro(
            ERROR_PARSEO, "valor_procedimiento no numérico"
        ) from None
    if math.isnan(numero) or math.isinf(numero) or numero < 0:
        raise ErrorRegistro(ERROR_PARSEO, "valor_procedimiento fuera de rango")
    return numero


def convertir_fecha(valor: Any) -> date:
    """Extrae la fecha (sin hora) de fecha_solicitud."""
    texto = _texto(valor)
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErrorRegistro(ERROR_PARSEO, "fecha_solicitud inválida")


# ---------------------------------------------------------------------------
# CatalogRepository
# ---------------------------------------------------------------------------


def _leer_csv(texto: str, columnas: tuple[str, ...], nombre: str) -> list[dict]:
    lector = csv.DictReader(io.StringIO(texto.lstrip("﻿")))
    encabezado = [c.strip() for c in (lector.fieldnames or [])]
    faltantes = [c for c in columnas if c not in encabezado]
    if faltantes:
        raise ValueError(f"Catálogo {nombre}: faltan columnas {faltantes}")
    return [{k.strip(): v for k, v in fila.items() if k} for fila in lector]


def cargar_catalogo_servicios(texto: str) -> frozenset[str]:
    """Servicios con cubre_sistema_publico = SI, normalizados para comparar."""
    filas = _leer_csv(texto, (COLUMNA_SERVICIO, COLUMNA_CUBRE), "de servicios")
    servicios = frozenset(
        normalizar_texto(f[COLUMNA_SERVICIO])
        for f in filas
        if _texto(f.get(COLUMNA_CUBRE)).upper() == "SI"
        and _texto(f.get(COLUMNA_SERVICIO))
    )
    if not servicios:
        raise ValueError("Catálogo de servicios: no hay servicios cubiertos")
    return servicios


def cargar_catalogo_perfiles(texto: str) -> dict[str, int]:
    """Perfil (en mayúsculas) -> porcentaje de cobertura (0..100)."""
    filas = _leer_csv(texto, (COLUMNA_PERFIL, COLUMNA_PORCENTAJE), "de perfiles")
    perfiles: dict[str, int] = {}
    for fila in filas:
        perfil = _texto(fila.get(COLUMNA_PERFIL)).upper()
        if not perfil:
            continue
        try:
            porcentaje = int(_texto(fila.get(COLUMNA_PORCENTAJE)))
        except ValueError:
            raise ValueError(
                f"Catálogo de perfiles: porcentaje inválido para {perfil}"
            ) from None
        if not 0 <= porcentaje <= 100:
            raise ValueError(f"Catálogo de perfiles: porcentaje fuera de 0..100 ({perfil})")
        perfiles[perfil] = porcentaje
    if not perfiles:
        raise ValueError("Catálogo de perfiles: vacío")
    return perfiles


# ---------------------------------------------------------------------------
# CoverageClassifier
# ---------------------------------------------------------------------------


def clasificar(
    perfil: str,
    servicio: str,
    valor_procedimiento: float,
    servicios_cubiertos: frozenset[str],
    perfiles: dict[str, int],
) -> dict[str, Any]:
    """Regla FR4. El perfil se valida antes que el servicio (ADR-007)."""
    clave_perfil = _texto(perfil).upper()
    if clave_perfil not in perfiles:
        raise ErrorRegistro(ERROR_PERFIL, f"perfil fuera de catálogo: {clave_perfil}")
    if normalizar_texto(servicio) in servicios_cubiertos:
        porcentaje = perfiles[clave_perfil]
        return {
            "cubre": "SI",
            "porcentaje_cobertura": porcentaje,
            "regla_aplicada": REGLA_CUBRE,
            "valor_cubierto": round(valor_procedimiento * porcentaje / 100, 2),
        }
    return {
        "cubre": "NO",
        "porcentaje_cobertura": 0,
        "regla_aplicada": REGLA_NO_CUBRE,
        "valor_cubierto": 0.0,
    }


# ---------------------------------------------------------------------------
# PatientPrivacyService
# ---------------------------------------------------------------------------


def seudonimizar(dno: str, seguro_social: str, clave: bytes) -> str:
    """HMAC-SHA-256(clave, upper(trim(DNO)) + '|' + upper(trim(SeguroSocial)))."""
    mensaje = f"{_texto(dno).upper()}|{_texto(seguro_social).upper()}"
    return hmac.new(clave, mensaje.encode("utf-8"), hashlib.sha256).hexdigest()


def extraer_clave(secret_string: str | None) -> bytes:
    """Extrae la clave del JSON del secreto: {"clave": "..."}.

    Los mensajes de error nunca incluyen el contenido del secreto.
    """
    if not secret_string:
        raise ValueError("El secreto no tiene SecretString")
    try:
        datos = json.loads(secret_string)
    except json.JSONDecodeError:
        raise ValueError("El secreto no es un JSON válido") from None
    clave = datos.get("clave") if isinstance(datos, dict) else None
    if not isinstance(clave, str) or len(clave) < LONGITUD_MINIMA_CLAVE:
        raise ValueError(
            f"El secreto no tiene un campo 'clave' de al menos "
            f"{LONGITUD_MINIMA_CLAVE} caracteres"
        )
    return clave.encode("utf-8")


def obtener_clave(cliente_secrets: Any, secret_id: str) -> bytes:
    """Lee la clave desde Secrets Manager (una llamada). Falla de inmediato."""
    try:
        respuesta = cliente_secrets.get_secret_value(SecretId=secret_id)
    except Exception as error:  # noqa: BLE001 - se re-lanza con contexto
        raise RuntimeError(
            f"No se pudo leer el secreto {secret_id}: {type(error).__name__}. "
            "Verifique que el secreto exista y que el rol del job tenga "
            "secretsmanager:GetSecretValue."
        ) from error
    return extraer_clave(respuesta.get("SecretString"))


# ---------------------------------------------------------------------------
# Procesamiento por orden (lo que Spark aplica en cada partición)
# ---------------------------------------------------------------------------


def procesar_registro(
    fila: dict[str, Any],
    servicios_cubiertos: frozenset[str],
    perfiles: dict[str, int],
    clave: bytes,
    run_id: str,
    ahora: datetime | None = None,
) -> dict[str, Any]:
    """Procesa una orden y devuelve un dict con CAMPOS_UNIFICADOS.

    ``tipo`` es "ok" (va a curated/) o "cuarentena" (va a quarantine/).
    Ningún campo con datos personales (nombre, DNO, seguro social, glosa)
    sale de esta función.
    """
    marca = ahora or datetime.now(timezone.utc)
    id_solicitud = _texto(fila.get("id_solicitud"))
    resultado: dict[str, Any] = {campo: None for campo in CAMPOS_UNIFICADOS}
    resultado.update(
        id_solicitud=id_solicitud or ID_FALTANTE,
        run_id=run_id,
        timestamp_proceso=marca,
        fecha_solicitud=_texto(fila.get("fecha_solicitud")) or None,
    )
    try:
        if not id_solicitud:
            raise ErrorRegistro(ERROR_PARSEO, "falta id_solicitud")
        glosa = parsear_glosa(fila.get("glosa"))
        valor = convertir_valor(fila.get("valor_procedimiento"))
        fecha = convertir_fecha(fila.get("fecha_solicitud"))
        decision = clasificar(
            glosa["PerfilCobertura"],
            glosa["ServicioSolicitado"],
            valor,
            servicios_cubiertos,
            perfiles,
        )
    except ErrorRegistro as error:
        resultado.update(tipo="cuarentena", cubre=error.codigo, detalle=error.detalle)
        return resultado

    resultado.update(
        tipo="ok",
        paciente_hash=seudonimizar(glosa["DNO"], glosa["SeguroSocial"], clave),
        perfil_cobertura=glosa["PerfilCobertura"].strip().upper(),
        servicio_solicitado=glosa["ServicioSolicitado"].strip(),
        entidad_emisora=_texto(fila.get("entidad_emisora")) or None,
        medio_emisor=_texto(fila.get("medio_emisor")) or None,
        valor_procedimiento=valor,
        fecha=fecha,
        **decision,
    )
    return resultado


def procesar_particion(
    filas: Iterable[dict[str, Any]],
    servicios_cubiertos: frozenset[str],
    perfiles: dict[str, int],
    clave: bytes,
    run_id: str,
) -> Iterator[tuple]:
    """Aplica procesar_registro a una partición y devuelve tuplas ordenadas."""
    for fila in filas:
        registro = procesar_registro(fila, servicios_cubiertos, perfiles, clave, run_id)
        yield tuple(registro[campo] for campo in CAMPOS_UNIFICADOS)


def contar_resultados(registros: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Conteos de control con los mismos nombres que la línea METRICAS."""
    conteo = {
        "records_input": 0,
        "records_output": 0,
        "records_cubre_si": 0,
        "records_cubre_no": 0,
        "records_quarantined_parseo": 0,
        "records_quarantined_perfil": 0,
    }
    for registro in registros:
        conteo["records_input"] += 1
        cubre = registro["cubre"]
        if registro["tipo"] == "ok":
            conteo["records_output"] += 1
            conteo["records_cubre_si" if cubre == "SI" else "records_cubre_no"] += 1
        elif cubre == ERROR_PARSEO:
            conteo["records_quarantined_parseo"] += 1
        else:
            conteo["records_quarantined_perfil"] += 1
    return conteo


def verificar_invariante(conteo: dict[str, int]) -> None:
    """records_input = records_output + cuarentena (NFR1). Si no, falla."""
    salida = (
        conteo["records_output"]
        + conteo["records_quarantined_parseo"]
        + conteo["records_quarantined_perfil"]
    )
    if conteo["records_input"] != salida:
        raise RuntimeError(
            f"Invariante incumplido: entrada={conteo['records_input']} "
            f"salida+cuarentena={salida}"
        )


def linea_metricas(metricas: dict[str, Any]) -> str:
    """Línea única que se busca en CloudWatch (prefijo fijo METRICAS)."""
    return "METRICAS " + json.dumps(metricas, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Parámetros y S3
# ---------------------------------------------------------------------------


def validar_parametros(etiqueta: str, factor: str) -> int:
    """Valida etiqueta_ejecucion y factor_replicacion; devuelve el factor."""
    if etiqueta not in ETIQUETAS_VALIDAS:
        raise ValueError(
            f"etiqueta_ejecucion '{etiqueta}' no válida; use una de {ETIQUETAS_VALIDAS}"
        )
    try:
        valor = int(factor)
    except ValueError:
        raise ValueError("factor_replicacion debe ser un entero") from None
    if not 1 <= valor <= FACTOR_MAXIMO:
        raise ValueError(f"factor_replicacion debe estar entre 1 y {FACTOR_MAXIMO}")
    return valor


def dividir_uri_s3(uri: str) -> tuple[str, str]:
    """'s3://bucket/ruta/archivo' -> ('bucket', 'ruta/archivo')."""
    if not uri.startswith("s3://"):
        raise ValueError(f"URI S3 no válida: {uri}")
    bucket, _, llave = uri[len("s3://") :].partition("/")
    if not bucket or not llave:
        raise ValueError(f"URI S3 no válida: {uri}")
    return bucket, llave


def leer_texto_s3(cliente_s3: Any, uri: str) -> str:
    """Lee un archivo de texto UTF-8 desde S3."""
    bucket, llave = dividir_uri_s3(uri)
    try:
        respuesta = cliente_s3.get_object(Bucket=bucket, Key=llave)
    except Exception as error:  # noqa: BLE001 - se re-lanza con contexto
        raise RuntimeError(
            f"No se pudo leer {uri}: {type(error).__name__}. "
            "Verifique que el archivo esté subido en esa ruta."
        ) from error
    return respuesta["Body"].read().decode("utf-8")


def region_de_arn(arn: str) -> str | None:
    """Región de un ARN (arn:aws:servicio:REGION:...), o None."""
    partes = arn.split(":")
    return partes[3] if len(partes) > 3 and partes[0] == "arn" and partes[3] else None


# ---------------------------------------------------------------------------
# BatchPipeline: punto de entrada del Glue Job
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover - solo corre en AWS Glue
    import sys
    import time
    import uuid

    import boto3
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions
    from pyspark import StorageLevel
    from pyspark.context import SparkContext
    from pyspark.sql import functions as F
    from pyspark.sql import types as T

    inicio = time.time()
    args = getResolvedOptions(
        sys.argv,
        [
            "JOB_NAME",
            "input_path",
            "catalog_services_path",
            "catalog_profiles_path",
            "output_path",
            "quarantine_path",
            "secret_id",
            "factor_replicacion",
            "etiqueta_ejecucion",
        ],
    )
    etiqueta = args["etiqueta_ejecucion"]
    factor = validar_parametros(etiqueta, args["factor_replicacion"])

    sc = SparkContext.getOrCreate()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    run_id = str(uuid.uuid4())
    print(f"INICIO run_id={run_id} ejecucion={etiqueta} factor={factor}", flush=True)

    # 1. Clave y catálogos (driver, una sola vez). Si algo falla, el job termina.
    cliente_secrets = boto3.client(
        "secretsmanager", region_name=region_de_arn(args["secret_id"])
    )
    clave = obtener_clave(cliente_secrets, args["secret_id"])
    cliente_s3 = boto3.client("s3")
    servicios = cargar_catalogo_servicios(
        leer_texto_s3(cliente_s3, args["catalog_services_path"])
    )
    perfiles = cargar_catalogo_perfiles(
        leer_texto_s3(cliente_s3, args["catalog_profiles_path"])
    )
    print(
        f"CATALOGOS servicios_cubiertos={len(servicios)} perfiles={sorted(perfiles)}",
        flush=True,
    )
    difusion = sc.broadcast((servicios, perfiles, clave))

    # 2. Lectura del CSV (todo como texto).
    entrada = (
        spark.read.option("header", True)
        .option("encoding", "UTF-8")
        .option("quote", '"')
        .option("escape", '"')
        .option("mode", "PERMISSIVE")
        .csv(args["input_path"])
    )
    faltantes = [c for c in COLUMNAS_ENTRADA if c not in entrada.columns]
    if faltantes:
        raise RuntimeError(f"El CSV de entrada no tiene las columnas {faltantes}")
    entrada = entrada.select(*COLUMNAS_ENTRADA)

    # 3. Replicación para la prueba de escala (FR8).
    if factor > 1:
        copias = spark.range(factor).withColumnRenamed("id", "copia")
        entrada = (
            entrada.crossJoin(F.broadcast(copias))
            .withColumn(
                "id_solicitud",
                F.when(F.col("copia") == 0, F.col("id_solicitud")).otherwise(
                    F.concat(
                        F.col("id_solicitud"),
                        F.lit("-R"),
                        F.lpad(F.col("copia").cast("string"), 2, "0"),
                    )
                ),
            )
            .drop("copia")
        )

    particiones = max(sc.defaultParallelism * 2, 2)
    entrada = entrada.repartition(particiones)
    records_input = entrada.count()

    # 4. Clasificación por partición con la lógica en Python puro (ADR-006).
    def _procesar(filas):
        servicios_b, perfiles_b, clave_b = difusion.value
        return procesar_particion(
            (f.asDict() for f in filas), servicios_b, perfiles_b, clave_b, run_id
        )

    texto = T.StringType()
    esquema = T.StructType(
        [
            T.StructField("tipo", texto),
            T.StructField("id_solicitud", texto),
            T.StructField("paciente_hash", texto),
            T.StructField("cubre", texto),
            T.StructField("porcentaje_cobertura", T.IntegerType()),
            T.StructField("perfil_cobertura", texto),
            T.StructField("servicio_solicitado", texto),
            T.StructField("entidad_emisora", texto),
            T.StructField("medio_emisor", texto),
            T.StructField("valor_procedimiento", T.DoubleType()),
            T.StructField("valor_cubierto", T.DoubleType()),
            T.StructField("regla_aplicada", texto),
            T.StructField("run_id", texto),
            T.StructField("timestamp_proceso", T.TimestampType()),
            T.StructField("fecha", T.DateType()),
            T.StructField("detalle", texto),
            T.StructField("fecha_solicitud", texto),
        ]
    )
    assert tuple(f.name for f in esquema.fields) == CAMPOS_UNIFICADOS
    unificado = spark.createDataFrame(entrada.rdd.mapPartitions(_procesar), esquema)
    unificado = unificado.persist(StorageLevel.MEMORY_AND_DISK)

    # 5. Conteos de control antes de escribir (NFR1).
    conteo = {
        "records_input": records_input,
        "records_output": 0,
        "records_cubre_si": 0,
        "records_cubre_no": 0,
        "records_quarantined_parseo": 0,
        "records_quarantined_perfil": 0,
    }
    for fila in unificado.groupBy("tipo", "cubre").count().collect():
        n = fila["count"]
        if fila["tipo"] == "ok":
            conteo["records_output"] += n
            clave_conteo = "records_cubre_si" if fila["cubre"] == "SI" else "records_cubre_no"
            conteo[clave_conteo] += n
        elif fila["cubre"] == ERROR_PARSEO:
            conteo["records_quarantined_parseo"] += n
        else:
            conteo["records_quarantined_perfil"] += n
    verificar_invariante(conteo)

    # 6. Escritura: particiones por ejecución (y fecha en curated/).
    etiqueta_col = F.lit(etiqueta)
    (
        unificado.filter(F.col("tipo") == "ok")
        .select(*CAMPOS_SALIDA)
        .withColumn("ejecucion", etiqueta_col)
        .write.mode("overwrite")
        .partitionBy("ejecucion", "fecha")
        .parquet(args["output_path"])
    )
    cuarentena = unificado.filter(F.col("tipo") == "cuarentena").select(
        *CAMPOS_CUARENTENA
    )
    if conteo["records_quarantined_parseo"] + conteo["records_quarantined_perfil"] > 0:
        (
            cuarentena.withColumn("ejecucion", etiqueta_col)
            .write.mode("overwrite")
            .partitionBy("ejecucion")
            .parquet(args["quarantine_path"])
        )
    unificado.unpersist()

    # 7. Métricas para CloudWatch (stdout -> /aws-glue/jobs/output).
    metricas = dict(
        conteo,
        run_id=run_id,
        ejecucion=etiqueta,
        factor_replicacion=factor,
        paralelismo=sc.defaultParallelism,
        particiones=particiones,
        duration_seconds=round(time.time() - inicio, 1),
    )
    linea = linea_metricas(metricas)
    print(linea, flush=True)
    print(linea, file=sys.stderr, flush=True)
    job.commit()


if __name__ == "__main__":  # pragma: no cover
    main()
