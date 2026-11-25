# Propuesta del agente `pool`: HMA-LD + pool de rutas + set partitioning

*(estado final; resultados con el juez oficial, β = 0,2, ρ = 0)*

## Idea en una frase
Con consumo según la carga, la factibilidad de una ruta es **local** (depende solo de su secuencia y su carga) y su costo es fijo (μ1 + μ2·d), así que todas las rutas factibles que HMA-LD evalúa durante la búsqueda —cientos de miles, que hoy descarta— se guardan en un pool y un modelo de *set partitioning* (HiGHS) elige periódicamente la mejor combinación, que se re-inyecta en la búsqueda.

## Mecanismo (por qué debería funcionar)
- El consumo según la carga rompe soluciones "por ruta": una ruta que deja de alcanzar la estación obliga a HMA a re-equilibrar clientes entre rutas mediante movimientos locales de 1–2 rutas a la vez. El SP combina **muchas rutas compatibles de golpe** (un movimiento de vecindario de tamaño exponencial), y basta que existan K−1 rutas factibles disjuntas en el pool para eliminar un vehículo (−1000 en TC).
- HMA ya genera esas rutas: cada llamada a `update_route_status` que devuelve "factible" (CLS, ALS, PSI/SSI, inserciones, reparación del cruce) produce una ruta válida. Volcarlas cuesta poco (hash de 64 bits + una línea de texto).
- Deduplicación por **conjunto de clientes** (se guarda la secuencia más corta): para el SP solo importa el conjunto.
- **Verificación perezosa**: no se evalúa todo el pool con el programa lineal exacto; solo las columnas que elige el SP pasan por el evaluador exacto (mismo LP que el juez). Si alguna falla, se elimina y se re-resuelve.
- El SP arranca con la solución vigente de HMA como incumbente (`highspy.setSolution`), así que nunca empeora.

## Qué la hace nueva
- **Frente a HMA (Zheng et al., 2025)**: HMA no tiene memoria de rutas; descarta toda ruta que no queda en la solución actual. Aquí la búsqueda se vuelve una matheurística: HMA hace de generador de columnas y el SP de recombinador global.
- **Frente a Rastani y Çatay (2023) / Zachariadis et al. (2015)**: ellos incorporan la carga en la evaluación (LNS con consumo según la carga / VRPSPD con carga); no recombinan rutas por programación entera.
- **Frente a Adapt-CMSA (Akbay et al., 2022; 2024)**: CMSA resuelve con CPLEX un MILP *arc-based* restringido a los componentes (arcos) de soluciones construidas probabilísticamente; es pesado y no escala a 100 clientes con recarga parcial. Aquí el MIP es de *rutas* (100 filas, decenas de miles de columnas), la recarga parcial y el consumo según la carga quedan "dentro" de cada columna (resueltos exactamente por LP al verificar), y las columnas salen gratis de la búsqueda de un algoritmo del estado del arte.
- **Frente a ILS-SP (Subramanian et al., 2013) y otras matheurísticas de set partitioning (p. ej. Rochat-Taillard, Kelly-Xu, HGS+SP)**: la idea pool+SP es conocida en VRP clásico; lo nuevo es (i) aplicarla a EVRP-TW-SPD con recarga parcial y consumo según la carga, donde la factibilidad de una columna no es trivial (LP de recarga) y se resuelve con verificación perezosa; (ii) recolectar **todas** las rutas factibles evaluadas por el chequeo O(n) de HMA-LD (no solo óptimos locales), y (iii) medir que el efecto se concentra justamente donde la carga rompe las soluciones (reducción de vehículos).
- Honestamente: la novedad es de **aplicación e integración**, no un principio algorítmico nuevo.

## Implementación
- `fasteval.py`: evaluador rápido de rutas (condiciones necesarias + plan "recargar lo más tarde posible" como condición suficiente + LP exacto de `common/evrp.py` en los casos dudosos). Coincide con `eval_route` en 170/170 rutas publicadas probadas.
- `pool.py`: pool deduplicado, reparación de rutas con 0–2 estaciones, vecindarios (relocate, swap, 2-opt*) y ruin&recreate que alimentan el pool, SP con `scipy.optimize.milp` y con `highspy` (incumbente).
- `proto.py`: prototipo del paso 2 (desde soluciones publicadas).
- `hma-pool/`: copia de HMA-LD (base) con: `pooldump.h` (volcado deduplicado por hash de toda ruta factible, expandida con hiperarcos y en ids del problema maestro, también desde subproblemas), `--pool_file`; v2 (`bin/evrp-tw-spd-v2`): `--pool_every S --pool_tl T --pool_dir D` llama al SP cada S segundos de CPU, re-inyecta la solución si mejora y **descuenta el tiempo de pared del SP del presupuesto de HMA**.
- `sp_solve.py`: carga del pool, SP con incumbente y verificación perezosa (y pulido opcional en Python).
- `metodo_pool.py`: método para `bench.py` con el mismo presupuesto total T que HMA-LD.

