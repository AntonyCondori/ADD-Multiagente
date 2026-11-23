"""Transforma respuestas validadas en incrementos ADD y vistas como código."""
from copy import deepcopy
import re

def nuevo():
    return {k: [] for k in ("drivers", "escenarios", "decisiones", "elementos", "iteraciones")}

def identificados(filas, prefijo, inicio=1):
    return [dict(fila, id=f"{prefijo}-{i:02}") for i, fila in enumerate(filas, inicio)]

def aplicar(rol, respuesta, anterior, ultima):
    r = deepcopy(anterior)
    if rol == "analista":
        filas = respuesta["drivers"]
        if not any(x["priorizado"] for x in filas):
            raise ValueError("Prioriza al menos un driver.")
        r["drivers"] = identificados(filas, "DRV")
    elif rol == "calidad":
        filas = respuesta["escenarios"]
        esperados = {x["id"] for x in r["drivers"] if x["tipo"] == "calidad"}
        if {x["driver"] for x in filas} != esperados:
            raise ValueError(f"Cada driver de calidad requiere escenario: {sorted(esperados)}.")
        r["escenarios"] = identificados(filas, "ESC")
    elif rol == "decisiones":
        datos = respuesta.copy()
        nuevos = datos.pop("nuevos_elementos")
        objetivo = datos.pop("objetivo")
        # Un escenario formaliza un driver. Se conserva el origen de cada enlace.
        datos["drivers_directos"] = list(dict.fromkeys(datos["motivada_por"]))
        datos["escenarios"] = list(dict.fromkeys(datos["escenarios"]))
        via = [e["driver"] for e in r["escenarios"] if e["id"] in datos["escenarios"]]
        datos["motivada_por"] = list(dict.fromkeys([*datos["drivers_directos"], *via]))
        numero = len(r["iteraciones"]) + 1
        decision = f"DEC-{numero:02}"
        existentes = {etiqueta(e["nombre"]).casefold():e for e in r["elementos"]}
        filas, reutilizados = [], []
        for nombre in dict.fromkeys(n.strip() for n in nuevos):
            clave = etiqueta(nombre).casefold()
            if not clave:
                raise ValueError("Cada elemento necesita un nombre legible.")
            if clave in existentes:
                elemento = existentes[clave]
                if decision not in elemento["implementa"]:
                    elemento["implementa"].append(decision)
                    reutilizados.append(elemento["id"])
                continue
            elemento = {"id":f"ELM-{len(r['elementos'])+len(filas)+1:02}",
                        "nombre":nombre, "implementa":[decision], "padre":objetivo}
            filas.append(elemento)
            existentes[clave] = elemento
        if not filas:
            raise ValueError(f"Refinar {objetivo} requiere al menos un elemento interno nuevo.")
        if numero == 1 and len(filas) < 2:
            raise ValueError("La descomposición inicial necesita dos elementos diferentes.")
        r["decisiones"].append(dict(datos, id=decision))
        r["elementos"].extend(filas)
        r["iteraciones"].append({"numero":numero, "objetivo":objetivo, "decision":decision,
                                "creados":[x["id"] for x in filas],"reutilizados":reutilizados})
        if ultima:
            cubiertos = {d for dec in r["decisiones"] for d in dec["motivada_por"]}
            faltan = [x["id"] for x in r["drivers"] if x["priorizado"] and x["id"] not in cubiertos]
            if faltan:
                raise ValueError(f"R1: cubre los drivers pendientes {faltan} en esta iteración.")
    return r

def etiqueta(texto):
    # Sólo texto de una línea entra al lenguaje del diagrama.
    texto = re.sub(r'[^\w .,():áéíóúñü/-]', " ", texto, flags=re.UNICODE)
    return " ".join(texto.split())[:150]

def construir_vistas(r, propuesta):
    vistas = {}
    nombres = {x["id"]: etiqueta(x["nombre"]) for x in r["elementos"]}
    if len(set(nombres.values())) != len(nombres) or not all(nombres.values()):
        raise ValueError("Los nombres deben ser únicos y legibles tras convertirlos a etiquetas.")
    for vista, relaciones in propuesta.items():
        usados = {a[k] for a in relaciones for k in ("origen", "destino")}
        tipo = "component" if vista == "componentes" else "participant"
        lineas = ["@startuml"]
        for clave, nombre in nombres.items():
            if vista == "componentes" or clave in usados:
                lineas.append(f'{tipo} "{nombre}" as {clave.replace("-", "_")}')
        for a in relaciones:
            mensaje = etiqueta(a["mensaje"])
            if not mensaje:
                raise ValueError("Cada relación necesita un mensaje legible.")
            lineas.append(f'{a["origen"].replace("-", "_")} -> {a["destino"].replace("-", "_")} : {mensaje}')
        if vista == "componentes":
            for e in r["elementos"]:
                if e["padre"] != "SISTEMA":
                    lineas.append(f'{e["padre"].replace("-", "_")} -> {e["id"].replace("-", "_")} : se descompone en')
        vistas[vista] = "\n".join([*lineas, "@enduml", ""])
    return vistas

def enlaces(r):
    salida = set()
    for x in r["escenarios"]:
        salida.add((x["driver"], "formaliza_en", x["id"]))
    for x in r["decisiones"]:
        salida.update((d, "motiva", x["id"]) for d in x["motivada_por"])
        salida.update((e, "justifica", x["id"]) for e in x["escenarios"])
    for x in r["elementos"]:
        salida.update((d, "implementada_en", x["id"]) for d in x["implementa"])
    return salida

