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


# --- Cálculo de compras, sobrantes e inventario ---

def calcular_necesidades(pedidos, recetas):
    necesidades = {}
    for pedido in pedidos:
        for material, kg in pedido.necesidades(recetas[pedido.producto]).items():
            necesidades[material] = necesidades.get(material, 0) + kg
    return necesidades


def calcular_faltantes(necesidades, inventario):
    return {
        material: max(kg - inventario.get(material, 0), 0)
        for material, kg in necesidades.items()
    }


def elegir_compra(ofertas, kg_faltantes):
    """Arma las opciones de compra (cada presentación sola, o una combinada con otra
    que completa lo que falta) y se queda con la más barata; si empatan, con la que
    deja menos sobrante."""
    if kg_faltantes <= 0:
        return []

    opciones = []
    for principal in ofertas:
        maximo = principal.cantidad_para(kg_faltantes)
        opciones.append([(principal, maximo)])
        for otra in ofertas:
            if otra is principal:
                continue
            for cantidad in range(maximo):
                resto = kg_faltantes - cantidad * principal.kg
                opciones.append([(principal, cantidad), (otra, otra.cantidad_para(resto))])

    mejor = None
    for opcion in opciones:
        kg = sum(oferta.kg * cantidad for oferta, cantidad in opcion)
        costo = sum(oferta.precio * cantidad for oferta, cantidad in opcion)
        if mejor is None or (costo, kg) < (mejor["costo"], mejor["kg"]):
            mejor = {"costo": costo, "kg": kg, "opcion": opcion}

    return [
        {
            "proveedor": oferta.proveedor,
            "material": oferta.material,
            "presentacion": oferta.presentacion,
            "cantidad": cantidad,
            "kg": cantidad * oferta.kg,
            "costo": cantidad * oferta.precio,
        }
        for oferta, cantidad in mejor["opcion"]
        if cantidad > 0
    ]


def calcular_compras_y_sobrantes(faltantes, ofertas, materiales):
    compras = []
    sobrantes = []
    for material, kg_faltantes in faltantes.items():
        del_material = [oferta for oferta in ofertas if oferta.material == material]
        compra = elegir_compra(del_material, kg_faltantes)
        compras.extend(compra)

        sobrante = sum(item["kg"] for item in compra) - kg_faltantes
        if sobrante > 0:
            reutilizable = materiales[material]["reutilizable"]
            sobrantes.append({
                "material": material,
                "kg_sobrante": round(sobrante, 2),
                "destino": "reutilizar" if reutilizable else "descartar",
            })
    return compras, sobrantes
