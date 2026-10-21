import sys
from pathlib import Path

from fuentes import ErrorDatos, FuenteCSV, crear_fuente
from pipeline import (preparar_materiales, preparar_recetas, preparar_ofertas, preparar_cantidades,
                      limpiar_pedidos, calcular_necesidades, calcular_faltantes,
                      calcular_compras_y_sobrantes, verificar_cupos, actualizar_inventario,
                      verificar_resultado, guardar_csv)

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_DATOS = RAIZ / "data"
CARPETA_SALIDA = RAIZ / "outputs"


def planificar(ruta_pedidos, carpeta_datos=CARPETA_DATOS):
    fuente = FuenteCSV()
    materiales = preparar_materiales(fuente.cargar(carpeta_datos / "materiales.csv"))
    recetas = preparar_recetas(fuente.cargar(carpeta_datos / "recetas.csv"), materiales)
    ofertas = preparar_ofertas(fuente.cargar(carpeta_datos / "proveedores.csv"), materiales)
    inventario = preparar_cantidades(fuente.cargar(carpeta_datos / "inventario.csv"),
                                     "inventario", "kg_disponible", materiales)
    cupos = preparar_cantidades(fuente.cargar(carpeta_datos / "permisos.csv"),
                                "permisos", "cupo_anual_kg", materiales)

    registros = crear_fuente(ruta_pedidos).cargar(ruta_pedidos)
    pedidos, rechazos = limpiar_pedidos(registros, recetas)

    necesidades = calcular_necesidades(pedidos, recetas)
    faltantes = calcular_faltantes(necesidades, inventario)
    compras, sobrantes = calcular_compras_y_sobrantes(faltantes, ofertas, materiales)
    avisos = verificar_cupos(compras, cupos)
    inventario_nuevo = actualizar_inventario(inventario, necesidades, compras, sobrantes)
    verificar_resultado(faltantes, compras, inventario_nuevo)

    return {
        "materiales": materiales,
        "leidos": len(registros),
        "pedidos": pedidos,
        "rechazos": rechazos,
        "compras": compras,
        "sobrantes": sobrantes,
        "avisos": avisos,
        "inventario_nuevo": inventario_nuevo,
    }


def mostrar_resultados(resultado):
    materiales = resultado["materiales"]
    print(f"Pedidos leídos: {resultado['leidos']} | válidos: {len(resultado['pedidos'])} "
          f"| rechazados: {len(resultado['rechazos'])}")
    for rechazo in resultado["rechazos"]:
        print(f"  Fila {rechazo['fila']} ({rechazo['id']}): {rechazo['motivo']}")

    print("Lista de compras:")
    for item in resultado["compras"]:
        print(f"  {item['proveedor']}: {item['cantidad']} {item['presentacion']} de "
              f"{materiales[item['material']]['nombre']} ({item['kg']:g} kg) - ${item['costo']:,}")
    total = sum(item["costo"] for item in resultado["compras"])
    print(f"  Total: ${total:,}")

    print("Sobrantes:")
    for sobrante in resultado["sobrantes"]:
        print(f"  {materiales[sobrante['material']]['nombre']}: "
              f"{sobrante['kg_sobrante']:g} kg ({sobrante['destino']})")

    for aviso in resultado["avisos"]:
        print(f"AVISO: {aviso}")

    print("Inventario actualizado:")
    for material, kg in resultado["inventario_nuevo"].items():
        print(f"  {materiales[material]['nombre']}: {kg:g} kg")


def guardar_resultados(resultado, carpeta):
    carpeta.mkdir(exist_ok=True)
    if resultado["compras"]:
        guardar_csv(resultado["compras"], carpeta / "compras.csv")
    if resultado["sobrantes"]:
        guardar_csv(resultado["sobrantes"], carpeta / "sobrantes.csv")
    if resultado["rechazos"]:
        guardar_csv(resultado["rechazos"], carpeta / "rechazos.csv")
    guardar_csv([{"material": m, "kg_disponible": kg} for m, kg in resultado["inventario_nuevo"].items()],
                carpeta / "inventario_actualizado.csv")


def main(ruta_pedidos):
    try:
        resultado = planificar(ruta_pedidos)
    except (ErrorDatos, FileNotFoundError) as error:
        sys.exit(f"Error: {error}")
    mostrar_resultados(resultado)
    guardar_resultados(resultado, CARPETA_SALIDA)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit("Uso: python src/main.py [archivo_de_pedidos.csv | archivo_de_pedidos.json]")
    main(Path(sys.argv[1]) if len(sys.argv) == 2 else CARPETA_DATOS / "pedidos.csv")
