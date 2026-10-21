import math
import re
from datetime import datetime

from fuentes import ErrorDatos
from modelo import KG_POR_QUINTAL, Oferta, Pedido

PATRON_PEDIDO = re.compile(r"PED-\d{3}")
PATRON_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")

COLUMNAS = {
    "materiales": ("id", "nombre", "controlado", "reutilizable"),
    "recetas": ("producto", "material", "kg_por_quintal"),
    "proveedores": ("proveedor", "ciudad", "material", "presentacion", "kg_por_presentacion", "precio_cop"),
    "pedidos": ("id", "fecha", "cliente", "producto", "quintales"),
    "inventario": ("material", "kg_disponible"),
    "permisos": ("material", "cupo_anual_kg"),
}


# --- Validación del esquema y conversión de valores ---

def validar_esquema(registros, tabla):
    if not registros:
        raise ErrorDatos(f"La tabla {tabla} está vacía")
    faltan = set(COLUMNAS[tabla]) - set(registros[0])
    if faltan:
        raise ErrorDatos(f"A la tabla {tabla} le faltan columnas: {', '.join(sorted(faltan))}")


def convertir_numero(valor):
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return None
    numero = float(valor)
    if not math.isfinite(numero):
        raise ValueError(f"{valor} no es un número finito")
    return numero


def numero_obligatorio(valor, descripcion):
    try:
        numero = convertir_numero(valor)
    except (ValueError, TypeError):
        raise ErrorDatos(f"{descripcion} no es un número: {valor}")
    if numero is None:
        raise ErrorDatos(f"Falta el valor de {descripcion}")
    return numero


def a_booleano(valor, descripcion):
    texto = str(valor).strip().lower()
    if texto not in ("si", "no"):
        raise ErrorDatos(f"{descripcion} debe ser 'si' o 'no', no '{valor}'")
    return texto == "si"


def fecha_valida(valor):
    """La regex comprueba la forma AAAA-MM-DD; strptime, que la fecha exista en el calendario."""
    if not isinstance(valor, str) or PATRON_FECHA.fullmatch(valor) is None:
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d")
    except ValueError:
        return False
    return True


# --- Tablas de referencia: si tienen errores el programa se detiene ---

def preparar_materiales(registros):
    validar_esquema(registros, "materiales")
    materiales = {}
    for registro in registros:
        codigo = registro["id"]
        if codigo in materiales:
            raise ErrorDatos(f"El material {codigo} está repetido")
        materiales[codigo] = {
            "nombre": registro["nombre"],
            "controlado": a_booleano(registro["controlado"], f"'controlado' de {codigo}"),
            "reutilizable": a_booleano(registro["reutilizable"], f"'reutilizable' de {codigo}"),
        }
    return materiales


def preparar_recetas(registros, materiales):
    validar_esquema(registros, "recetas")
    recetas = {}
    for registro in registros:
        producto = registro["producto"]
        material = registro["material"]
        if material not in materiales:
            raise ErrorDatos(f"La receta de {producto} usa un material desconocido: {material}")
        kg = numero_obligatorio(registro["kg_por_quintal"], f"kg de {material} en {producto}")
        if kg <= 0:
            raise ErrorDatos(f"La receta de {producto} tiene una cantidad inválida de {material}")
        if producto not in recetas:
            recetas[producto] = {}
        if material in recetas[producto]:
            raise ErrorDatos(f"La receta de {producto} repite el material {material}")
        recetas[producto][material] = kg

    for producto, receta in recetas.items():
        if not math.isclose(sum(receta.values()), KG_POR_QUINTAL):
            raise ErrorDatos(f"La receta de {producto} no suma {KG_POR_QUINTAL} kg por quintal")
    return recetas


def preparar_ofertas(registros, materiales):
    validar_esquema(registros, "proveedores")
    ofertas = []
    for registro in registros:
        proveedor = registro["proveedor"]
        material = registro["material"]
        if material not in materiales:
            raise ErrorDatos(f"{proveedor} ofrece un material desconocido: {material}")
        kg = numero_obligatorio(registro["kg_por_presentacion"], f"kg por presentación de {proveedor}")
        precio = numero_obligatorio(registro["precio_cop"], f"precio de {proveedor}")
        if kg <= 0 or precio <= 0:
            raise ErrorDatos(f"{proveedor} tiene una presentación o un precio inválido para {material}")
        ofertas.append(Oferta(proveedor, registro["ciudad"], material,
                              registro["presentacion"], kg, int(precio)))

    materiales_ofrecidos = {oferta.material for oferta in ofertas}
    for material in materiales:
        if material not in materiales_ofrecidos:
            raise ErrorDatos(f"Ningún proveedor ofrece {material}")
    return ofertas


def preparar_cantidades(registros, tabla, columna, materiales):
    """Sirve para inventario.csv y permisos.csv: un valor en kg por material."""
    validar_esquema(registros, tabla)
    cantidades = {}
    for registro in registros:
        material = registro["material"]
        if material not in materiales:
            raise ErrorDatos(f"La tabla {tabla} tiene un material desconocido: {material}")
        if material in cantidades:
            raise ErrorDatos(f"La tabla {tabla} repite el material {material}")
        kg = numero_obligatorio(registro[columna], f"{columna} de {material}")
        if kg < 0:
            raise ErrorDatos(f"La tabla {tabla} tiene un valor negativo para {material}")
        cantidades[material] = kg
    return cantidades


# --- Pedidos: las filas con errores se apartan con su motivo ---

def validar_pedido(registro, recetas):
    motivos = []

    codigo = registro.get("id")
    if not isinstance(codigo, str) or PATRON_PEDIDO.fullmatch(codigo) is None:
        motivos.append("id con formato inválido")

    if not fecha_valida(registro.get("fecha")):
        motivos.append("fecha inválida")

    cliente = registro.get("cliente")
    if not isinstance(cliente, str) or cliente.strip() == "":
        motivos.append("cliente faltante")

    if registro.get("producto") not in recetas:
        motivos.append("producto sin receta")

    try:
        quintales = convertir_numero(registro.get("quintales"))
    except (ValueError, TypeError):
        motivos.append("quintales no numérico")
    else:
        if quintales is None:
            motivos.append("quintales faltante")
        elif quintales <= 0:
            motivos.append("quintales fuera de rango")

    return motivos


def limpiar_pedidos(registros, recetas):
    validar_esquema(registros, "pedidos")
    pedidos = []
    rechazos = []
    ids_aceptados = set()

    for fila, registro in enumerate(registros, start=1):
        motivos = validar_pedido(registro, recetas)
        if registro.get("id") in ids_aceptados:
            motivos.append("id duplicado")

        if motivos:
            rechazos.append({"fila": fila, "id": registro.get("id"), "motivo": "; ".join(motivos)})
            continue

        ids_aceptados.add(registro["id"])
        pedidos.append(Pedido(registro["id"], registro["fecha"], registro["cliente"].strip(),
                              registro["producto"], convertir_numero(registro["quintales"])))

    if not pedidos:
        raise ErrorDatos("No quedan pedidos válidos para planificar")
    return pedidos, rechazos
