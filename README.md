# POAD-TP2 – Planificación de compras de materiales para pedidos de pólvora

**Autor:** Pedro Luis Fuentes Prieto · Programación Orientada a Datos · UCA 2026

## Problema
Una empresa que vende pólvora por quintal recibe pedidos de distintos clientes.
Para cumplirlos tiene que comprar materiales, pero los proveedores los venden
en presentaciones cerradas (bolsas, bidones), así que casi siempre se compra
de más. Parte de ese sobrante se puede guardar para la próxima tanda y parte
se descarta. También debe llevar un inventario de los materiales disponibles
para aprovecharlos antes de comprar. Hoy ese cálculo se hace a mano.

## Pregunta
Dado un conjunto de pedidos y el inventario disponible, ¿cuánto de cada material hay que comprar,
en las presentaciones que vende el proveedor, y cuánto sobra,
separando lo que se puede reutilizar de lo que se descarta?

## Datos
- Proveedores: se armará una lista con sus datos y las condiciones de compra.
  Las variables de esta lista se definirán más adelante.
- Pedidos: cada uno con fecha, producto y cantidad en quintales.
  Se armará una lista de pedidos; sus variables definitivas se aclararán más adelante.
- Materiales: cuánto de cada material lleva un quintal de producto,
  en qué presentación se compra y si el sobrante es reutilizable.
- Inventario: cantidad disponible de cada material, incluidos los sobrantes
  reutilizables de pedidos anteriores.
- Fuente de los datos: a definir.

## Cómo funcionará la app
El programa trabajará a partir de las listas de proveedores y pedidos,
junto con los datos de los materiales y el inventario disponible. Sumará las
necesidades de los pedidos, descontará lo que ya haya en inventario y calculará
cuánto comprar para cubrir lo faltante según las presentaciones de los proveedores.
Mostrará una lista de compras y los sobrantes, separando lo reutilizable
de lo que se descarta. Una vez atendidos los pedidos, actualizará el inventario
con las compras y los consumos, conservando los sobrantes reutilizables
y excluyendo lo descartado.

## Lenguaje
Todo el trabajo se hace únicamente en Python.
