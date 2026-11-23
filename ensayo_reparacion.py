"""Prueba controlada del agente Arquitecto ante un identificador inexistente."""
import argparse
import json
from pathlib import Path
from marco.auditoria import auditar, compilador
from marco.contratos import contrato, validar
from marco.diseno import construir_vistas
from marco.modelo import guardar, leer, Modelo

def probar(caso, salida, url, jar=None):
    cfg = leer(caso/"ejecucion.json")
    if cfg["modo"]!="inferencia" or cfg["estado"]!="valido":
        raise ValueError("Selecciona una ejecución de inferencia válida.")
    r = leer(caso/"registro.json")
    original = next(x for x in reversed(leer(caso/"respuestas.json")) if x["rol"]=="arquitecto")
    propuesta = json.loads(original["respuesta"])
    esquema = contrato("arquitecto",r)
    validar(propuesta,esquema)
    comando = compilador(jar)
    salida.mkdir(parents=True,exist_ok=False)
    antes = propuesta["secuencia"][0]["origen"]
    falso = "ELM-999999"
    if any(e["id"]==falso for e in r["elementos"]):
        raise ValueError("El identificador de control está ocupado.")
    propuesta["secuencia"][0]["origen"] = falso
    texto = (caso/"requisitos.txt").read_text(encoding="utf-8").strip()
    contexto = {"requisitos":texto,"registro":r,"iteracion_final":False}
    modelo = Modelo(url,cfg["modelo"],cfg["semilla"])
    resultado = {"tipo":"inyeccion_controlada","caso":caso.name,"modelo":cfg["modelo"],
                 "semilla":cfg["semilla"],"original":antes,"inyectado":falso,"intentos":[]}
    raw = json.dumps(propuesta,ensure_ascii=False)
    for i in range(cfg["max_correcciones_por_artefacto"]+1):
        try:
            propuesta = json.loads(raw)
            validar(propuesta,esquema)
            vistas = construir_vistas(r,propuesta)
            errores,met,svg = auditar(r,vistas,comando)
            if errores:
                raise ValueError(" | ".join(errores))
            resultado.update(estado="reparado",metricas=met,correcciones=i)
            for nombre,contenido in vistas.items():
                (salida/(nombre+".puml")).write_text(contenido,encoding="utf-8")
                (salida/(nombre+".svg")).write_bytes(svg[nombre])
            resultado["intentos"].append({"intento":i,"aceptado":True})
            guardar(salida/"ensayo.json",resultado)
            return True
        except (ValueError,TypeError) as exc:
            resultado["intentos"].append({"intento":i,"aceptado":False,"error":str(exc),"respuesta":raw})
            resultado.update(estado="rechazado",correcciones=i)
            guardar(salida/"ensayo.json",resultado)
            contexto["correccion"]={"respuesta_previa":raw,"error_del_verificador":str(exc)}
        if i < cfg["max_correcciones_por_artefacto"]:
            raw = modelo.llamar("arquitecto",contexto,esquema)
            guardar(salida/"respuestas.json",modelo.eventos)
    return False

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("caso",type=Path)
    p.add_argument("salida",type=Path)
    p.add_argument("--url",default="http://127.0.0.1:8080/v1")
    p.add_argument("--jar")
    a=p.parse_args()
    try:
        ok=probar(a.caso,a.salida,a.url,a.jar)
        print("Ensayo reparado." if ok else "Límite de correcciones alcanzado.")
        raise SystemExit(0 if ok else 1)
    except (ValueError,OSError,RuntimeError,KeyError) as exc:
        p.exit(1,str(exc)+"\n")

