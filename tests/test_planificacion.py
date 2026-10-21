import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from fuentes import ErrorDatos, FuenteDatos, FuenteCSV, FuenteJSON, crear_fuente
from modelo import Pedido, Oferta
from pipeline import (fecha_valida, validar_pedido, limpiar_pedidos, preparar_materiales,
                      preparar_recetas, preparar_ofertas, preparar_cantidades,
                      calcular_necesidades, calcular_faltantes, elegir_compra)

DATOS = RAIZ / "data"

MATERIALES = {
    "NIT": {"nombre": "Nitrato de potasio", "controlado": True, "reutilizable": True},
    "AZU": {"nombre": "Azufre", "controlado": False, "reutilizable": True},
}
RECETAS = {"Pólvora negra grano fino": {"NIT": 37.5, "CAR": 7.5, "AZU": 5.0},
           "Pólvora para mecha": {"NIT": 37.0, "CAR": 7.5, "AZU": 5.0, "DEX": 0.5}}
PEDIDO_OK = {"id": "PED-001", "fecha": "2026-10-02", "cliente": "Cliente A",
             "producto": "Pólvora negra grano fino", "quintales": "4"}
AZUFRE_25 = Oferta("P1", "Cali", "AZU", "bulto", 25, 95000)
AZUFRE_50 = Oferta("P2", "Cúcuta", "AZU", "bulto", 50, 180000)


class PruebasFuentes(unittest.TestCase):
    def test_csv_y_json_leen_los_mismos_registros(self):
        registros_csv = FuenteCSV().cargar(DATOS / "pedidos.csv")
        registros_json = FuenteJSON().cargar(DATOS / "pedidos.json")
        self.assertEqual(len(registros_csv), 56)
        self.assertEqual(len(registros_json), 56)
        self.assertEqual([r["id"] for r in registros_csv], [r["id"] for r in registros_json])

    def test_archivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            FuenteCSV().cargar(DATOS / "no_existe.csv")

    def test_json_que_no_es_lista(self):
        ruta = Path(tempfile.mkdtemp()) / "pedido.json"
        ruta.write_text(json.dumps(PEDIDO_OK), encoding="utf-8")
        with self.assertRaises(ErrorDatos):
            FuenteJSON().cargar(ruta)

    def test_json_mal_escrito(self):
        ruta = Path(tempfile.mkdtemp()) / "roto.json"
        ruta.write_text('[{"id": "PED-001",', encoding="utf-8")
        with self.assertRaises(ErrorDatos):
            FuenteJSON().cargar(ruta)

    def test_fuente_datos_es_abstracta(self):
        with self.assertRaises(TypeError):
            FuenteDatos()

    def test_crear_fuente_segun_extension(self):
        self.assertIsInstance(crear_fuente("pedidos.csv"), FuenteCSV)
        self.assertIsInstance(crear_fuente("pedidos.JSON"), FuenteJSON)
        with self.assertRaises(ErrorDatos):
            crear_fuente("pedidos.xlsx")


class PruebasPedidos(unittest.TestCase):
    def test_fecha_con_regex_y_calendario(self):
        self.assertTrue(fecha_valida("2026-10-02"))
        self.assertFalse(fecha_valida("02/10/2026"))
        self.assertFalse(fecha_valida("2026-11-31"))  # forma correcta, pero no existe
        self.assertFalse(fecha_valida(None))

    def test_pedido_correcto_no_tiene_motivos(self):
        self.assertEqual(validar_pedido(PEDIDO_OK, RECETAS), [])

    def test_ids_con_formato_invalido(self):
        for codigo in ["PED17", "ped-001", "PED-0001", "XPED-001", 1]:
            self.assertIn("id con formato inválido", validar_pedido({**PEDIDO_OK, "id": codigo}, RECETAS))

    def test_quintales_invalidos(self):
        self.assertIn("quintales faltante", validar_pedido({**PEDIDO_OK, "quintales": ""}, RECETAS))
        self.assertIn("quintales faltante", validar_pedido({**PEDIDO_OK, "quintales": None}, RECETAS))
        self.assertIn("quintales no numérico", validar_pedido({**PEDIDO_OK, "quintales": "abc"}, RECETAS))
        self.assertIn("quintales fuera de rango", validar_pedido({**PEDIDO_OK, "quintales": "-2"}, RECETAS))

    def test_limpiar_datos_de_ejemplo(self):
        recetas = preparar_recetas(FuenteCSV().cargar(DATOS / "recetas.csv"),
                                   preparar_materiales(FuenteCSV().cargar(DATOS / "materiales.csv")))
        pedidos, rechazos = limpiar_pedidos(FuenteCSV().cargar(DATOS / "pedidos.csv"), recetas)
        self.assertEqual(len(pedidos), 50)
        self.assertEqual([r["fila"] for r in rechazos], [13, 19, 26, 34, 42, 48])
        self.assertTrue(all(isinstance(p, Pedido) and isinstance(p.quintales, float) for p in pedidos))

    def test_duplicado_conserva_la_primera_aparicion(self):
        segundo = {**PEDIDO_OK, "cliente": "Cliente B", "quintales": "9"}
        pedidos, rechazos = limpiar_pedidos([PEDIDO_OK, segundo], RECETAS)
        self.assertEqual(len(pedidos), 1)
        self.assertEqual(pedidos[0].cliente, "Cliente A")
        self.assertEqual(rechazos, [{"fila": 2, "id": "PED-001", "motivo": "id duplicado"}])

    def test_sin_pedidos_validos(self):
        with self.assertRaises(ErrorDatos):
            limpiar_pedidos([{**PEDIDO_OK, "quintales": "0"}], RECETAS)

    def test_tabla_vacia_o_sin_columnas(self):
        with self.assertRaises(ErrorDatos):
            limpiar_pedidos([], RECETAS)
        sin_fecha = {clave: valor for clave, valor in PEDIDO_OK.items() if clave != "fecha"}
        with self.assertRaisesRegex(ErrorDatos, "fecha"):
            limpiar_pedidos([sin_fecha], RECETAS)


