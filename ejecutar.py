"""Ejecuta el marco ADD sobre un archivo de requisitos o una colección."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from marco.flujo import ejecutar
from marco.modelo import leer

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("entrada", type=Path, help="Archivo TXT o carpeta con archivos TXT.")
    p.add_argument("salida", type=Path, help="Carpeta nueva para esta ejecución.")
    p.add_argument("--url", default="http://127.0.0.1:8080/v1")
    p.add_argument("--modelo",default="qwen3.5-4b-q4_K_M")
    p.add_argument("--semilla",type=int,default=7)
    p.add_argument("--iteraciones",type=int,default=2)
    p.add_argument("--correcciones",type=int,default=3)
    p.add_argument("--procesos",type=int,choices=(1,2,3,4),default=1,
                   help="Casos concurrentes del lote. Ajustar a los slots del servidor.")
    p.add_argument("--jar")
    p.add_argument("--reproducir",type=Path,help="Carpeta de una ejecución original del mismo caso.")
    a = p.parse_args()
    lote = a.entrada.is_dir()
    if lote and a.reproducir:
        p.error("La reproducción se realiza por caso.")
    if lote and a.salida.exists():
        p.error("Usa un directorio de salida nuevo para el lote.")
    archivos = sorted(a.entrada.glob("*.txt")) if lote else [a.entrada]
    if not archivos:
        p.error("No se encontraron casos TXT.")
    if a.reproducir:
        cfg = leer(a.reproducir/"ejecucion.json")
        a.modelo, a.semilla = cfg["modelo"], cfg["semilla"]
        a.iteraciones, a.correcciones = cfg["iteraciones_ADD"], cfg["max_correcciones_por_artefacto"]
    def procesar(archivo):
        destino = a.salida / archivo.stem if lote else a.salida
        try:
            res = ejecutar(archivo,destino,a.modelo,a.url,a.semilla,a.iteraciones,a.correcciones,a.jar,
                           a.reproducir/"respuestas.json" if a.reproducir else None)
            print(archivo.stem, res["estado"], res["metricas"], flush=True)
            return 0
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"{archivo.stem}: {exc}", flush=True)
            return 1
    with ThreadPoolExecutor(max_workers=a.procesos) as pool:
        fallidos = sum(pool.map(procesar,archivos))
    return int(fallidos > 0)

if __name__ == "__main__":
    raise SystemExit(main())

