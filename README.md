# POAD-TP2 – Planificación de compras de materiales para pedidos de pólvora

**Autor:** Pedro Luis Fuentes Prieto · Programación Orientada a Datos · UCA 2026

## Problema
Una empresa que vende pólvora por quintal recibe pedidos de distintos clientes.
Para cumplirlos tiene que comprar materiales, pero los proveedores los venden
en presentaciones cerradas (bolsas, bultos, costales), así que casi siempre se compra
de más. Parte de ese sobrante se puede guardar para la próxima tanda y parte
se descarta. También debe llevar un inventario de los materiales disponibles
para aprovecharlos antes de comprar. Hoy ese cálculo se hace a mano.

## Usuario y solución
Lo usaría la persona que hace las compras de la empresa. El programa lee los pedidos
(en CSV o JSON) y los datos de materiales, recetas, proveedores, inventario y permisos;
aparta los pedidos con errores, calcula cuánto material hace falta, descuenta el inventario
y arma la compra más barata con las presentaciones de los proveedores. Muestra:
- la lista de compras por proveedor y su costo total;
- los sobrantes, separando lo que se reutiliza de lo que se descarta;
- un aviso si la compra de un material controlado supera el cupo anual del permiso;
- el inventario que queda después de atender los pedidos;
- los pedidos rechazados y el motivo.

### Alcance de esta versión
Incluye un solo período de compras (todos los pedidos del archivo juntos) y combina hasta dos
presentaciones por material. Queda fuera: plazos de entrega de los proveedores, descuentos
por volumen, fechas de vencimiento de los materiales y la planificación de la producción.

## Datos
Los datos son **ficticios**, armados para el trabajo. Procedencia, variables y limitaciones
en [`data/README.md`](data/README.md). Cada fila de `pedidos.csv` / `pedidos.json` es un
pedido de un cliente: id, fecha, cliente, producto y cantidad en quintales
(56 filas: 50 válidas y 6 con errores a propósito).

Se toma 1 quintal = 50 kg, como se usa en Colombia. Las recetas parten de la
proporción clásica de la pólvora negra: 75 % nitrato de potasio, 15 % carbón y 10 % azufre.

### Marco regulatorio
El Decreto 2174 de 2023 (art. 2.2.4.2.6) establece que el nitrato de potasio es una materia
prima controlada: para adquirirlo hace falta un permiso del Departamento Control Comercio
de Armas, Municiones y Explosivos, que se pide declarando la cantidad requerida y un plan
anual de fabricación. Por eso `permisos.csv` tiene un cupo anual y el programa avisa
si una compra lo supera.

**Supuesto:** el cupo de 10.000 kg y el volumen de los pedidos (unos 6.900 kg de nitrato)
son supuestos que en la realidad no serían posibles, por el límite máximo que autoriza el permiso.
Se usan solo para tener las 50 observaciones que pide la consigna y poder probar el programa.

## Instalación y ejecución
No requiere bibliotecas externas (Python 3.10 o superior). Desde la carpeta del proyecto:
```bash
python src/main.py                     # usa data/pedidos.csv
python src/main.py data/pedidos.json   # mismos pedidos en JSON
```
Los resultados se muestran por pantalla y se guardan en `outputs/`: `compras.csv`,
`sobrantes.csv`, `inventario_actualizado.csv` y `rechazos.csv`. Si una lista de compras,
sobrantes o rechazos queda vacía, su CSV anterior se elimina. Los archivos de `data/` no se modifican.

## Pruebas
```bash
python -m unittest discover -s tests -v
```
Prueban casos normales (cálculos conocidos), entradas inválidas (fechas imposibles, ids mal
escritos, duplicados, faltantes, JSON roto, archivos inexistentes) y propiedades del resultado:
que la lectura CSV y JSON dé lo mismo y que se conserven las cantidades
(inventario inicial + comprado − consumido − descartado = inventario final).

## Organización del código
| Archivo | Contenido |
|---|---|
| `src/fuentes.py` | `FuenteDatos` (clase abstracta con `cargar(ruta)`), `FuenteCSV`, `FuenteJSON`, `crear_fuente()` según la extensión y `ErrorDatos` |
| `src/modelo.py` | `Pedido` (calcula los kg de cada material que necesita) y `Oferta` (cuántas presentaciones hacen falta para cubrir una cantidad) |
| `src/pipeline.py` | validación del esquema, preparación de las tablas, limpieza de pedidos, cálculo de compras, sobrantes, cupos e inventario, y guardado |
| `src/main.py` | coordina la lectura, el cálculo, la muestra por pantalla y el guardado |
| `tests/test_planificacion.py` | pruebas con `unittest` |

