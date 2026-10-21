import math

KG_POR_QUINTAL = 50


class Pedido:
    def __init__(self, codigo, fecha, cliente, producto, quintales):
        self.codigo = codigo
        self.fecha = fecha
        self.cliente = cliente
        self.producto = producto
        self.quintales = quintales

    def kg_totales(self):
        return self.quintales * KG_POR_QUINTAL

    def necesidades(self, receta):
        """Kg de cada material que lleva el pedido según la receta de su producto."""
        return {material: kg * self.quintales for material, kg in receta.items()}

    def __str__(self):
        return f"{self.codigo} | {self.fecha} | {self.cliente} | {self.producto} | {self.quintales:g} qq"


class Oferta:
    def __init__(self, proveedor, ciudad, material, presentacion, kg, precio):
        self.proveedor = proveedor
        self.ciudad = ciudad
        self.material = material
        self.presentacion = presentacion
        self.kg = kg
        self.precio = precio

    def cantidad_para(self, kg_faltantes):
        """Cuántas presentaciones hacen falta para cubrir los kg pedidos."""
        if kg_faltantes <= 0:
            return 0
        # Redondeo para que errores de coma flotante (ej. 30.0000001) no sumen una bolsa de más
        return math.ceil(round(kg_faltantes / self.kg, 6))

    def __str__(self):
        return f"{self.proveedor} ({self.ciudad}): {self.presentacion} de {self.kg:g} kg a ${self.precio:,}"
