"""Reaudita el registro y los archivos PlantUML de una ejecución guardada."""
import argparse
import json
from pathlib import Path
from marco.auditoria import auditar, compilador
from marco.modelo import leer
from estructura import revisar_iteraciones

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("carpeta",type=Path)
    p.add_argument("--jar")
    a = p.parse_args()
    try:
        r = leer(a.carpeta/"registro.json")
        vistas = {}
        for n in ("componentes","secuencia"):
            f = a.carpeta/(n+".puml")
            if f.exists():
                vistas[n] = f.read_text(encoding="utf-8-sig")
        errores, m, _ = auditar(r,vistas,compilador(a.jar))
        try:
            revisar_iteraciones(r)
        except ValueError as exc:
            errores.append(str(exc))
        print(json.dumps({"errores":errores,"metricas":m},ensure_ascii=False,indent=2))
        return int(bool(errores))
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
        print(f"Entrada inválida: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