class PruebasReferencias(unittest.TestCase):
    def test_receta_que_no_suma_50_kg(self):
        filas = [{"producto": "Mala", "material": "NIT", "kg_por_quintal": "40"},
                 {"producto": "Mala", "material": "AZU", "kg_por_quintal": "5"}]
        with self.assertRaisesRegex(ErrorDatos, "no suma"):
            preparar_recetas(filas, MATERIALES)

    def test_material_repetido_o_booleano_invalido(self):
        fila = {"id": "NIT", "nombre": "Nitrato", "controlado": "si", "reutilizable": "si"}
        with self.assertRaisesRegex(ErrorDatos, "repetido"):
            preparar_materiales([fila, fila])
        with self.assertRaises(ErrorDatos):
            preparar_materiales([{**fila, "reutilizable": "quizás"}])

    def test_inventario_negativo(self):
        with self.assertRaisesRegex(ErrorDatos, "negativo"):
            preparar_cantidades([{"material": "NIT", "kg_disponible": "-1"}],
                                "inventario", "kg_disponible", MATERIALES)

    def test_material_sin_proveedor(self):
        filas = [{"proveedor": "P1", "ciudad": "Cali", "material": "NIT", "presentacion": "bolsa",
                  "kg_por_presentacion": "25", "precio_cop": "310000"}]
        with self.assertRaisesRegex(ErrorDatos, "AZU"):
            preparar_ofertas(filas, MATERIALES)


class PruebasCompras(unittest.TestCase):
    def test_necesidades_de_pedidos_conocidos(self):
        pedidos = [Pedido("PED-001", "2026-10-02", "A", "Pólvora negra grano fino", 2),
                   Pedido("PED-002", "2026-10-03", "B", "Pólvora para mecha", 1)]
        necesidades = calcular_necesidades(pedidos, RECETAS)
        self.assertAlmostEqual(necesidades["NIT"], 112)  # 2 * 37.5 + 37
        self.assertAlmostEqual(necesidades["DEX"], 0.5)
        self.assertAlmostEqual(sum(necesidades.values()), 3 * 50)  # 3 quintales = 150 kg
        self.assertEqual(calcular_necesidades([], RECETAS), {})

    def test_faltantes_descuentan_inventario(self):
        faltantes = calcular_faltantes({"NIT": 100, "AZU": 10}, {"NIT": 30, "AZU": 50})
        self.assertEqual(faltantes, {"NIT": 70, "AZU": 0})

    def test_combinar_presentaciones(self):
        compra = elegir_compra([AZUFRE_25, AZUFRE_50], 75)
        self.assertEqual(sum(item["costo"] for item in compra), 275000)  # un bulto de 50 y uno de 25
        self.assertEqual(sum(item["kg"] for item in compra), 75)

    def test_si_no_falta_nada_no_se_compra(self):
        self.assertEqual(elegir_compra([AZUFRE_25, AZUFRE_50], 0), [])

    def test_empate_de_costo_deja_menos_sobrante(self):
        ofertas = [Oferta("P1", "Cali", "X", "bolsa", 12, 100), Oferta("P2", "Cali", "X", "bolsa", 10, 100)]
        compra = elegir_compra(ofertas, 9)
        self.assertEqual(len(compra), 1)
        self.assertEqual(compra[0]["proveedor"], "P2")

    def test_cantidad_exacta_sin_sobrante(self):
        self.assertEqual(AZUFRE_25.cantidad_para(50), 2)
        self.assertEqual(AZUFRE_25.cantidad_para(50.0000001), 2)
        self.assertEqual(AZUFRE_25.cantidad_para(51), 3)


if __name__ == "__main__":
    unittest.main()
