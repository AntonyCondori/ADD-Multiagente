"""Lista los nodos que los revisores deben alinear con su referencia congelada."""
import argparse
from pathlib import Path
from marco.modelo import huella, guardar, leer
from revision import referencia

def preparar(caso, carpeta):
    consenso = leer(carpeta/"consenso.json")
    referencia(consenso)
    info = leer(caso/"ejecucion.json")
    if info["sha256_requisitos"] != consenso["sha256_requisitos"]:
        raise ValueError("La referencia pertenece a otro caso.")
    plantilla = carpeta/"alineacion.json"
    if plantilla.exists() and leer(plantilla)["mapa"]:
        raise ValueError("Ya hay una alineación iniciada en esta carpeta.")
    r = leer(caso/"registro.json")
    mapa = {fila["id"]:None for grupo in ("drivers","escenarios","decisiones","elementos") for fila in r[grupo]}
    guardar(plantilla,{"huella_registro":huella(r),"mapa":mapa,"criterio":""})

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("caso",type=Path)
    p.add_argument("revision",type=Path)
    a = p.parse_args()
    try:
        preparar(a.caso,a.revision)
    except (OSError,ValueError,KeyError) as exc:
        p.exit(1,str(exc)+"\n")

