"""Verificación del formato de intercambio del registro exportado."""
import re
from pathlib import Path
from marco.modelo import leer

ESQUEMA = Path(__file__).resolve().parent/"esquemas"/"registro.schema.json"

def validar_formato(valor, esquema, ruta="registro"):
    """Aplica los tipos y restricciones usados en el esquema 2020-12 del proyecto."""
    tipos = {"object":dict,"array":list,"boolean":bool,"integer":int,"string":str}
    tipo = esquema.get("type")
    if tipo and type(valor) is not tipos[tipo]:
        raise ValueError(f"{ruta}: se esperaba {tipo}.")
    if "enum" in esquema and valor not in esquema["enum"]:
        raise ValueError(f"{ruta}: valor fuera del vocabulario.")
    if tipo == "object":
        if set(valor) != set(esquema["required"]):
            raise ValueError(f"{ruta}: campos esperados {', '.join(esquema['required'])}.")
        for k, v in valor.items():
            validar_formato(v, esquema["properties"][k], f"{ruta}.{k}")
    elif tipo == "array":
        for i, v in enumerate(valor):
            validar_formato(v, esquema["items"], f"{ruta}[{i}]")
    elif tipo == "string":
        if len(valor.strip()) < esquema.get("minLength",0):
            raise ValueError(f"{ruta}: texto vacío.")
        if "pattern" in esquema and not re.fullmatch(esquema["pattern"],valor):
            raise ValueError(f"{ruta}: identificador inválido {valor}.")
    elif tipo == "integer" and valor < esquema.get("minimum",valor):
        raise ValueError(f"{ruta}: número fuera de rango.")

def revisar_iteraciones(r):
    validar_formato(r,leer(ESQUEMA))
    if not r["drivers"] or not r["iteraciones"] or not any(x["priorizado"] for x in r["drivers"]):
        raise ValueError("El registro final requiere drivers priorizados e iteraciones.")
    conocidos = set()
    decisiones = {x["id"] for x in r["decisiones"]}
    elementos = {x["id"]:x for x in r["elementos"]}
    usados = set()
    escenarios = {e["id"]:e["driver"] for e in r["escenarios"]}
    for adr in r["decisiones"]:
        fuentes = set(adr["drivers_directos"])
        for escenario in adr["escenarios"]:
            if escenario not in escenarios:
                raise ValueError(f"R5 {adr['id']}: escenario desconocido.")
            fuentes.add(escenarios[escenario])
        if set(adr["motivada_por"]) != fuentes:
            raise ValueError(f"Coherencia {adr['id']}: motivos incompatibles con sus fuentes.")
    for n,it in enumerate(r["iteraciones"],1):
        objetivo = it["objetivo"]
        if it["numero"] != n or (objetivo != "SISTEMA" if n==1 else objetivo not in conocidos):
            raise ValueError(f"Integridad de iteraciones ADD, iteración {n}: número u objetivo de refinamiento inválido.")
        if it["decision"] not in decisiones or it["decision"] in usados or not it["creados"]:
            raise ValueError(f"Integridad de iteraciones ADD, iteración {n}: ADR inválido o sin elementos nuevos.")
        usados.add(it["decision"])
        if set(it["reutilizados"]) - conocidos:
            raise ValueError(f"Integridad de iteraciones ADD, iteración {n}: se reutiliza un elemento que aún no existía.")
        for k in it["creados"]:
            if k in conocidos or k not in elementos or elementos[k]["padre"] != objetivo:
                raise ValueError(f"Integridad de iteraciones ADD, iteración {n}: creación inconsistente de {k}.")
            conocidos.add(k)
    if conocidos!=set(elementos) or usados!=decisiones:
        raise ValueError("Integridad de iteraciones ADD: el registro tiene elementos o decisiones sin iteración ADD.")

