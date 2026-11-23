"""Ensayo determinista F1–F9 sobre copias aisladas de diseños registrados."""
import argparse
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from marco.auditoria import auditar, compilar, compilador
from marco.modelo import guardar, leer


def mutar(fallo, r, vistas):
    """Devuelve el diagnóstico esperado y la entidad o posición sembrada."""
    driver = r["drivers"][0]
    decision = r["decisiones"][0]["id"]
    elemento = r["elementos"][0]
    if fallo == "F1":
        ausente = "DEC-0"
        while any(d["id"] == ausente for d in r["decisiones"]):
            ausente += "0"
        elemento["implementa"].append(ausente)
        return "R5", elemento["id"]
    if fallo == "F2":
        elemento["implementa"].append(driver["id"])
        return "R6", elemento["id"]
    if fallo == "F3":
        nuevo = "DRV-0"
        while any(d["id"] == nuevo for d in r["drivers"]):
            nuevo += "0"
        r["drivers"].append(dict(driver, id=nuevo, priorizado=True))
        return "R1", nuevo
    if fallo == "F4":
        for campo in ("motivada_por", "drivers_directos", "escenarios"):
            r["decisiones"][0][campo] = []
        return "R2", decision
    if fallo == "F5":
        for e in r["elementos"]:
            e["implementa"] = [d for d in e["implementa"] if d != decision]
        return "R3", decision
    if fallo == "F6":
        elemento["implementa"] = []
        return "R4", elemento["id"]
    if fallo in ("F7", "F8"):
        lineas = vistas["componentes"].splitlines()
        i = next(i for i, linea in enumerate(lineas) if linea.startswith('component "'))
        alias = lineas[i].rsplit(" as ", 1)[1]
        if fallo == "F7":
            lineas[i] = f'component "Nombre alterado {alias}" as {alias}'
            esperado = ("R7", alias)
        else:
            lineas[i] = lineas[i].replace('"', '', 1)
            esperado = ("R8", f"línea {i+1} ")
        vistas["componentes"] = "\n".join(lineas) + "\n"
        return esperado
    if fallo == "F9":
        # Se conservan tipos, grados de realización y referencias existentes.
        otro = next((e for e in r["elementos"] if set(e["implementa"]) != set(elemento["implementa"])), None)
        if otro is None:
            raise ValueError("F9 requiere dos elementos con justificaciones distintas.")
        elemento["implementa"], otro["implementa"] = otro["implementa"], elemento["implementa"]
        return None, f"{elemento['id']} y {otro['id']}"
    raise ValueError(f"Fallo desconocido: {fallo}")


def ejecutar(lote, comando):
    @lru_cache(maxsize=64)
    def compilar_una_vez(texto, cmd):
        return compilar(texto, cmd)

    casos = []
    for ruta in sorted(lote.glob("*/ejecucion.json")):
        if leer(ruta)["estado"] != "valido":
            continue
        carpeta = ruta.parent
        registro = leer(carpeta/"registro.json")
        originales = {v:(carpeta/f"{v}.puml").read_text(encoding="utf-8-sig")
                      for v in ("componentes", "secuencia")}
        def revisar(r, vistas):
            return auditar(r, vistas, tuple(comando), compilar_vista=compilar_una_vez)[0]
        limpio = revisar(registro, originales)
        if limpio:
            casos.append({"caso":carpeta.name, "hallazgos_control":limpio, "ensayos":[]})
            continue
        ensayos = []
        for i in range(1, 10):
            fallo = f"F{i}"
            r, vistas = deepcopy(registro), originales.copy()
            regla, lugar = mutar(fallo, r, vistas)
            hallazgos = revisar(r, vistas)
            esperados = [h for h in hallazgos if regla and h.startswith(regla+" ")]
            ensayos.append({"fallo":fallo, "regla_esperada":regla, "localizacion":lugar,
                            "detectado":bool(esperados) if regla else None,
                            "localizado":any(lugar in h for h in esperados) if regla else None,
                            "hallazgos":hallazgos})
        casos.append({"caso":carpeta.name, "hallazgos_control":limpio, "ensayos":ensayos})
    if not casos:
        raise ValueError("El lote debe contener al menos un caso válido.")
    pruebas = [e for c in casos for e in c["ensayos"]]
    por_tipo = {}
    for i in range(1, 9):
        grupo = [e for e in pruebas if e["fallo"] == f"F{i}"]
        por_tipo[f"F{i}"] = {"sembrados":len(grupo), "detectados":sum(e["detectado"] for e in grupo),
                            "localizados":sum(e["localizado"] for e in grupo)}
    total = {k:sum(g[k] for g in por_tipo.values()) for k in ("sembrados","detectados","localizados")}
    f9 = [e for e in pruebas if e["fallo"] == "F9"]
    return {"total_F1_F8":total, "por_tipo":por_tipo,
            "controles_limpios":len(casos), "controles_con_alerta":sum(bool(c["hallazgos_control"]) for c in casos),
            "F9_sin_alerta":[sum(not e["hallazgos"] for e in f9),len(f9)], "casos":casos}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("lote", type=Path)
    p.add_argument("salida", type=Path)
    p.add_argument("--jar")
    a = p.parse_args()
    if a.salida.exists():
        p.error("Usa un archivo nuevo para conservar las mediciones previas.")
    resultado = ejecutar(a.lote, compilador(a.jar))
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    guardar(a.salida, resultado)
    print(resultado["total_F1_F8"])
