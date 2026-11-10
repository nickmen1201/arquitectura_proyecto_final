"""Pruebas de la lógica de negocio del job (Python puro, sin Spark ni AWS)."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import job_cobertura as jc
from preparar_muestras import CASOS_DANADOS, construir_muestra_danada

FIXTURES = Path(__file__).parent / "fixtures"
CLAVE = b"k" * 40
OTRA_CLAVE = b"z" * 40
AHORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def servicios() -> frozenset[str]:
    texto = (FIXTURES / "COIL_catalogo_servicios_cubiertos.csv").read_text("utf-8")
    return jc.cargar_catalogo_servicios(texto)


@pytest.fixture(scope="module")
def perfiles() -> dict[str, int]:
    texto = (FIXTURES / "COIL_catalogo_perfiles_cobertura.csv").read_text("utf-8")
    return jc.cargar_catalogo_perfiles(texto)


@pytest.fixture(scope="module")
def nombres_servicios() -> list[str]:
    texto = (FIXTURES / "COIL_catalogo_servicios_cubiertos.csv").read_text("utf-8")
    return [f["servicio"] for f in csv.DictReader(io.StringIO(texto))]


def glosa(**cambios: str | None) -> str:
    campos = {
        "Paciente": "Paula Vargas Ramírez",
        "DNO": "DNO-23291911",
        "SeguroSocial": "SS-173-47-2763",
        "Edad": "14",
        "PerfilCobertura": "ESTANDAR",
        "ServicioSolicitado": "Terapia física ambulatoria",
        "Medicacion": "acetaminofén|naproxeno",
    }
    campos.update(cambios)
    return "; ".join(f"{k}: {v}" for k, v in campos.items() if v is not None)


def fila(**cambios: str | None) -> dict[str, str | None]:
    base = {
        "id_solicitud": "CHV-0000001",
        "fecha_solicitud": "2026-05-06 10:09:31",
        "glosa": glosa(),
        "medio_emisor": "Farmacia Aliada",
        "valor_procedimiento": "84617",
        "entidad_emisora": "Unidad de Salud Valle Claro",
    }
    base.update(cambios)
    return base


def procesar(registro, servicios, perfiles, clave=CLAVE):
    return jc.procesar_registro(registro, servicios, perfiles, clave, "run-1", AHORA)


# --------------------------------------------------------------------- glosa


class TestParsearGlosa:
    def test_extrae_campos_de_una_glosa_real(self):
        campos = jc.parsear_glosa(glosa())
        assert campos["DNO"] == "DNO-23291911"
        assert campos["PerfilCobertura"] == "ESTANDAR"
        assert campos["ServicioSolicitado"] == "Terapia física ambulatoria"
        assert campos["Medicacion"] == "acetaminofén|naproxeno"

    def test_tolera_orden_espacios_y_mayusculas_en_claves(self):
        texto = "  servicioSOLICITADO :  Hemograma completo ; dno:DNO-1;SeguroSocial: SS-2 ; PerfilCobertura:COPAGO"
        campos = jc.parsear_glosa(texto)
        assert campos["ServicioSolicitado"] == "Hemograma completo"
        assert campos["DNO"] == "DNO-1"
        assert campos["PerfilCobertura"] == "COPAGO"

    @pytest.mark.parametrize("faltante", jc.CAMPOS_GLOSA_OBLIGATORIOS)
    def test_campo_obligatorio_ausente_es_error_parseo(self, faltante):
        with pytest.raises(jc.ErrorRegistro) as error:
            jc.parsear_glosa(glosa(**{faltante: None}))
        assert error.value.codigo == jc.ERROR_PARSEO
        assert faltante in error.value.detalle

    def test_campo_obligatorio_vacio_es_error_parseo(self):
        with pytest.raises(jc.ErrorRegistro):
            jc.parsear_glosa(glosa(DNO=""))

    @pytest.mark.parametrize("valor", [None, "", "   "])
    def test_glosa_vacia(self, valor):
        with pytest.raises(jc.ErrorRegistro, match="glosa vacía"):
            jc.parsear_glosa(valor)

    def test_texto_libre_sin_formato(self):
        with pytest.raises(jc.ErrorRegistro):
            jc.parsear_glosa("Paciente requiere consulta, sin datos")

    def test_sin_medicacion_no_es_error(self):
        campos = jc.parsear_glosa(glosa(Medicacion=None))
        assert "Medicacion" not in campos


class TestConversiones:
    @pytest.mark.parametrize("texto,esperado", [("84617", 84617.0), (" 1500.5 ", 1500.5), ("0", 0.0)])
    def test_valor_valido(self, texto, esperado):
        assert jc.convertir_valor(texto) == esperado

    @pytest.mark.parametrize("texto", ["no-aplica", "", None, "-1", "nan", "inf"])
    def test_valor_invalido(self, texto):
        with pytest.raises(jc.ErrorRegistro) as error:
            jc.convertir_valor(texto)
        assert error.value.codigo == jc.ERROR_PARSEO

    @pytest.mark.parametrize(
        "texto", ["2026-05-06 10:09:31", "2026-05-06T10:09:31", "2026-05-06"]
    )
    def test_fecha_valida(self, texto):
        assert jc.convertir_fecha(texto) == date(2026, 5, 6)

    @pytest.mark.parametrize("texto", ["2026-13-45 10:00:00", "", None, "06/05/2026"])
    def test_fecha_invalida(self, texto):
        with pytest.raises(jc.ErrorRegistro, match="fecha_solicitud"):
            jc.convertir_fecha(texto)


# ----------------------------------------------------------------- catálogos


class TestCatalogos:
    def test_carga_los_catalogos_reales(self, servicios, perfiles):
        assert len(servicios) == 20
        assert perfiles == {"PRIORITARIO": 100, "ESTANDAR": 50, "COPAGO": 25}

    def test_excluye_servicios_que_no_cubre_el_sistema(self):
        texto = "servicio,cubre_sistema_publico\nA,SI\nB,NO\nC, si \n"
        assert jc.cargar_catalogo_servicios(texto) == frozenset({"a", "c"})

    def test_tolera_bom(self):
        texto = "﻿servicio,cubre_sistema_publico\nA,SI\n"
        assert jc.cargar_catalogo_servicios(texto) == frozenset({"a"})

    def test_columna_faltante(self):
        with pytest.raises(ValueError, match="faltan columnas"):
            jc.cargar_catalogo_servicios("nombre_servicio,cubre_sistema_publico\nA,SI\n")

    def test_sin_servicios_cubiertos(self):
        with pytest.raises(ValueError, match="no hay servicios"):
            jc.cargar_catalogo_servicios("servicio,cubre_sistema_publico\nA,NO\n")

    def test_perfil_con_porcentaje_invalido(self):
        texto = f"{jc.COLUMNA_PERFIL},{jc.COLUMNA_PORCENTAJE}\nX,cien\n"
        with pytest.raises(ValueError, match="porcentaje inválido"):
            jc.cargar_catalogo_perfiles(texto)

    def test_perfil_con_porcentaje_fuera_de_rango(self):
        texto = f"{jc.COLUMNA_PERFIL},{jc.COLUMNA_PORCENTAJE}\nX,150\n"
        with pytest.raises(ValueError, match="fuera de 0..100"):
            jc.cargar_catalogo_perfiles(texto)

    def test_catalogo_de_perfiles_vacio(self):
        with pytest.raises(ValueError, match="vacío"):
            jc.cargar_catalogo_perfiles(f"{jc.COLUMNA_PERFIL},{jc.COLUMNA_PORCENTAJE}\n,\n")


# ------------------------------------------------------------- clasificación


class TestClasificar:
    def test_tabla_de_verdad_completa(self, servicios, perfiles, nombres_servicios):
        """Las 20 x 3 combinaciones cubiertas dan el porcentaje del perfil."""
        for servicio in nombres_servicios:
            for perfil, porcentaje in perfiles.items():
                decision = jc.clasificar(perfil, servicio, 1000.0, servicios, perfiles)
                assert decision == {
                    "cubre": "SI",
                    "porcentaje_cobertura": porcentaje,
                    "regla_aplicada": "RG-01",
                    "valor_cubierto": 1000.0 * porcentaje / 100,
                }

    @pytest.mark.parametrize("perfil", ["PRIORITARIO", "ESTANDAR", "COPAGO"])
    def test_servicio_no_cubierto_da_cero(self, servicios, perfiles, perfil):
        decision = jc.clasificar(perfil, "Implante capilar", 903765.0, servicios, perfiles)
        assert decision == {
            "cubre": "NO",
            "porcentaje_cobertura": 0,
            "regla_aplicada": "RG-00",
            "valor_cubierto": 0.0,
        }

    def test_perfil_desconocido_se_valida_antes_que_el_servicio(self, servicios, perfiles):
        for servicio in ("Hemograma completo", "Implante capilar"):
            with pytest.raises(jc.ErrorRegistro) as error:
                jc.clasificar("VIP", servicio, 1.0, servicios, perfiles)
            assert error.value.codigo == jc.ERROR_PERFIL

    def test_ignora_mayusculas_y_espacios(self, servicios, perfiles):
        decision = jc.clasificar(" copago ", "  HEMOGRAMA completo ", 100.0, servicios, perfiles)
        assert decision["cubre"] == "SI"
        assert decision["porcentaje_cobertura"] == 25

    def test_redondea_valor_cubierto(self, servicios, perfiles):
        decision = jc.clasificar("COPAGO", "Hemograma completo", 33333.33, servicios, perfiles)
        assert decision["valor_cubierto"] == 8333.33


# ------------------------------------------------------------- privacidad


class TestSeudonimizar:
    def test_es_hmac_sha256_hexadecimal(self):
        resultado = jc.seudonimizar("DNO-1", "SS-2", CLAVE)
        esperado = hmac.new(CLAVE, b"DNO-1|SS-2", hashlib.sha256).hexdigest()
        assert resultado == esperado
        assert len(resultado) == 64 and resultado == resultado.lower()

    def test_no_es_un_sha256_sin_clave(self):
        sin_clave = hashlib.sha256(b"DNO-1|SS-2").hexdigest()
        assert jc.seudonimizar("DNO-1", "SS-2", CLAVE) != sin_clave

    def test_otra_clave_da_otro_resultado(self):
        assert jc.seudonimizar("DNO-1", "SS-2", CLAVE) != jc.seudonimizar(
            "DNO-1", "SS-2", OTRA_CLAVE
        )

    def test_normaliza_espacios_y_mayusculas(self):
        assert jc.seudonimizar(" dno-1 ", "ss-2 ", CLAVE) == jc.seudonimizar(
            "DNO-1", "SS-2", CLAVE
        )

    def test_separador_evita_colisiones_de_limite(self):
        assert jc.seudonimizar("AB", "CD", CLAVE) != jc.seudonimizar("A", "BCD", CLAVE)


class TestClaveSecreta:
    def test_extrae_clave_del_json(self):
        assert jc.extraer_clave(json.dumps({"clave": "x" * 64})) == b"x" * 64

    @pytest.mark.parametrize(
        "contenido",
        [None, "", "no-es-json", "[]", json.dumps({"otra": "x" * 64}), json.dumps({"clave": "corta"})],
    )
    def test_secreto_invalido(self, contenido):
        with pytest.raises(ValueError):
            jc.extraer_clave(contenido)

    def test_mensaje_de_error_no_revela_el_secreto(self):
        with pytest.raises(ValueError) as error:
            jc.extraer_clave(json.dumps({"clave": "valor-confidencial"}))
        assert "valor-confidencial" not in str(error.value)

    def test_obtener_clave_con_cliente(self):
        class Cliente:
            def get_secret_value(self, SecretId):
                assert SecretId == "arn:aws:secretsmanager:us-east-1:1:secret:x"
                return {"SecretString": json.dumps({"clave": "q" * 64})}

        assert jc.obtener_clave(Cliente(), "arn:aws:secretsmanager:us-east-1:1:secret:x") == b"q" * 64

    def test_obtener_clave_falla_con_mensaje_claro(self):
        class Cliente:
            def get_secret_value(self, SecretId):
                raise PermissionError("AccessDenied")

        with pytest.raises(RuntimeError, match="GetSecretValue"):
            jc.obtener_clave(Cliente(), "mi-secreto")

    def test_region_de_arn(self):
        assert jc.region_de_arn("arn:aws:secretsmanager:us-east-1:123:secret:a") == "us-east-1"
        assert jc.region_de_arn("mi-secreto") is None


# --------------------------------------------------------------- por orden


class TestProcesarRegistro:
    def test_orden_valida_produce_los_14_campos_sin_pii(self, servicios, perfiles):
        r = procesar(fila(), servicios, perfiles)
        assert r["tipo"] == "ok"
        assert set(jc.CAMPOS_SALIDA) <= set(r)
        salida = {c: r[c] for c in jc.CAMPOS_SALIDA}
        assert all(v is not None for v in salida.values())
        assert salida == {
            "id_solicitud": "CHV-0000001",
            "paciente_hash": jc.seudonimizar("DNO-23291911", "SS-173-47-2763", CLAVE),
            "cubre": "SI",
            "porcentaje_cobertura": 50,
            "perfil_cobertura": "ESTANDAR",
            "servicio_solicitado": "Terapia física ambulatoria",
            "entidad_emisora": "Unidad de Salud Valle Claro",
            "medio_emisor": "Farmacia Aliada",
            "valor_procedimiento": 84617.0,
            "valor_cubierto": 42308.5,
            "regla_aplicada": "RG-01",
            "run_id": "run-1",
            "timestamp_proceso": AHORA,
            "fecha": date(2026, 5, 6),
        }
        texto = json.dumps(r, default=str)
        for dato_personal in ("Paula", "Vargas", "DNO-23291911", "SS-173-47-2763"):
            assert dato_personal not in texto

    def test_servicio_no_cubierto(self, servicios, perfiles):
        r = procesar(fila(glosa=glosa(ServicioSolicitado="Implante capilar")), servicios, perfiles)
        assert (r["tipo"], r["cubre"], r["porcentaje_cobertura"], r["valor_cubierto"]) == (
            "ok", "NO", 0, 0.0,
        )

    @pytest.mark.parametrize(
        "cambios,codigo,detalle",
        [
            ({"glosa": glosa(DNO=None)}, "ERROR_PARSEO", "falta campo DNO"),
            ({"glosa": ""}, "ERROR_PARSEO", "glosa vacía"),
            ({"valor_procedimiento": "abc"}, "ERROR_PARSEO", "no numérico"),
            ({"fecha_solicitud": "mal"}, "ERROR_PARSEO", "fecha_solicitud"),
            ({"glosa": glosa(PerfilCobertura="VIP")}, "ERROR_PERFIL", "VIP"),
        ],
    )
    def test_errores_van_a_cuarentena(self, servicios, perfiles, cambios, codigo, detalle):
        r = procesar(fila(**cambios), servicios, perfiles)
        assert r["tipo"] == "cuarentena"
        assert r["cubre"] == codigo
        assert detalle in r["detalle"]
        assert r["id_solicitud"] == "CHV-0000001"
        assert r["paciente_hash"] is None
        assert r["run_id"] == "run-1"

    @pytest.mark.parametrize("valor", [None, "", "  "])
    def test_sin_id_se_registra_como_sin_id(self, servicios, perfiles, valor):
        r = procesar(fila(id_solicitud=valor), servicios, perfiles)
        assert (r["tipo"], r["id_solicitud"], r["cubre"]) == ("cuarentena", "SIN_ID", "ERROR_PARSEO")

    def test_usa_hora_actual_si_no_se_indica(self, servicios, perfiles):
        r = jc.procesar_registro(fila(), servicios, perfiles, CLAVE, "run-1")
        assert r["timestamp_proceso"].tzinfo is not None

    def test_procesar_particion_devuelve_tuplas_en_orden(self, servicios, perfiles):
        tuplas = list(jc.procesar_particion([fila(), fila(glosa="")], servicios, perfiles, CLAVE, "r"))
        assert len(tuplas) == 2
        assert all(len(t) == len(jc.CAMPOS_UNIFICADOS) for t in tuplas)
        assert tuplas[0][jc.CAMPOS_UNIFICADOS.index("tipo")] == "ok"
        assert tuplas[1][jc.CAMPOS_UNIFICADOS.index("cubre")] == "ERROR_PARSEO"


# ------------------------------------------------ conteos, métricas, params


class TestControl:
    def test_contar_y_verificar(self, servicios, perfiles):
        filas = [
            fila(),
            fila(glosa=glosa(ServicioSolicitado="Implante capilar")),
            fila(glosa=""),
            fila(glosa=glosa(PerfilCobertura="VIP")),
        ]
        conteo = jc.contar_resultados(procesar(f, servicios, perfiles) for f in filas)
        assert conteo == {
            "records_input": 4,
            "records_output": 2,
            "records_cubre_si": 1,
            "records_cubre_no": 1,
            "records_quarantined_parseo": 1,
            "records_quarantined_perfil": 1,
        }
        jc.verificar_invariante(conteo)

    def test_invariante_incumplido(self):
        conteo = dict.fromkeys(
            ("records_output", "records_quarantined_parseo", "records_quarantined_perfil"), 1
        )
        conteo["records_input"] = 5
        with pytest.raises(RuntimeError, match="Invariante"):
            jc.verificar_invariante(conteo)

    def test_linea_metricas(self):
        linea = jc.linea_metricas({"run_id": "r", "records_input": 3})
        assert linea.startswith("METRICAS ")
        assert json.loads(linea[len("METRICAS ") :]) == {"records_input": 3, "run_id": "r"}

    @pytest.mark.parametrize("etiqueta", jc.ETIQUETAS_VALIDAS)
    def test_parametros_validos(self, etiqueta):
        assert jc.validar_parametros(etiqueta, "10") == 10

    @pytest.mark.parametrize(
        "etiqueta,factor,mensaje",
        [("otra", "1", "etiqueta"), ("esqueleto", "x", "entero"), ("esqueleto", "0", "entre"), ("esqueleto", "101", "entre")],
    )
    def test_parametros_invalidos(self, etiqueta, factor, mensaje):
        with pytest.raises(ValueError, match=mensaje):
            jc.validar_parametros(etiqueta, factor)


class TestS3:
    def test_dividir_uri(self):
        assert jc.dividir_uri_s3("s3://b/catalogs/x.csv") == ("b", "catalogs/x.csv")

    @pytest.mark.parametrize("uri", ["http://b/x", "s3://b", "s3:///x", "s3://b/"])
    def test_uri_invalida(self, uri):
        with pytest.raises(ValueError):
            jc.dividir_uri_s3(uri)

    def test_leer_texto(self):
        class Cuerpo:
            def read(self):
                return "servicio,ñandú".encode("utf-8")

        class Cliente:
            def get_object(self, Bucket, Key):
                assert (Bucket, Key) == ("b", "k.csv")
                return {"Body": Cuerpo()}

        assert jc.leer_texto_s3(Cliente(), "s3://b/k.csv") == "servicio,ñandú"

    def test_leer_texto_falla_con_mensaje_claro(self):
        class Cliente:
            def get_object(self, Bucket, Key):
                raise FileNotFoundError("NoSuchKey")

        with pytest.raises(RuntimeError, match="s3://b/k.csv"):
            jc.leer_texto_s3(Cliente(), "s3://b/k.csv")


# ------------------------------------------------------- muestra dañada


class TestMuestraDanada:
    def test_cada_caso_da_el_resultado_esperado(self, servicios, perfiles):
        validas = [fila(id_solicitud=f"CHV-{i:07d}") for i in range(1, 4)]
        muestra = construir_muestra_danada(validas)
        assert len(muestra) == len(validas) + len(CASOS_DANADOS)
        casos = muestra[len(validas) :]
        for (id_caso, descripcion, esperado), registro in zip(CASOS_DANADOS, casos):
            r = procesar(registro, servicios, perfiles)
            obtenido = "VALIDA" if r["tipo"] == "ok" else r["cubre"]
            assert obtenido == esperado, f"{id_caso}: {descripcion} -> {r}"

    def test_conteo_de_cuarentena_esperado(self):
        esperados = [e for _, _, e in CASOS_DANADOS]
        assert esperados.count("ERROR_PARSEO") == 10
        assert esperados.count("ERROR_PERFIL") == 2
        assert esperados.count("VALIDA") == 2

    def test_requiere_al_menos_una_fila_base(self):
        with pytest.raises(ValueError):
            construir_muestra_danada([])
