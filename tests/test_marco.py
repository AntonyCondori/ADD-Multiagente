import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from marco.auditoria import auditar, compilador
from marco.contratos import contrato, validar
from marco.diseno import aplicar, construir_vistas, enlaces, nuevo
from marco.flujo import ejecutar
from marco.modelo import guardar, huella, leer
from revision import iniciar, puntuar
from evaluar import resumir
from estructura import revisar_iteraciones
from expertos import plantilla, resumir as resumir_expertos
import csv

ANALISTA = {"drivers":[{"tipo":"calidad","priorizado":True,"texto":"Responder en un segundo."}]}
CALIDAD = {"escenarios":[{"driver":"DRV-01","atributo":"latencia","fuente":"Usuario",
    "estimulo":"Consulta","artefacto":"Catálogo","entorno":"Normal","respuesta":"Devuelve ficha","medida":"1 s"}]}
DECISION = {"objetivo":"SISTEMA","motivada_por":["DRV-01"],"escenarios":["ESC-01"],
            "contexto":"Consultas repetidas","tactica":"Caché","alternativa":"Lectura directa",
            "consecuencias":"Posible desfase","nuevos_elementos":["Consultas","Caché"]}
ARISTA = {"origen":"ELM-01","destino":"ELM-02","mensaje":"Buscar ficha"}
ARQUITECTO = {"componentes":[ARISTA],"secuencia":[ARISTA]}

def registro():
    r = nuevo()
    for rol, resp in [("analista",ANALISTA),("calidad",CALIDAD),("decisiones",DECISION)]:
        validar(resp,contrato(rol,r))
        r = aplicar(rol,resp,r,True)
    return r

class Reglas(unittest.TestCase):
    def setUp(self):
        self.r = registro()
        self.v = construir_vistas(self.r,ARQUITECTO)

    def revisar(self):
        with patch("marco.auditoria.compilar",return_value=b"<svg/>"):
            return auditar(self.r,self.v,[])

    def test_reglas_y_tasa_de_huerfanos(self):
        self.r["decisiones"][0]["motivada_por"] = ["DRV-99"]
        self.r["elementos"][0]["implementa"] = []
        errores,m,_ = self.revisar()
        for regla in ("R1","R2","R4","R5"):
            self.assertTrue(any(e.startswith(regla) for e in errores))
        self.assertEqual(m["elementos_huerfanos"],[1,2])

    def test_nombre_y_alias_inexistente(self):
        self.v["secuencia"] = self.v["secuencia"].replace("ELM_02","ELM_99")
        errores,_,_ = self.revisar()
        self.assertTrue(any(e.startswith("R5 secuencia") for e in errores))

    def test_r8_rechazo_compilador(self):
        with patch("marco.auditoria.compilar", side_effect=ValueError("error sintáctico")):
            errores,m,_ = auditar(self.r,self.v,[])
        self.assertEqual(m["validez_sintactica"],[0,2])
        self.assertEqual(sum(e.startswith("R8") for e in errores),2)

    def test_decision_sin_realizacion_y_tipo_incorrecto(self):
        for e in self.r["elementos"]:
            e["implementa"] = ["DRV-01"]
        errores,_,_ = self.revisar()
        self.assertTrue(any(e.startswith("R3 DEC-01:") for e in errores))
        self.assertTrue(any(e.startswith("R6 ELM-01:") for e in errores))

    def test_campo_faltante_no_cuenta(self):
        self.r["escenarios"][0]["medida"] = "Sin especificar"
        self.assertEqual(self.revisar()[1]["completitud_escenarios"],[5,6])

    def test_instruccion_fuera_de_contrato(self):
        self.v["componentes"] = self.v["componentes"].replace("@enduml","!include fichero\n@enduml")
        self.assertEqual(self.revisar()[1]["validez_sintactica"],[1,2])

    def test_refinamiento_conserva_padre(self):
        d = dict(DECISION,objetivo="ELM-01",nuevos_elementos=["Índice"])
        actualizado = aplicar("decisiones",d,self.r,True)
        self.assertEqual(actualizado["elementos"][-1]["padre"],"ELM-01")
        self.assertEqual(len(self.r["elementos"]),2)

    def test_reutilizacion_y_trazabilidad_transitiva(self):
        self.r["drivers"].append(dict(self.r["drivers"][0],id="DRV-02",tipo="funcional"))
        d = dict(DECISION,objetivo="ELM-01",motivada_por=["DRV-02"],nuevos_elementos=["Caché","Índice"])
        actualizado = aplicar("decisiones",d,self.r,True)
        revisar_iteraciones(actualizado)
        self.assertEqual(actualizado["decisiones"][-1]["drivers_directos"],["DRV-02"])
        self.assertEqual(actualizado["decisiones"][-1]["motivada_por"],["DRV-02","DRV-01"])
        self.assertEqual(actualizado["iteraciones"][-1]["reutilizados"],["ELM-02"])
        self.assertEqual(actualizado["elementos"][1]["implementa"],["DEC-01","DEC-02"])

    def test_un_objetivo_no_puede_preceder_a_su_creacion(self):
        self.r["iteraciones"][0]["objetivo"]="ELM-01"
        with self.assertRaisesRegex(ValueError,"Integridad de iteraciones ADD"):
            revisar_iteraciones(self.r)

    def test_id_desconocido_y_tipo_invalido(self):
        with self.assertRaises(ValueError):
            validar(dict(DECISION,motivada_por=["DRV-90"]),contrato("decisiones",self.r))
        with self.assertRaises(ValueError):
            validar({"drivers":[dict(ANALISTA["drivers"][0],priorizado=1)]},contrato("analista",nuevo()))

    def test_sin_drivers_de_calidad(self):
        r = aplicar("analista",{"drivers":[dict(ANALISTA["drivers"][0],tipo="funcional")]},nuevo(),False)
        validar({"escenarios":[]},contrato("calidad",r))
        self.assertEqual(aplicar("calidad",{"escenarios":[]},r,False)["escenarios"],[])