Las dos fuentes devuelven lo mismo (una lista de diccionarios), así que el resto del programa
no depende del formato del archivo de pedidos.

## Cómo funciona
1. Lee las tablas de referencia y comprueba que tengan las columnas necesarias.
2. Valida y limpia los pedidos (ver reglas abajo).
3. Suma lo que necesitan todos los pedidos válidos de cada material y descuenta el inventario.
4. Para lo que falta prueba cada presentación sola y combinada con otra que complete lo que
   falta, y elige la opción más barata. Si dos cuestan lo mismo, la que deja menos sobrante.
5. Separa el sobrante: si el material es reutilizable se guarda; si no, se descarta.
6. Avisa si la compra de un material controlado supera el cupo anual.
7. Calcula el inventario final y verifica que las compras cubran lo que falta y que
   ningún material quede negativo.

## Decisiones de limpieza
- **Tablas de referencia** (materiales, recetas, proveedores, inventario, permisos): un error
  ahí (material desconocido o repetido, receta que no suma 50 kg, número inválido o negativo,
  material sin proveedor) detiene el programa con un mensaje, porque sin esos datos
  no se puede calcular nada confiable.
- **Pedidos**: una fila con errores se aparta, se informa y se guarda en `outputs/rechazos.csv`
  con su número de fila (contando desde 1), el id y los motivos. Se rechaza si:
  - el id no tiene la forma `PED-` y tres dígitos (expresión regular `PED-\d{3}`);
  - la fecha no tiene la forma `AAAA-MM-DD` (expresión regular `\d{4}-\d{2}-\d{2}`) o no existe
    en el calendario (por ejemplo `2026-11-31`), lo que se comprueba con `datetime.strptime`;
  - falta el cliente, el producto no tiene receta, o los quintales faltan (vacío en CSV,
    `null` en JSON), son booleanos, no son un número o no son positivos;
  - el id ya fue aceptado antes: se conserva la primera aparición.
- Si no queda ningún pedido válido, el programa se detiene.

## Resultado de ejemplo
```
$ python src/main.py
Pedidos leídos: 56 | válidos: 50 | rechazados: 6
  Fila 13 (PED-012): id duplicado
  Fila 19 (PED17): id con formato inválido
  Fila 26 (PED-051): fecha inválida
  Fila 34 (PED-052): producto sin receta
  Fila 42 (PED-053): quintales fuera de rango
  Fila 48 (PED-054): cliente faltante; quintales faltante
Lista de compras:
  Químicos del Pacífico: 1 bolsa de Nitrato de potasio (25 kg) - $310,000
  Insumos Andinos: 137 bulto de Nitrato de potasio (6850 kg) - $80,830,000
  Carbonera El Roble: 70 costal de Carbón vegetal (1400 kg) - $4,200,000
  Azufrera del Norte: 18 bulto de Azufre (900 kg) - $3,240,000
  Distribuidora La Sabana: 2 bolsa de Grafito (10 kg) - $170,000
  Distribuidora La Sabana: 2 bolsa de Dextrina (50 kg) - $240,000
  Total: $88,990,000
Sobrantes:
  Nitrato de potasio: 3.5 kg (reutilizar)
  Carbón vegetal: 12.5 kg (descartar)
  Azufre: 5 kg (reutilizar)
  Grafito: 0.25 kg (reutilizar)
  Dextrina: 8.75 kg (descartar)
Inventario actualizado:
  Nitrato de potasio: 3.5 kg
  Azufre: 5 kg
  Carbón vegetal: 0 kg
  Grafito: 0.25 kg
  Dextrina: 0 kg
```

## Interpretación y limitaciones
- Para cubrir los 50 pedidos hay que gastar $88.990.000. Conviene comprar casi todo el nitrato
  en bultos de 50 kg porque el kilo sale más barato que en bolsa, y completar con una bolsa
  de 25 kg para no comprar un bulto entero de más.
- El sobrante de carbón y dextrina se pierde porque esos materiales no se pueden guardar;
  el del resto queda en el inventario para la próxima compra.
- Los 6 pedidos rechazados no entran en el cálculo: hay que corregirlos y volver a correr el programa.
- Los datos son ficticios: los montos sirven para mostrar cómo funciona el programa, no
  para decidir una compra real.
- El cupo de nitrato y la cantidad de pedidos son supuestos imposibles en la práctica por el
  límite máximo del permiso (ver Marco regulatorio).
- Solo se combinan dos presentaciones por material; con tres o más proveedores de un
  mismo material podría existir una compra un poco más barata.
- El cupo se compara con lo que se compra ahora; no se lleva la cuenta de lo comprado
  antes en el año.
