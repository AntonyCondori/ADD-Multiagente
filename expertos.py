"""Prepara y resume la revisión experta opcional con escala Likert 1–5."""
import argparse
import csv
from pathlib import Path
from statistics import median
from marco.modelo import guardar, leer, huella

CRITERIOS = ("tactica", "escenario", "coherencia_vistas", "claridad_adr")
CAMPOS = ("experto", "caso", "huella_registro", *CRITERIOS, "comentario")

def casos_validos(lote):
    casos = {}
    for p in sorted(lote.glob("*/ejecucion.json")):
        if leer(p)["estado"] == "valido":
            casos[p.parent.name] = huella(leer(p.parent/"registro.json"))
    if not casos:
        raise ValueError("El lote necesita al menos un caso válido.")
    return casos

def plantilla(lote, salida, expertos):
    if len(set(expertos)) != len(expertos) or len(expertos) not in (2,3):
        raise ValueError("Usa dos o tres códigos de experto distintos.")
    casos = casos_validos(lote)
    with salida.open("x",encoding="utf-8-sig",newline="") as f:
        w = csv.DictWriter(f,fieldnames=CAMPOS)
        w.writeheader()
        for experto in expertos:
            for caso, firma in casos.items():
                w.writerow({"experto":experto,"caso":caso,"huella_registro":firma})

def resumir(lote, respuestas, salida):
    casos = casos_validos(lote)
    valores = {caso:{k:[] for k in CRITERIOS} for caso in casos}
    pares = set()
    expertos = set()
    with respuestas.open(encoding="utf-8-sig",newline="") as f:
        for fila in csv.DictReader(f):
            persona, caso = fila["experto"].strip(), fila["caso"]
            par = (persona,caso)
            if not persona or par in pares or caso not in casos or casos[caso] != fila["huella_registro"]:
                raise ValueError("Fila duplicada, incompleta o asociada a otra ejecución.")
            pares.add(par)
            expertos.add(persona)
            for k in CRITERIOS:
                n = int(fila[k])
                if not 1<=n<=5:
                    raise ValueError(f"{par}: {k} debe estar entre 1 y 5.")
                valores[caso][k].append(n)
    if len(expertos) not in (2,3) or len(pares)!=len(expertos)*len(casos):
        raise ValueError("Todos los expertos deben valorar cada caso.")
    if salida.exists():
        raise FileExistsError(salida)
    guardar(salida,{c:{k:{"puntuaciones":ns,"mediana":median(ns)} for k,ns in v.items()} for c,v in valores.items()})

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="accion",required=True)
    a = sub.add_parser("preparar")
    a.add_argument("lote",type=Path)
    a.add_argument("salida",type=Path)
    a.add_argument("expertos",nargs="+")
    b = sub.add_parser("resumir")
    b.add_argument("lote",type=Path)
    b.add_argument("respuestas",type=Path)
    b.add_argument("salida",type=Path)
    args = p.parse_args()
    try:
        if args.accion=="preparar":
            plantilla(args.lote,args.salida,args.expertos)
        else:
            resumir(args.lote,args.respuestas,args.salida)
    except (OSError,ValueError,KeyError) as exc:
        p.exit(1,str(exc)+"\n")

