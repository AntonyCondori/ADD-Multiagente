"""Mide TRN y ES en los archivos PlantUML y las instantáneas de dos iteraciones."""
import argparse
import re
from pathlib import Path
from marco.diseno import etiqueta
from marco.modelo import leer, guardar

def medir(d):
    a,b = [leer(d/f"iteracion-{i:02}.json") for i in (1,2)]
    elementos = {e["id"]:etiqueta(e["nombre"]) for e in b["elementos"]}
    resueltas = menciones = 0
    for n in ("componentes","secuencia"):
        lineas = (d/f"{n}.puml").read_text(encoding="utf-8").splitlines()
        nombres = {}
        for linea in lineas:
            decl = re.fullmatch(r'(?:component|participant) "([^"]+)" as (ELM_\d+)',linea)
            if decl:
                nombre,alias = decl.groups()
                nombres[alias] = nombre
        for linea in lineas:
            decl = re.fullmatch(r'(?:component|participant) "[^"]+" as (ELM_\d+)',linea)
            relacion = re.fullmatch(r"(ELM_\d+) -> (ELM_\d+) : .+",linea)
            ids = decl.groups() if decl else relacion.groups() if relacion else ()
            menciones += len(ids)
            resueltas += sum(k in nombres and nombres[k]==elementos.get(k.replace("_","-")) for k in ids)
    total = estables = 0
    it = b["iteraciones"][1]
    for grupo in ("drivers","escenarios","decisiones","elementos"):
        despues = {x["id"]:dict(x) for x in b[grupo]}
        for fila in a[grupo]:
            total += 1
            nueva = despues.get(fila["id"])
            if nueva and grupo=="elementos" and fila["id"] in it["reutilizados"]:
                nueva["implementa"] = [v for v in nueva["implementa"] if v!=it["decision"]]
            estables += nueva==fila
    return {"TRN":[resueltas,menciones],"ES":[estables,total]}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("lote",type=Path)
    p.add_argument("salida",type=Path)
    a=p.parse_args()
    if a.salida.exists():
        p.error("Indica un archivo de salida nuevo.")
    casos={d.name:medir(d) for d in sorted(a.lote.iterdir()) if d.is_dir() and leer(d/"ejecucion.json")["estado"]=="valido"}
    total={k:[sum(v[k][i] for v in casos.values()) for i in (0,1)] for k in ("TRN","ES")}
    guardar(a.salida,{"casos":casos,"total":total})
    print(total)