class Flujo(unittest.TestCase):
    def test_reparacion_y_limite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            entrada=base/"caso.txt"
            entrada.write_text("Consulta de fichas.",encoding="utf-8")
            with patch("marco.flujo.compilador",return_value=["java"]), patch("marco.flujo.subprocess.run") as version, patch("marco.auditoria.compilar",return_value=b"<svg/>"):
                version.return_value.stdout=b"PlantUML version prueba"
                secuencia = [ANALISTA,CALIDAD,DECISION,{"componentes":[],"secuencia":[]},ARQUITECTO]
                with patch("marco.modelo.Modelo.llamar",side_effect=[json.dumps(x) for x in secuencia]) as llamada:
                    resultado=ejecutar(entrada,base/"ok","prueba","local",iteraciones=1)
                    self.assertEqual(resultado["correcciones"],1)
                    self.assertEqual(llamada.call_args.args[0],"arquitecto")
                    self.assertIn("correccion",llamada.call_args.args[1])
                with patch("marco.modelo.Modelo.llamar",return_value="{}"):
                    with self.assertRaises(RuntimeError):
                        ejecutar(entrada,base/"fallo","prueba","local",reintentos=1)
                    self.assertEqual(leer(base/"fallo/ejecucion.json")["estado"],"fallido")

    def test_compilador_real(self):
        try:
            cmd=compilador()
        except RuntimeError as exc:
            self.skipTest(str(exc))
        r=registro()
        errores,m,svg=auditar(r,construir_vistas(r,ARQUITECTO),cmd)
        self.assertEqual(errores,[])
        self.assertEqual(m["validez_sintactica"],[2,2])
        self.assertTrue(all(b"<svg" in x for x in svg.values()))

class Evaluacion(unittest.TestCase):
    def test_referencia_independiente_y_faltantes(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Path(tmp)
            (b/"x.txt").write_text("Caso sintético de prueba.",encoding="utf-8")
            iniciar(b,b/"rev")
            d=b/"rev/x"
            r=registro()
            a=leer(d/"revision-A.json")
            ids={fila["id"]:fila["id"] for filas in [r["drivers"],r["escenarios"],r["decisiones"],r["elementos"]] for fila in filas}
            a.update(nodos=ids,enlaces=[list(e) for e in sorted(enlaces(r))])
            for letra in "AB":
                guardar(d/f"revision-{letra}.json",dict(a,revisor=letra))
            guardar(d/"consenso.json",dict(a,revisores=["A","B"],resolucion="Consenso sintético de prueba."))
            mapa=dict(ids)
            mapa["ELM-02"]=None
            guardar(d/"alineacion.json",{"criterio":"Ejemplo de nodo sin equivalencia.","huella_registro":huella(r),"mapa":mapa})
            res=puntuar(d,r,a["sha256_requisitos"])
            self.assertEqual(res["precision"],[4,5])
            self.assertEqual(res["recall"],[4,5])
            self.assertEqual(res["f1"],[8,10])
            self.assertEqual(len(res["faltantes"]),1)
            caso = b/"lote/x"
            caso.mkdir(parents=True)
            guardar(caso/"registro.json",r)
            (caso/"requisitos.txt").write_text("Caso sintético de prueba.",encoding="utf-8")
            guardar(caso/"ejecucion.json",{
                "modo":"inferencia","estado":"valido","modelo":"fixture para prueba",
                "sha256_requisitos":a["sha256_requisitos"],"segundos":1,
                "correcciones":0,"prompt_tokens":100,"completion_tokens":30
            })
            _, estadisticas = resumir(b/"lote",b/"informe",b/"rev")
            self.assertEqual(estadisticas["recall"]["media_por_caso"],0.8)
            self.assertEqual(estadisticas["f1"]["media_por_caso"],0.8)
            self.assertTrue((b/"informe/informe.html").is_file())

    def test_excluye_replay_de_experimentos(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Path(tmp)
            (b/"x").mkdir()
            guardar(b/"x/ejecucion.json",{"modo":"reproduccion"})
            with self.assertRaisesRegex(ValueError,"reproducción"):
                resumir(b,b/"informe")

    def test_revision_experta_con_dos_valoraciones(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp)
            (b/"lote/caso").mkdir(parents=True)
            guardar(b/"lote/caso/ejecucion.json",{"estado":"valido"})
            guardar(b/"lote/caso/registro.json",registro())
            archivo = b/"respuestas.csv"
            plantilla(b/"lote",archivo,["A","B"])
            with archivo.open(encoding="utf-8-sig",newline="") as f:
                filas = list(csv.DictReader(f))
            for i,fila in enumerate(filas):
                for k in ("tactica","escenario","coherencia_vistas","claridad_adr"):
                    fila[k] = 3+i
            with archivo.open("w",encoding="utf-8-sig",newline="") as f:
                w=csv.DictWriter(f,fieldnames=filas[0].keys())
                w.writeheader()
                w.writerows(filas)
            resumir_expertos(b/"lote",archivo,b/"resumen.json")
            self.assertEqual(leer(b/"resumen.json")["caso"]["tactica"]["mediana"],3.5)

if __name__ == "__main__":
    unittest.main()

