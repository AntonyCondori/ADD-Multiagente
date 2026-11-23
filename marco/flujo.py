"""Orquestación, checkpoints y evidencia de cada ejecución."""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

from .auditoria import auditar, compilador
from .contratos import contrato, validar
from .diseno import aplicar, construir_vistas, enlaces, nuevo
from .modelo import Modelo, guardar, huella

def ejecutar(entrada, destino, modelo, url, semilla=7, iteraciones=2, reintentos=3, jar=None, grabacion=None):
    texto = Path(entrada).read_text(encoding="utf-8-sig").strip()
    if not texto or iteraciones < 1 or reintentos < 0:
        raise ValueError("Se requieren requisitos, al menos una iteración y un límite de correcciones no negativo.")
    comando = compilador(jar)
    version = subprocess.run([*comando, "-version"], capture_output=True, timeout=30).stdout.decode(errors="replace").splitlines()[0]
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=False)
    (destino/"requisitos.txt").write_text(texto+"\n", encoding="utf-8")
    inicio = time.monotonic()
    agente = Modelo(url, modelo, semilla, grabacion)
    r = nuevo()
    hist = []
    info = {"estado":"en curso", "modo":"reproduccion" if grabacion else "inferencia",
            "inicio_utc":datetime.now(timezone.utc).isoformat(), "python":platform.python_version(),
            "modelo":modelo,"semilla":semilla,"temperatura":0,"plantuml":version,
            "iteraciones_ADD":iteraciones,"max_correcciones_por_artefacto":reintentos,
            "sha256_requisitos":hashlib.sha256(texto.encode()).hexdigest(),
            "huella_software":huella({p.name:p.read_text(encoding="utf-8") for p in sorted(Path(__file__).parent.glob("*.py"))})}
    guardar(destino/"ejecucion.json",info)
    roles = ["analista","calidad", *(["decisiones"]*iteraciones),"arquitecto"]
    try:
        for etapa, rol in enumerate(roles, 1):
            esquema = contrato(rol,r)
            ultima = rol == "decisiones" and len(r["iteraciones"]) == iteraciones-1
            contexto = {"requisitos":texto,"registro":r,"iteracion_final":ultima}
            if rol == "decisiones":
                cubiertos = {d for x in r["decisiones"] for d in x["motivada_por"]}
                contexto["drivers_priorizados_pendientes"] = [d["id"] for d in r["drivers"] if d["priorizado"] and d["id"] not in cubiertos]
            for intento in range(reintentos+1):
                raw = agente.llamar(rol,contexto,esquema)
                guardar(destino/"respuestas.json",agente.eventos)
                evento = {"etapa":etapa,"rol":rol,"intento":intento+1}
                try:
                    respuesta = json.loads(raw)
                    validar(respuesta, esquema)
                    if rol == "arquitecto":
                        vistas = construir_vistas(r,respuesta)
                        errores, metricas, svg = auditar(r,vistas,comando)
                        info["metricas"] = metricas
                        if errores:
                            raise ValueError(" | ".join(errores))
                        for nombre, contenido in vistas.items():
                            (destino/(nombre+".puml")).write_text(contenido,encoding="utf-8")
                            (destino/(nombre+".svg")).write_bytes(svg[nombre])
                    else:
                        r = aplicar(rol,respuesta,r,ultima)
                    evento["estado"] = "aceptado"
                except (ValueError, TypeError) as exc:
                    evento.update(estado="rechazado", error=str(exc))
                    contexto["correccion"] = {"respuesta_previa":raw, "error_del_verificador":str(exc)}
                hist.append(evento)
                guardar(destino/"historial.json",hist)
                if evento["estado"] == "aceptado":
                    guardar(destino/"registro.json",r)
                    if rol == "decisiones":
                        guardar(destino/f"iteracion-{len(r['iteraciones']):02}.json", r)
                    break
                if intento == reintentos:
                    raise RuntimeError(f"{rol}: agotó las correcciones. {evento['error']}")
        agente.cerrar()
        with (destino/"trazabilidad.csv").open("w",encoding="utf-8-sig",newline="") as f:
            w = csv.writer(f)
            w.writerow(("origen","relacion","destino"))
            w.writerows(sorted(enlaces(r)))
        info["estado"] = "valido"
    except Exception as exc:
        info.update(estado="fallido",error=str(exc))
        raise
    finally:
        info["segundos"] = round(time.monotonic()-inicio,3)
        info["llamadas_registradas"] = len(agente.eventos)
        info["correcciones"] = sum(e["intento"]>1 for e in hist)
        for nombre in ("prompt_tokens","completion_tokens"):
            usos = [e["uso"].get(nombre) for e in agente.eventos]
            info[nombre] = sum(usos) if not grabacion and usos and all(isinstance(n,int) for n in usos) else None
        guardar(destino/"ejecucion.json",info)
    return info

