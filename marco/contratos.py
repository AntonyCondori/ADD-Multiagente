"""Contratos de los cuatro agentes generativos y validación de sus respuestas."""

def cadena(opciones=None):
    if opciones is not None and opciones:
        return {"type": "string", "enum": list(opciones)}
    return {"type": "string", "minLength": 1, "maxLength": 220}

def lista(item, minimo=0, maximo=8):
    return {"type": "array", "items": item, "minItems": minimo, "maxItems": maximo}

def objeto(**campos):
    return {"type": "object", "properties": campos, "required": list(campos), "additionalProperties": False}

PARTES = ("fuente", "estimulo", "artefacto", "entorno", "respuesta", "medida")
TIPOS = ["funcional", "calidad", "restriccion", "preocupacion", "objetivo"]

def contrato(rol, registro):
    drivers = [x["id"] for x in registro["drivers"]]
    calidad = [x["id"] for x in registro["drivers"] if x["tipo"] == "calidad"]
    escenarios = [x["id"] for x in registro["escenarios"]]
    elementos = [x["id"] for x in registro["elementos"]]
    if rol == "analista":
        driver = objeto(tipo=cadena(TIPOS), texto=cadena(), priorizado={"type":"boolean"})
        return objeto(drivers=lista(driver, 1, 12))
    if rol == "calidad":
        escenario = objeto(driver=cadena(calidad), atributo=cadena(),
                           **{p: cadena() for p in PARTES})
        return objeto(escenarios=lista(escenario, len(calidad), len(calidad)))
    if rol == "decisiones":
        return objeto(objetivo=cadena(elementos or ["SISTEMA"]),
                      motivada_por=lista(cadena(drivers), 1, len(drivers)),
                      escenarios=lista(cadena(escenarios), 0, len(escenarios)),
                      contexto=cadena(), tactica=cadena(), alternativa=cadena(), consecuencias=cadena(),
                      nuevos_elementos=lista(cadena(), 1 if elementos else 2, 3))
    relacion = objeto(origen=cadena(elementos), destino=cadena(elementos), mensaje=cadena())
    return objeto(componentes=lista(relacion, 1, 10), secuencia=lista(relacion, 1, 12))

def validar(valor, contrato, ruta="respuesta"):
    tipo = contrato["type"]
    esperado = {"object": dict, "array": list, "string": str, "boolean": bool}[tipo]
    if type(valor) is not esperado:
        raise ValueError(f"{ruta}: tipo esperado {tipo}")
    if tipo == "object":
        if set(valor) != set(contrato["required"]):
            raise ValueError(f"{ruta}: se esperan los campos {contrato['required']}")
        for k, v in valor.items():
            validar(v, contrato["properties"][k], f"{ruta}.{k}")
    elif tipo == "array":
        if not contrato["minItems"] <= len(valor) <= contrato["maxItems"]:
            raise ValueError(f"{ruta}: número de entradas fuera de rango.")
        for i, v in enumerate(valor):
            validar(v, contrato["items"], f"{ruta}[{i}]")
    elif tipo == "string":
        if not valor.strip() or len(valor) > contrato.get("maxLength", float("inf")) or ("enum" in contrato and valor not in contrato["enum"]):
            raise ValueError(f"{ruta}: texto vacío o referencia desconocida {valor!r}")