## Resultados medidos (juez oficial: `check_solution(..., beta=0.2, rho=0.0, use_reported=False)`)

### Paso 2 — prototipo desde las soluciones publicadas de HMA (56 instancias de 100 clientes)
`proto.py`, 30 s por instancia, semilla 1 (`res/proto30.json`, `res/proto30.log`). Columnas: rutas publicadas reparadas (0–2 estaciones, ambas orientaciones), divisiones de rutas irreparables, clientes solos, relocate/swap/2-opt* entre rutas vecinas y ruin&recreate alrededor de la solución vigente; SP con `scipy.optimize.milp` cada ~14 s.

| | factibles (juez) | K = K publicado | K mayor |
|---|---|---|---|
| reparación mínima (`consumo_carga.py`) | 23/56 | 23 | — (33 infactibles) |
| pool + SP (30 s) | **56/56** | 40 | 16 (15 con +1, rc107_21 con +2) |

- En las 23 donde ambas son factibles: mismo K; pool mejor en 8, gap medio −0,003 % (prácticamente igual).
- De las 33 que la reparación no salva: 17 se recuperan **con el mismo número de vehículos** (todas las c2, c103/c105/c108/c109, r108, r111, r112, rc101, rc105) y 16 con un vehículo más.
- Lectura: el SP convierte "infactible" en "factible a costo casi idéntico" en la mitad de los casos difíciles, sin volver a correr HMA.

### Paso 3a — HMA-LD + pool, SP solo al final (`pool_f20`)
Mismo presupuesto T = 120 s que HMA-LD (base), 12 instancias de 100 clientes del conjunto de desarrollo × 3 semillas. HMA-LD-pool corre 0,8·T s de CPU volcando rutas; el SP (HiGHS, incumbente = solución de HMA) usa el tiempo restante hasta T. Comparación pareada por semilla con `base/resultados/hma_ld/corridas.csv` (`scripts/comparar.py`).

| instancia | HMA-LD TC medio | K medio | pool_f20 TC medio | K medio | mejor/igual/peor |
|---|---|---|---|---|---|
| c101_21 | 13047.08 | 12.00 | 13047.08 | 12.00 | 0/3/0 |
| c106_21 | 12026.81 | 11.00 | 12026.81 | 11.00 | 0/3/0 |
| c202_21 | 4641.07 | 4.00 | 4641.07 | 4.00 | 0/3/0 |
| c206_21 | 4639.88 | 4.00 | 4639.88 | 4.00 | 0/3/0 |
| r102_21 | 17763.91 | 16.33 | **16503.90** | **15.00** | 3/0/0 |
| r108_21 | 12039.08 | 11.00 | 12045.10 | 11.00 | 0/0/3 |
| r202_21 | 4081.37 | 3.00 | 4085.55 | 3.00 | 0/1/2 |
| r209_21 | 3893.36 | 3.00 | 3903.33 | 3.00 | 0/0/3 |
| rc102_21 | 15858.57 | 14.33 | 15889.72 | 14.33 | 1/1/1 |
| rc106_21 | 15094.02 | 13.67 | 14756.52 | 13.33 | 1/1/1 |
| rc202_21 | 5248.52 | 4.00 | 5248.52 | 4.00 | 0/3/0 |
| rc206_21 | 4536.75 | 3.33 | 4841.98 | 3.67 | 0/1/2 |

36/36 factibles en ambos. Mejor/igual/peor 5/19/12; vehículos totales 299 → 295 (−4); ΔTC medio por corrida −0,11 %. En las 5 corridas ganadoras el SP elimina 1–2 vehículos (p. ej. r102_21 s3: 18425,46 → 16546,62; rc106_21 s2: 15450,31 → 14422,82). Las pérdidas vienen de quitarle 20 % del tiempo a HMA cuando el SP no encuentra nada (r1/r2 con distancia), y rc206_21 es ruido de semilla de HMA (3 vs 4 vehículos).


### Paso 3b — versión final `pool_v2`: SP periódico dentro de HMA-LD con re-inyección + multiarranque
`bin/evrp-tw-spd-v2` con `--pool_every 25 --pool_tl 8` (cada 25 s de CPU de HMA se llama al SP con límite duro de 8 s; su tiempo de pared se descuenta del presupuesto de HMA; si el SP mejora, su solución reemplaza al individuo de HMA y la búsqueda sigue desde ahí). Si HMA termina antes (criterio de 20 generaciones sin mejora) y quedan ≥ 25 s, se relanza con otra semilla volcando al **mismo** pool; 12 s finales para el SP. SP: HiGHS (`highspy`, 1 hilo), incumbente, pre-filtro a 20 000 columnas, relajación lineal + filtro por costo reducido a 2 000 columnas, verificación perezosa con el LP exacto. Presupuesto T = 120 s; tiempo de pared medio 112 s (máx. 132 s), frente a 124 s (máx. 140 s) de `hma_ld_llenar`.

