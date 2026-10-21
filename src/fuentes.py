import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class ErrorDatos(ValueError):
    """Los datos no cumplen lo que el programa necesita para planificar."""


class FuenteDatos(ABC):
    @abstractmethod
    def cargar(self, ruta):
        """Devuelve los registros del archivo como una lista de diccionarios."""

    def comprobar_archivo(self, ruta):
        if not Path(ruta).is_file():
            raise FileNotFoundError(f"No existe el archivo: {Path(ruta).name}")


class FuenteCSV(FuenteDatos):
    def cargar(self, ruta):
        self.comprobar_archivo(ruta)
        with open(ruta, encoding="utf-8", newline="") as archivo:
            return list(csv.DictReader(archivo))


class FuenteJSON(FuenteDatos):
    def cargar(self, ruta):
        self.comprobar_archivo(ruta)
        with open(ruta, encoding="utf-8") as archivo:
            try:
                datos = json.load(archivo)
            except json.JSONDecodeError:
                raise ErrorDatos(f"{Path(ruta).name} no es un JSON válido")
        if not isinstance(datos, list) or not all(isinstance(fila, dict) for fila in datos):
            raise ErrorDatos(f"{Path(ruta).name}: el contenido debe ser una lista de registros")
        return datos


def crear_fuente(ruta):
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ErrorDatos(f"Formato no soportado: {Path(ruta).name} (se acepta .csv o .json)")
