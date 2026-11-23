"""Verificador independiente de referencias, cobertura y compilación real."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from .contratos import PARTES
from .diseno import etiqueta

def compilador(jar=None):
    jar = jar or os.getenv("PLANTUML_JAR")
    if not jar and shutil.which("plantuml"):
        return ["plantuml"]
    if not jar:
        jar = next(iter(sorted((Path.home()/".vscode/extensions").glob("jebbs.plantuml-*/plantuml.jar"), reverse=True)), None)
    if jar and Path(jar).is_file() and shutil.which("java"):
        return ["java", "-Djava.awt.headless=true", "-jar", str(Path(jar).resolve())]
    raise RuntimeError("Se necesita PlantUML. Indica --jar o configura PLANTUML_JAR y Java.")

def compilar(texto, comando):
    p = subprocess.run([*comando, "-charset","UTF-8","-failfast2","-tsvg","-pipe"],
                       input=texto.encode(), capture_output=True, timeout=60,
                       env={**os.environ, "PLANTUML_SECURITY_PROFILE":"SANDBOX"})
    if p.returncode:
        raise ValueError(p.stderr.decode(errors="replace")[:500] or "PlantUML rechazó la vista.")
    if ET.fromstring(p.stdout).tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("PlantUML no devolvió un SVG.")
    return p.stdout

def auditar(r, vistas, comando, *, compilar_vista=None):
    compilar_vista = compilar_vista or compilar
    errores, svg = [], {}
    indices = {}
    for grupo, prefijo in [("drivers","DRV"),("escenarios","ESC"),("decisiones","DEC"),("elementos","ELM")]:
        filas = r[grupo]
        indices[grupo] = {x["id"]:x for x in filas}
        if len(indices[grupo]) != len(filas) or any(not re.fullmatch(prefijo+r"-\d+", k) for k in indices[grupo]):
            errores.append(f"R5 {grupo}: identificadores repetidos o inválidos.")
    drivers, esc, dec, elm = (indices[k] for k in ("drivers","escenarios","decisiones","elementos"))
    def comprobar_enlaces(origen, campo, referencias, destino, prefijo):
        for valor in referencias:
            if not isinstance(valor, str) or not re.fullmatch(prefijo + r"-\d+", valor):
                errores.append(f"R6 {origen}: {campo} requiere {prefijo}, recibió {valor!r}.")
            elif valor not in destino:
                errores.append(f"R5 {origen}: {campo} referencia {valor}, que no existe.")
    cubiertos = set()
    for x in dec.values():
        ids = set(x["motivada_por"])
        if not ids.intersection(drivers):
            errores.append(f"R2 {x['id']}: carece de driver válido.")
        cubiertos.update(ids)
        comprobar_enlaces(x["id"], "motivada_por", ids, drivers, "DRV")
        comprobar_enlaces(x["id"], "drivers_directos", x.get("drivers_directos", []), drivers, "DRV")
        comprobar_enlaces(x["id"], "escenarios", x["escenarios"], esc, "ESC")
        for e in set(x["escenarios"]).intersection(esc):
            if esc[e]["driver"] not in ids:
                errores.append(f"Coherencia {x['id']}: {e} corresponde a otro driver.")
    for x in esc.values():
        comprobar_enlaces(x["id"], "driver", [x["driver"]], drivers, "DRV")
    realizadas = set()
    for x in elm.values():
        comprobar_enlaces(x["id"], "implementa", x["implementa"], dec, "DEC")
        realizadas.update(x["implementa"])
        if x.get("padre","SISTEMA") != "SISTEMA":
            comprobar_enlaces(x["id"], "padre", [x["padre"]], elm, "ELM")
    for clave in sorted(dec.keys() - realizadas):
        errores.append(f"R3 {clave}: decisión estructural sin elemento que la implemente.")
    priorizados = {k for k,x in drivers.items() if x["priorizado"]}
    for k in sorted(priorizados - cubiertos):
        errores.append(f"R1 {k}: sin decisión.")
    visibles = set()
    for vista, tipo in [("componentes","component"),("secuencia","participant")]:
        texto = vistas.get(vista, "")
        declarados, usados = set(), set()
        formato = True
        lineas = [s.strip() for s in texto.splitlines() if s.strip()]
        if (lineas[:1] != ["@startuml"] or lineas[-1:] != ["@enduml"]
                or lineas.count("@startuml") != 1 or lineas.count("@enduml") != 1):
            formato = False
        for numero, linea in enumerate(texto.splitlines(), 1):
            linea = linea.strip()
            if not linea or linea in ("@startuml", "@enduml"):
                continue
            decl = re.fullmatch(tipo+r' "([^"]+)" as (ELM_\d+)', linea)
            flecha = re.fullmatch(r"(ELM_\d+) -> (ELM_\d+) : (.+)", linea)
            if decl:
                nombre, alias = decl.groups()
                k = alias.replace("_","-")
                if k not in elm:
                    errores.append(f"R5 {vista}: alias {alias} sin elemento en el registro.")
                elif k in declarados or etiqueta(elm[k]["nombre"]) != nombre:
                    errores.append(f"R7 {vista}: {alias} repetido o asociado a un nombre divergente.")
                declarados.add(k)
            elif flecha:
                usados.update(k.replace("_","-") for k in flecha.groups()[:2])
            else:
                formato = False
                errores.append(f"R8 {vista}: línea {numero} fuera de la sintaxis admitida.")
        if usados - declarados:
            errores.append(f"R5 {vista}: alias sin declaración {sorted(usados-declarados)}.")
        if not formato or not declarados or not usados:
            errores.append(f"Vista {vista}: falta contenido o se usó sintaxis fuera del contrato.")
        visibles.update(declarados | usados)
        if vista == "componentes" and set(elm) - declarados:
            errores.append("Vista componentes: faltan elementos del registro.")
        # Sólo se entrega al compilador el subconjunto que reconoce el auditor.
        if formato:
            try:
                svg[vista] = compilar_vista(texto, comando)
            except (ValueError, ET.ParseError, OSError, subprocess.TimeoutExpired) as ex:
                errores.append(f"R8 {vista}: {ex}")
        else:
            errores.append(f"R8 {vista}: compilación omitida por formato de entrada.")
    huerfanos = sorted(k for k in visibles if k not in elm or not set(elm[k]["implementa"]).intersection(dec))
    errores.extend(f"R4 {k}: elemento visible sin decisión." for k in huerfanos)
    ausente = {"sin especificar", "desconocido", "pendiente", "no especificado"}
    presentes = sum(isinstance(x.get(p), str) and bool(x[p].strip()) and x[p].strip().casefold().rstrip(".") not in ausente
                    for x in esc.values() for p in PARTES)
    metricas = {"cobertura_drivers":[len(priorizados & cubiertos),len(priorizados)],
                "elementos_huerfanos":[len(huerfanos),len(visibles)],
                "completitud_escenarios":[presentes,6*len(esc)], "validez_sintactica":[len(svg),2]}
    return errores, metricas, svg

