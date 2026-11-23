"""Inicia la inferencia local con el motor portátil y el modelo del experimento."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

BASE = Path(__file__).resolve().parent
ARCHIVO = "llama-b12647-bin-win-cpu-x64.zip"
HASH_MOTOR = "e5814566b6fdeebc5d1cff90d8881299602f78e2aa083923105d0bbff7889c7c"
HASH_MODELO = "a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50"
NOMBRE = "qwen3.5-4b-q4_K_M"

def sha(ruta):
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda:f.read(1024*1024), b""):
            h.update(bloque)
    return h.hexdigest()

def localizar_modelo():
    modelos = Path(os.getenv("OLLAMA_MODELS", str(Path.home()/".ollama"/"models")))
    return modelos/"blobs"/("sha256-"+HASH_MODELO)

def comando(motor, modelo, alias, puerto):
    return [str(motor),"--offline","-m",str(modelo),"--alias",alias,
            "--host","127.0.0.1","--port",str(puerto),"--reasoning","off",
            "--parallel","2","-t","4","-c","10240","--no-webui"]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gguf",type=Path,default=localizar_modelo())
    p.add_argument("--alias",default=NOMBRE)
    p.add_argument("--motor",type=Path,help="Ejecutable llama-server para otra plataforma.")
    p.add_argument("--puerto",type=int,default=8080)
    p.add_argument("--comprobar",action="store_true",help="Comprueba los archivos y la versión del motor.")
    a=p.parse_args()
    if not a.gguf.is_file():
        p.error("Falta el modelo. Consulta Instalación en README.md o indica --gguf.")
    if a.alias == NOMBRE and sha(a.gguf) != HASH_MODELO:
        p.error("El archivo difiere del modelo del experimento. Usa su alias propio con --alias.")
    with tempfile.TemporaryDirectory(prefix="marco-add-") as tmp:
        motor = a.motor or shutil.which("llama-server")
        if not a.motor and sys.platform == "win32":
            paquete = BASE/"terceros"/ARCHIVO
            if sha(paquete) != HASH_MOTOR:
                p.error("El archivo del motor portátil no coincide con el hash publicado.")
            with zipfile.ZipFile(paquete) as z:
                z.extractall(tmp)
            motor = Path(tmp)/"llama-server.exe"
        if not motor:
            p.error("Indica la ruta del ejecutable llama-server con --motor.")
        if a.comprobar:
            return subprocess.call([str(motor),"--version"])
        print(f"Servidor local en http://127.0.0.1:{a.puerto}/v1. Ctrl+C para cerrar.",flush=True)
        try:
            return subprocess.call(comando(motor,a.gguf,a.alias,a.puerto))
        except KeyboardInterrupt:
            return 0

if __name__ == "__main__":
    raise SystemExit(main())

