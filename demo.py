"""Demostración local de trazabilidad sobre una ejecución real guardada."""
import argparse
from copy import deepcopy
from pathlib import Path

from marco.auditoria import auditar, compilador
from marco.modelo import leer
from estructura import revisar_iteraciones

BASE = Path(__file__).resolve().parent

def demostrar(caso, jar=None):
    if leer(caso/"ejecucion.json")["estado"] != "valido":
        raise ValueError("Escoge un caso que completó la verificación final.")
    original = leer(caso/"registro.json")
    revisar_iteraciones(original)
    vistas = {v:(caso/(v+".puml")).read_text(encoding="utf-8") for v in ("componentes","secuencia")}
    comando = compilador(jar)
    errores, antes, _ = auditar(original,vistas,comando)
    if errores:
        raise ValueError("El caso original tiene errores: "+" | ".join(errores))
    copia = deepcopy(original)
    elemento = copia["elementos"][-1]
    decision = next(d for d in copia["decisiones"] if d["id"] == elemento["implementa"][0])
    driver = next(d for d in copia["drivers"] if d["id"] == decision["motivada_por"][0])
    print(f"Caso: {caso.name}\n")
    print(f"Driver {driver['id']}: {driver['texto']}")
    print(f"Decisión {decision['id']}: {decision['tactica']}")
    print(f"Elemento {elemento['id']}: {elemento['nombre']}\n")
    print("Ejecución original: R1–R5 superadas.")
    print(f"Prueba controlada: quitar en memoria el enlace de {elemento['id']} con sus decisiones.")
    elemento["implementa"] = []
    errores, despues, _ = auditar(copia,vistas,comando)
    for e in errores:
        print(e)
    for titulo,clave in [("Vistas compiladas","validez_sintactica"),("Elementos huérfanos","elementos_huerfanos")]:
        a,b = antes[clave],despues[clave]
        print(f"{titulo}: antes {a[0]}/{a[1]}, después {b[0]}/{b[1]}.")
    return any(e.startswith("R3 ") for e in errores)

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("caso",nargs="?",type=Path,default=BASE/"evidencia/02-reservas")
    p.add_argument("--jar")
    a=p.parse_args()
    try:
        raise SystemExit(0 if demostrar(a.caso,a.jar) else 1)
    except (ValueError,KeyError,OSError,RuntimeError) as e:
        p.exit(1,str(e)+"\n")

