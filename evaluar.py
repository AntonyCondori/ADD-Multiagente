"""Resume un lote real, manteniendo explícitos los fallos y denominadores."""
import argparse
import csv
from html import escape
from pathlib import Path
import os
import statistics
from urllib.parse import quote
from marco.modelo import leer, guardar, huella
from revision import puntuar

METRICAS = ("validez_sintactica","cobertura_drivers","elementos_huerfanos","completitud_escenarios","precision","recall")
ETIQUETAS = ("Vistas compiladas","Drivers cubiertos","Elementos huérfanos","Partes de escenario presentes","Precisión","Recall")

def resumir(raiz, salida, revisiones=None):
    rutas = sorted(raiz.glob("*/ejecucion.json"))
    if not rutas:
        raise ValueError("No hay ejecuciones en la carpeta del lote.")
    filas, detalle = [], {}
    for ruta in rutas:
        info = leer(ruta)
        if info["modo"] != "inferencia":
            raise ValueError(f"{ruta.parent.name}: una reproducción no es una observación experimental.")
        fila = {"caso":ruta.parent.name,"estado":info["estado"],"error":info.get("error"),"modelo":info["modelo"],
                "segundos":info.get("segundos"),"correcciones":info.get("correcciones"),
                "tokens_entrada":info.get("prompt_tokens"),"tokens_salida":info.get("completion_tokens")}
        # Conservar métricas disponibles incluso cuando el último intento falló.
        fila.update({k:info.get("metricas",{}).get(k) for k in METRICAS})
        fila["rq2"] = "pendiente de referencia independiente"
        registro = ruta.parent/"registro.json"
        if registro.exists():
            fila["huella_registro"] = huella(leer(registro))
        if revisiones and info["estado"] == "valido":
            evaluacion = puntuar(revisiones/ruta.parent.name,leer(registro),info["sha256_requisitos"])
            detalle[fila["caso"]] = evaluacion
            fila.update({k:evaluacion[k] for k in ("precision","recall")})
            fila["rq2"] = "con referencia por consenso"
        filas.append(fila)
    resumen = {}
    for k in METRICAS:
        pares = [x[k] for x in filas if x[k] and x[k][1] > 0]
        resumen[k] = {"casos_con_denominador":len(pares),"numerador":sum(v[0] for v in pares),
                      "denominador":sum(v[1] for v in pares),
                      "media_por_caso":statistics.mean(n/d for n,d in pares) if pares else None}
    for k in ("segundos","correcciones","tokens_entrada","tokens_salida"):
        valores = [x[k] for x in filas if x[k] is not None]
        resumen[k] = {"casos":len(valores),"total":sum(valores),
                      "media":statistics.mean(valores) if valores else None}
    salida.mkdir(parents=True,exist_ok=False)
    guardar(salida/"resultados.json",{"casos":filas,"agregado":resumen,"evaluacion_semantica":detalle})
    with (salida/"por-caso.csv").open("w",encoding="utf-8-sig",newline="") as f:
        campos = ["caso","estado","error","modelo","segundos","correcciones","tokens_entrada","tokens_salida","rq2","huella_registro"]
        columnas = campos + [f"{k}_{s}" for k in METRICAS for s in ("numerador","denominador")]
        w = csv.DictWriter(f,fieldnames=columnas)
        w.writeheader()
        for fila in filas:
            row = {k:fila.get(k) for k in campos}
            for k in METRICAS:
                row[k+"_numerador"],row[k+"_denominador"] = fila[k] or (None,None)
            w.writerow(row)
    def link(p,t):
        url = quote(os.path.relpath(p,salida).replace(os.sep,"/"),safe="/.-_")
        return f'<a href="{url}">{escape(t)}</a>'
    def fraccion(par):
        return f"{par[0]}/{par[1]}" if par and par[1] else "Pendiente o sin denominador"
    validos = sum(x["estado"]=="valido" for x in filas)
    html = ["""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evaluación del marco ADD</title><style>body{font:16px/1.55 system-ui;color:#182c36;max-width:1100px;margin:3em auto;padding:0 1.5em}h1,h2{color:#164b46}table{border-collapse:collapse;display:block;overflow-x:auto}th,td{text-align:left;border-bottom:1px solid #cddad7;padding:.55em .85em}thead{background:#e9f3f0}a{color:#075b85}small{color:#456}article{border-top:2px solid #cddad7;margin:2em 0}code{font-size:.9em}</style>
<h1>Evaluación del marco multiagente ADD</h1>""",
            f"<p>{validos} de {len(filas)} casos alcanzaron la verificación final. Cada caso corresponde a una ejecución de inferencia.</p>",
            "<h2>Resultados estructurales y semánticos</h2><table><thead><tr><th>Métrica</th><th>Numerador / denominador</th><th>Media por caso</th><th>Casos medidos</th></tr></thead><tbody>"]
    for k,t in zip(METRICAS,ETIQUETAS):
        v=resumen[k]
        media="Pendiente" if v["media_por_caso"] is None else format(v["media_por_caso"],".1%")
        html.append(f"<tr><th>{t}</th><td>{fraccion((v['numerador'],v['denominador']))}</td><td>{media}</td><td>{v['casos_con_denominador']}</td></tr>")
    html.extend(["</tbody></table><p>La completitud cuenta campos documentados. La precisión y el recall requieren correspondencias revisadas por dos personas. El cumplimiento de atributos de calidad requiere evaluar el sistema diseñado.</p>",
                 "<h2>Costo de generación y corrección</h2><table><thead><tr><th>Medida</th><th>Total</th><th>Media por caso medido</th><th>Casos medidos</th></tr></thead><tbody>"])
    for k,titulo in [("correcciones","Correcciones"),("segundos","Segundos por ejecución"),
                     ("tokens_entrada","Tokens de entrada"),("tokens_salida","Tokens de salida")]:
        v = resumen[k]
        media = "Pendiente" if v["media"] is None else format(v["media"], ".2f")
        html.append(f"<tr><th>{titulo}</th><td>{v['total']:.2f}</td><td>{media}</td><td>{v['casos']}</td></tr>")
    html.append("</tbody></table><h2>Casos y artefactos</h2>")
    for fila,ruta in zip(filas,rutas):
        d=ruta.parent
        html.append(f"<article><h3>{escape(fila['caso'])}</h3><p>{escape((d/'requisitos.txt').read_text(encoding='utf-8'))}</p>")
        html.append(f"<p>Estado: {escape(fila['estado'])} · Correcciones: {fila['correcciones']} · Tiempo: {fila['segundos']} s · Tokens de entrada/salida: {fila['tokens_entrada']} / {fila['tokens_salida']}.</p>")
        if fila["error"]:
            html.append(f"<p>Error registrado: {escape(fila['error'])}</p>")
        html.append("<p>"+" · ".join(f"{label}: {fraccion(fila[k])}" for k,label in zip(METRICAS,ETIQUETAS) if fila[k])+"</p>")
        archivos=[("componentes.svg","Componentes"),("secuencia.svg","Secuencia"),("registro.json","Registro y ADR"),
                  ("trazabilidad.csv","Matriz de enlaces"),("historial.json","Correcciones"),("ejecucion.json","Configuración y métricas")]
        html.append("<p>"+" · ".join(link(d/f,t) for f,t in archivos if (d/f).exists())+"</p>")
        if (d/"registro.json").exists():
            r = leer(d/"registro.json")
            html.append("<details><summary>Examinar las decisiones y su trazabilidad</summary>")
            for it in r["iteraciones"]:
                adr = next(x for x in r["decisiones"] if x["id"]==it["decision"])
                html.append(f"<h4>Iteración {it['numero']} · {escape(adr['id'])} · {escape(adr['tactica'])}</h4>")
                for etiqueta,valor in [("Elemento refinado",it["objetivo"]),("Contexto",adr["contexto"]),
                                      ("Alternativa",adr["alternativa"]),("Consecuencias",adr["consecuencias"])]:
                    html.append(f"<p><strong>{etiqueta}</strong> · {escape(valor)}</p>")
                html.append("<ul>")
                for driver in r["drivers"]:
                    if driver["id"] in adr["motivada_por"]:
                        html.append(f"<li>{escape(driver['id'])} · {escape(driver['texto'])}</li>")
                html.append("</ul><p>Elementos creados · " + ", ".join(
                    escape(x["id"]+" "+x["nombre"]) for x in r["elementos"] if x["id"] in it["creados"])+"</p>")
            html.append("</details>")
        html.append("</article>")
    html.append("</html>")
    (salida/"informe.html").write_text("\n".join(html),encoding="utf-8")
    return filas,resumen

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("lote",type=Path)
    p.add_argument("salida",type=Path)
    p.add_argument("--revisiones",type=Path)
    a = p.parse_args()
    try:
        filas, _ = resumir(a.lote,a.salida,a.revisiones)
        print(f"{len(filas)} ejecuciones incluidas. Informe en {a.salida}")
    except (ValueError, KeyError, OSError, TypeError) as ex:
        p.exit(1,str(ex)+"\n")