**Referencia justa** (también usa todo el presupuesto): `base/resultados/hma_ld_llenar` (HMA-LD multiarranque). 12 instancias de 100 clientes del conjunto de desarrollo × 3 semillas, comparación pareada por semilla:

| instancia | HMA-LD TC medio | K medio | método TC medio | K medio | Δ TC medio | mejor/igual/peor |
|---|---|---|---|---|---|---|
| c101_21 | 13046.30 | 12.00 | 13046.30 | 12.00 | +0.00 | 0/3/0 |
| c106_21 | 12024.03 | 11.00 | 12026.81 | 11.00 | +2.78 | 1/1/1 |
| c202_21 | 4641.07 | 4.00 | 4641.07 | 4.00 | +0.00 | 0/3/0 |
| c206_21 | 4639.88 | 4.00 | 4639.88 | 4.00 | +0.00 | 0/3/0 |
| r102_21 | 17429.83 | 16.00 | 16463.31 | 15.00 | -966.52 | 3/0/0 |
| r108_21 | 12033.77 | 11.00 | 12067.39 | 11.00 | +33.61 | 0/0/3 |
| r202_21 | 4073.16 | 3.00 | 4085.78 | 3.00 | +12.61 | 1/0/2 |
| r209_21 | 3893.08 | 3.00 | 3903.33 | 3.00 | +10.25 | 0/0/3 |
| rc102_21 | 15872.40 | 14.33 | 15860.57 | 14.33 | -11.84 | 2/0/1 |
| rc106_21 | 15423.75 | 14.00 | 14412.73 | 13.00 | -1011.02 | 3/0/0 |
| rc202_21 | 5250.07 | 4.00 | 5249.98 | 4.00 | -0.09 | 1/0/2 |
| rc206_21 | 4850.37 | 3.67 | 4852.48 | 3.67 | +2.11 | 2/0/1 |

Corridas pareadas: 36; factibles ref 36, método 36. Mejor/igual/peor: 13/10/13. Vehículos totales: ref 300, método 294 (Δ -6). Δ TC medio por corrida: -0.934 %.

Contra HMA-LD de una sola corrida (`base/resultados/hma_ld`): mejor/igual/peor 8/13/15, vehículos 299 → 294 (−5), ΔTC medio por corrida −0,29 % (tabla en `res/tabla_v2_vs_hmald.md`).

**Resumen de lo medido (juez oficial, 36/36 factibles en todos los métodos):**
- La ganancia es **grande y concentrada**: en r102_21 los 3 semilla eliminan un vehículo (15 vs 16; −966 de TC medio, −5,5 %) y en rc106_21 también (13 vs 14; −1011, −6,6 %). Son las instancias tipo 1 con muchos vehículos y ventanas estrechas, donde el consumo según la carga rompe rutas.
- En c1/c2 el método empata (HMA ya llega al mismo óptimo aparente).
- En r108, r202, r209 pierde 10–34 de distancia (0,3–0,8 %): el tiempo que se le quita a HMA para el SP no se recupera cuando el SP no encuentra reducción de vehículos.
- Global: −6 vehículos en 36 corridas, ΔTC medio −0,93 % por corrida, pero 13 mejores / 10 iguales / 13 peores: **no domina** a la referencia.

## Límites honestos
- Solo conjunto de desarrollo (12 instancias de 100 clientes, 3 semillas, T = 120 s, no 630 s). No se corrió el conjunto reservado ni las pequeñas con la versión final; no hay prueba estadística (Wilcoxon) por falta de cuota.
- La mejora media (−0,93 %) la explican 2 de 12 instancias; en distancia pura el método es algo peor en r1/r2 con pocos vehículos.
- El pool se vuelca desde el chequeo O(n) de HMA-LD (su propia política de recarga); el SP solo puede recombinar rutas que HMA ya vio. No se generan columnas "conscientes de la carga" nuevas dentro de la versión final (el pulido en Python existe, `--polish`, pero no se midió en el banco).
- El MIP no se resuelve a optimalidad en las instancias con muchas columnas (filtro heurístico a 2 000 columnas); el SP es un recombinador heurístico.
- Novedad metodológica moderada: pool + set partitioning es conocido (Subramanian et al., 2013; Adapt-CMSA de Akbay et al.). Lo nuevo es la integración con HMA-LD, la verificación perezosa con el LP exacto de recarga y la evidencia de que la ganancia aparece justo donde el consumo según la carga obliga a un vehículo extra.
- Los tiempos usan la máquina compartida; HMA mide CPU y el SP pared, de modo que la contabilidad favorece levemente a la referencia (el SP se cobra en pared).

