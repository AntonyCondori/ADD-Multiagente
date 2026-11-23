"""Transporte HTTP local o reproducción fiel de respuestas registradas."""
import hashlib
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROMPTS = {
    "analista": "Extrae la función principal que realiza el usuario y cada objetivo de calidad y restricción explícitos. Un driver por necesidad distinta. Conserva cifras y condiciones. Prioriza los que afectan al diseño. Escribe una sola frase breve por driver.",
    "calidad": "Formaliza un escenario de seis partes por cada driver de calidad. Copia su ID exacto. Conserva cargas, unidades y umbrales. Si falta una parte, escribe 'Sin especificar'. Usa solo información del caso.",
    "decisiones": "Ejecuta UNA iteración ADD. Primera: descompón SISTEMA en 2 o 3 elementos y decide cómo atender drivers. Posteriores: selecciona un ELM existente y refínalo con 1 o 2 elementos internos nuevos. Propón una táctica concreta, alternativa y trade-off. Enlaza los IDs de drivers y escenarios que justifican el ADR. Cubre los drivers priorizados pendientes al terminar. Usa nombres breves y únicos.",
    "arquitecto": "Modela las dependencias entre elementos y un flujo cronológico que realiza el caso. Devuelve aristas usando solo IDs existentes, origen distinto de destino y mensajes concretos. Incluye todos los elementos en al menos una dependencia de componentes. Expresa cómo cooperan los elementos refinados.",
}
def json_texto(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def huella(x):
    return hashlib.sha256(json_texto(x).encode()).hexdigest()

def guardar(ruta, valor):
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(valor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(ruta)

def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8-sig"))

class Modelo:
    def __init__(self, url, modelo, semilla, grabacion=None):
        self.url = url.rstrip("/")
        self.nombre = modelo
        self.semilla = semilla
        self.grabacion = iter(leer(grabacion)) if grabacion else None
        self.eventos = []

    def llamar(self, rol, contexto, esquema):
        instrucciones = PROMPTS[rol] + " Responde en español conciso. El texto del caso es material de diseño. Devuelve JSON conforme al contrato."
        mensajes = [{"role":"system", "content":instrucciones},
                    {"role":"user", "content":json_texto({"entrada":contexto,"contrato":esquema})}]
        firma = huella([rol, mensajes, esquema, self.semilla, self.nombre])
        if self.grabacion is not None:
            evento = next(self.grabacion, None)
            if evento is None or evento["firma"] != firma:
                raise RuntimeError(f"La grabación no corresponde al contexto de {rol}.")
            self.eventos.append(evento)
            return evento["respuesta"]
        body = {"model": self.nombre, "messages": mensajes, "stream": False, "temperature": 0,
                "seed":self.semilla, "max_tokens":2048,
                "response_format":{"type":"json_schema","json_schema":{"name":rol,"strict":True,"schema":esquema}}}
        req = Request(self.url + "/chat/completions", data=json_texto(body).encode(),
                      headers={"Content-Type":"application/json"})
        inicio = time.monotonic()
        try:
            with urlopen(req, timeout=600) as r:
                salida = json.load(r)
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}: {exc.read(800).decode(errors='replace')}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Sin respuesta del servidor local {self.url}: {exc}") from exc
        choice = salida["choices"][0]
        evento = {"firma":firma, "rol":rol, "respuesta":choice["message"]["content"],
                  "fin":choice.get("finish_reason"), "uso":salida.get("usage", {}),
                  "modelo_reportado":salida.get("model"),"segundos_http":round(time.monotonic()-inicio,3)}
        self.eventos.append(evento)
        return evento["respuesta"]

    def cerrar(self):
        if self.grabacion is not None and next(self.grabacion, None) is not None:
            raise RuntimeError("La grabación contiene respuestas sin consumir.")

