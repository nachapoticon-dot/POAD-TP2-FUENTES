# Datos

## Procedencia
- **Fuente:** datos ficticios armados por el autor (Pedro Luis Fuentes Prieto) para este trabajo,
  el 21/10/2026. No salen de ninguna empresa real.
- **Nombres:** proveedores y clientes son inventados. Las ciudades son de Colombia porque el
  problema se plantea allí (quintal de 50 kg y la normativa sobre el nitrato de potasio).
- **Valores:** precios, presentaciones, recetas, pedidos, inventario y cupo fueron inventados
  con valores razonables. Las recetas siguen la proporción clásica 75/15/10 de la pólvora negra.
- **Licencia:** uso libre para fines educativos.

## Archivos
| Archivo | Cada fila es | Variables |
|---|---|---|
| `pedidos.csv` | un pedido de un cliente | `id` (PED-000), `fecha` (AAAA-MM-DD), `cliente`, `producto`, `quintales` |
| `materiales.csv` | un material | `id`, `nombre`, `controlado` (si/no), `reutilizable` (si/no) |
| `recetas.csv` | un material dentro de la receta de un producto | `producto`, `material`, `kg_por_quintal` |
| `proveedores.csv` | una presentación que vende un proveedor | `proveedor`, `ciudad`, `material`, `presentacion`, `kg_por_presentacion`, `precio_cop` (pesos colombianos) |
| `inventario.csv` | un material en depósito | `material`, `kg_disponible` |
| `permisos.csv` | un material controlado | `material`, `cupo_anual_kg` |

Todas las cantidades están en kg, salvo los pedidos, que están en quintales (1 quintal = 50 kg).

`pedidos.csv` tiene 56 pedidos, de octubre a diciembre de 2026. Un valor faltante es una celda vacía.
Seis filas tienen errores a propósito para probar la limpieza: un id duplicado, un id mal
escrito, una fecha que no existe, un producto sin receta, una cantidad en cero y una fila
sin cliente ni cantidad.

## Limitaciones
- Al ser datos inventados no reflejan precios ni demanda reales.
- El cupo de 10.000 kg de `permisos.csv` y el volumen de los 50 pedidos son supuestos que no
  serían posibles en la realidad por el límite máximo que autoriza el permiso para el nitrato
  de potasio; se eligieron para cumplir con la cantidad de observaciones pedida.
- Hay una sola presentación por proveedor y material, y como mucho dos proveedores por material.
- No hay datos de plazos de entrega, descuentos ni vencimientos.
