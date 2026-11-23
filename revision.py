"""Crea dos formularios independientes y registra el consenso por caso."""
from pathlib import Path
import argparse
import hashlib
import re
from marco.modelo import guardar, leer, huella
from marco.diseno import enlaces

TIPOS_ENLACE = {"formaliza_en":("DRV","ESC"), "motiva":("DRV","DEC"),
                "justifica":("ESC","DEC"), "implementada_en":("DEC","ELM")}

def referencia(doc):
    nodos = doc["nodos"]
    if not isinstance(nodos, dict) or not nodos or not doc["enlaces"]:
        raise ValueError("Completa la referencia con nodos y enlaces.")
    for k, v in nodos.items():
        if not re.fullmatch(r"(DRV|ESC|DEC|ELM)-[A-Za-z0-9_-]+", k) or not isinstance(v,str) or not v.strip():
            raise ValueError(f"Nodo de referencia inválido: {k}.")
    resultado = set()
    for a, tipo, b in doc["enlaces"]:
        par = TIPOS_ENLACE.get(tipo)
        if not par or a not in nodos or b not in nodos or (a.split("-")[0],b.split("-")[0]) != par:
            raise ValueError(f"Enlace de referencia inválido: {a} {tipo} {b}")
        if (a,tipo,b) in resultado:
            raise ValueError(f"Enlace duplicado: {a} {tipo} {b}")
        resultado.add((a,tipo,b))
    return resultado

def iniciar(casos, salida):
    archivos = sorted(Path(casos).glob("*.txt"))
    if not archivos:
        raise ValueError("La carpeta debe contener requisitos en archivos TXT.")
    Path(salida).mkdir(parents=True, exist_ok=False)
    for p in archivos:
        d = Path(salida)/p.stem
        d.mkdir()
        texto = p.read_text(encoding="utf-8-sig").strip()
        (d/"requisitos.txt").write_text(texto+"\n",encoding="utf-8")
        firma = hashlib.sha256(texto.encode()).hexdigest()
        for nom in ("revision-A","revision-B"):
            guardar(d/(nom+".json"), {"sha256_requisitos":firma,"revisor":"","nodos":{},"enlaces":[]})
        guardar(d/"consenso.json", {"sha256_requisitos":firma,"revisores":[], "resolucion":"",
                                     "nodos":{}, "enlaces":[]})
        guardar(d/"alineacion.json", {"huella_registro":"","mapa":{},"criterio":""})

def puntuar(carpeta, r, firma):
    revisiones = [leer(carpeta/f"revision-{letra}.json") for letra in ("A","B")]
    c = leer(carpeta/"consenso.json")
    alineacion = leer(carpeta/"alineacion.json")
    nombres = {d["revisor"].strip().casefold() for d in revisiones}
    if len(nombres)!=2 or "" in nombres or nombres != {n.strip().casefold() for n in c["revisores"]}:
        raise ValueError("Identifica a los dos revisores en los formularios y en el consenso.")
    for d in [*revisiones,c]:
        if d["sha256_requisitos"] != firma:
            raise ValueError("El caso revisado tiene otra huella.")
        referencia(d)
    if not c["resolucion"].strip() or not alineacion["criterio"].strip():
        raise ValueError("Documenta cómo resolvieron desacuerdos y equivalencias.")
    if alineacion["huella_registro"] != huella(r):
        raise ValueError("La alineación corresponde a otro registro.")
    reales = {v["id"] for grupo in ("drivers","escenarios","decisiones","elementos") for v in r[grupo]}
    mapa = alineacion["mapa"]
    valores = [v for v in mapa.values() if v is not None]
    if set(mapa) != reales or len(valores)!=len(set(valores)):
        raise ValueError("Cada nodo generado necesita una correspondencia única o null.")
    for k,v in mapa.items():
        if v is not None and (v not in c["nodos"] or k.split("-")[0] != v.split("-")[0]):
            raise ValueError(f"Correspondencia inválida: {k}, {v}.")
    generados, esperados = enlaces(r), referencia(c)
    encontrados = {(mapa[a],t,mapa[b]) for a,t,b in generados if mapa[a] and mapa[b]} & esperados
    return {"precision":[len(encontrados),len(generados)], "recall":[len(encontrados),len(esperados)],
            "f1":[2*len(encontrados),len(generados)+len(esperados)],
            "falsos_positivos":[list(e) for e in sorted(e for e in generados
                                if (mapa[e[0]],e[1],mapa[e[2]]) not in esperados)],
            "faltantes":[list(e) for e in sorted(esperados-encontrados)]}

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("casos",type=Path)
    p.add_argument("salida",type=Path)
    a = p.parse_args()
    iniciar(a.casos,a.salida)

