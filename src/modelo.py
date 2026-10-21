KG_POR_QUINTAL = 50


class Oferta:
    def __init__(self, proveedor, ciudad, material, presentacion, kg, precio):
        self.proveedor = proveedor
        self.ciudad = ciudad
        self.material = material
        self.presentacion = presentacion
        self.kg = kg
        self.precio = precio

    def __str__(self):
        return f"{self.proveedor} ({self.ciudad}): {self.presentacion} de {self.kg:g} kg a ${self.precio:,}"
