# PROPUESTA del agente `combinado`: HMA-LD-afín + pool de rutas con set partitioning + eliminación de vehículos consciente de la carga

*(Todas las cifras son del juez oficial `common/evrp.py: check_solution(..., beta=0.2, rho=0.0, use_reported=False)`, medidas con `base/bench.py`.)*

## 1. Idea en una frase
La evaluación afín concatenable (agente `afin`) libera tiempo de CPU dentro de HMA-LD; ese tiempo se gasta en (i) un *set partitioning* periódico sobre el pool de rutas factibles que HMA ya genera (agente `pool`) y (ii) un operador de eliminación de vehículos que expulsa la ruta más fácil de vaciar y reinserta sus clientes con la factibilidad exacta de batería según la carga, porque en este problema las ganancias grandes vienen de ahorrar un vehículo (μ1 = 1000).

## 2. Mecanismo
1. **Afín (`--afin 2`, margen 1e-4):** la batería con consumo e_ij(L) = h·d_ij·(1 + βL/C) es afín en la carga de entrada de cada segmento, así que la inserción de estaciones y la verificación de batería de cada movimiento de la búsqueda conservadora (CLS) se hacen en O(1) por candidato, sin copiar la solución. Con el mismo criterio de parada, HMA-LD-afín llega al mismo punto en ≈ 60 % del tiempo (agente `afin`).
2. **Pool + SP (agente `pool`, versión v2):** toda ruta que `update_route_status` declara factible se vuelca (deduplicada por conjunto de clientes, se guarda la secuencia más corta). Cada 25 s de CPU de HMA se llama a `pool/sp_solve.py` (HiGHS con 1 hilo, límite 8 s, incumbente = solución vigente), las columnas elegidas se verifican con el LP exacto del juez (verificación perezosa) y, si mejora, la solución del SP reemplaza al individuo de HMA. El tiempo de pared del SP se descuenta del presupuesto de HMA. Si HMA se detiene antes (20 generaciones sin mejora) se relanza con otra semilla volcando al mismo pool; 12 s finales para un último SP.
   - Cambio respecto de `pool`: como afín termina antes, se relanza HMA si quedan ≥ 10 s (en `pool` eran 25 s), para que el tiempo liberado por afín no se pierda.
3. **Eliminación de vehículos (`--elim 4 --elim_t 1`, nuevo):** cada 5 s de CPU (como mucho una vez por generación de HMA) se toma la mejor solución, se ordenan las rutas por facilidad de eliminación (menos clientes y, a igualdad, menos carga transportada) y se intenta vaciar una de las 4 más fáciles (rotando entre llamadas). Sus clientes entran a una pila de expulsión (*ejection pool*, simplificación de Nagata y Bräysy 2009): cada cliente se inserta en su mejor posición factible en las demás rutas; si no cabe en ninguna, se inserta expulsando **un** cliente w de alguna ruta (el de menor contador de expulsiones, luego menor desvío), que pasa a la pila. Se detiene al vaciar la pila (solución con K − 1 rutas, que reemplaza a la vigente si es más barata) o al agotar 1 s de CPU.
   - **Consciente de la carga:** cada inserción candidata se evalúa con `afin_station_insertion`, es decir, con la factibilidad *exacta* de ventanas, capacidad y batería con consumo según la carga y con las estaciones re-insertadas de forma óptima. El costo de insertar un cliente incluye el desvío a estaciones que provoca su carga extra en los arcos siguientes. HMA, en cambio, construye y repara en el espacio relajado (sin batería) y arregla la batería después.
   - Poda barata antes de la evaluación exacta: ventana (llegada más temprana desde el predecesor > l_c) y desvío de distancia sin estaciones ≥ mejor desvío encontrado.
4. **Reordenamiento intra-ruta con costo real (`--reord 1`, probado y descartado):** reubicar cada cliente dentro de su ruta evaluando distancia + estaciones óptimas con afín (adelantar entregas grandes o atrasar recogidas grandes baja la carga en los arcos largos). Ver resultados: no encontró ninguna mejora, por lo que no forma parte del método final.

## 3. Qué es nuevo
- **Frente a HMA (Zheng, Liu y Ong 2025):** HMA no tiene memoria de rutas ni un operador de reducción de flota; sus vecindarios se evalúan en el espacio relajado sin batería y la batería se verifica o repara después. Aquí (a) la batería según la carga se evalúa en O(1) dentro de la búsqueda (afín), (b) las rutas evaluadas se recombinan globalmente con SP y (c) hay un operador explícito de eliminación de vehículos cuyas inserciones ya son factibles en batería con consumo según la carga.
- **Frente a Rastani y Çatay (2023):** también tratan consumo según la carga (ALNS con evaluación arco a arco), pero sin resúmenes concatenables, sin recombinación por SP de las rutas visitadas y sin un operador de reducción de flota con pila de expulsión que use la factibilidad exacta de recarga parcial con ventanas.
- **Frente a Zachariadis, Tarantilis y Kiranoudis (2015):** su dependencia de la carga está en el objetivo (costo = distancia × carga) y no hay batería, estaciones ni recarga; aquí la dependencia es una restricción de batería que interactúa con recarga parcial y ventanas.
- **Honestamente:** cada pieza por separado es conocida (resúmenes de Vidal et al. extendidos por `afin`; pool + SP al estilo ILS-SP de Subramanian et al. 2013; pila de expulsión de Nagata y Bräysy 2009). Lo nuevo es la integración para VRPSPDTW-E con consumo según la carga, y la evidencia de que la combinación es más que la suma: afín libera tiempo que el SP y la eliminación usan para lo que más vale en este problema (vehículos).

## 4. Implementación
- `hma-comb/`: copia de `afin/hma-afin` (HMA-LD + afín) a la que se aplicó el parche de `pool/hma-pool` respecto de `base/hma-ld` (`pooldump.h`, `pooldump_sol.h`, envoltorios de `update_route_status`, volcados en CLS/LNS/cruce, SP periódico y re-inyección en `search_framework.cpp`, opciones `--pool_*`). El parche entró sin conflictos (solo desplazamientos).
  - `src/mov_carga.{h,cpp}` (nuevo): `elim_ruta` (eliminación con pila de expulsión y evaluación afín exacta) y `reord_rutas` (reordenamiento intra-ruta con costo real). Opciones `--elim N` (rutas candidatas, 0 = no), `--elim_t` (CPU por intento, 1 s), `--elim_every` (5 s), `--reord 0/1`, `--pool_afin 0/1` (volcar también las rutas que acepta afín; no usado en lo medido).
  - Compilar: `cd hma-comb && g++ -std=c++11 -O3 -o bin/evrp-comb src/*.cpp`.
- `metodo_comb.py`: envoltorio para `bench.py`, derivado de `pool/metodo_pool.py` (presupuesto total T en tiempo de pared, que incluye HMA, cada SP y el SP final; reinicios de HMA; mejor solución aceptada por el juez). Usa `pool/sp_solve.py` sin cambios (HiGHS `threads=1`). Opciones nuevas: `--extra` (opciones del binario) y `--min-restart`.
- Comando final (`cmd_final.txt`):
  `python3 /home/user/oe3/combinado/metodo_comb.py --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla} --beta {beta} --rho {rho} --v2 --every 25 --tl 8 --restart --t-final 12 --min-restart 10 --extra "--afin 2 --elim 4 --elim_t 1"`
- `correr.sh` (reparte instancias en 3 procesos `bench.py` de un hilo, reanudable), `unir.py`, `comparar.py` (tabla pareada, signos y Wilcoxon con scipy), `correr_reservado.sh`.

## 5. Resultados (juez oficial, β = 0,2, ρ = 0)

### 5.1 Ablación en desarrollo (12 instancias de 100 clientes × semillas 1–3, 120 s, pareado con `base/resultados/hma_ld_llenar`)
Todas las variantes: 36/36 corridas factibles. CPU medio por corrida: referencia 121,9 s (máx. 138,1); afín+pool 110,2 s (máx. 118,3); final 111,2 s (máx. 118,3). El método nunca usa más CPU que la referencia.

| variante | K total (ref 300) | ΔTC medio por par | mejor/igual/peor | signos p | Wilcoxon p |
|---|---|---|---|---|---|
| afín solo (`afin/resultados/hma_ld_afin_llenar`, ronda 1) | 296 | −1,44 % | 17/11/8 | 0,11 | 0,019 |
| pool solo (`pool/resultados/pool_v2`, ronda 1) | 294 | −0,93 % | 13/10/13 | 1,0 | 0,48 |
| **afín + pool** (`resultados/comb_afin_pool`) | 292 | −2,16 % | 18/11/7 | 0,043 | 0,00038 |
| **afín + pool + eliminación** (final, `resultados/comb_afin_pool_elim`) | **290** | **−2,83 %** | 18/10/8 | 0,076 | 0,00093 |

- La combinación afín+pool es mejor que cada pieza por separado: frente a afín solo, −0,71 % y −4 vehículos (13/15/8, Wilcoxon p = 0,15); frente a pool solo, −1,21 % y −2 vehículos (21/11/4, signos p = 0,0009).
- La eliminación de vehículos agrega −0,66 % y −2 vehículos (c106_21 y rc202_21) frente a afín+pool, pero pareado es 8/21/7 (Wilcoxon p = 0,39): **su aporte no es significativo** con 36 corridas.
- Reordenamiento intra-ruta con costo real (`--reord 1`): en una corrida de prueba (r102_21, 60 s) hizo 141 llamadas y **0 mejoras** (1,3 s de CPU). Se descartó y no se midió en el banco.

Tabla por instancia del método final (desarrollo):

| instancia | TC medio hma_ld_llenar | K medio hma_ld_llenar | TC medio afin+pool+elim | K medio afin+pool+elim | ΔTC medio (%) | mejor/igual/peor |
|---|---|---|---|---|---|---|
| c101_21 | 13046.30 | 12.00 | 13046.30 | 12.00 | +0.00 | 0/3/0 |
| c106_21 | 12024.03 | 11.00 | 11392.13 | 10.33 | -5.26 | 2/1/0 |
| c202_21 | 4641.07 | 4.00 | 4641.07 | 4.00 | +0.00 | 0/3/0 |
| c206_21 | 4639.88 | 4.00 | 4639.88 | 4.00 | +0.00 | 0/3/0 |
| r102_21 | 17429.83 | 16.00 | 17116.62 | 15.67 | -1.80 | 1/0/2 |
| r108_21 | 12033.77 | 11.00 | 12048.36 | 11.00 | +0.12 | 0/0/3 |
| r202_21 | 4073.16 | 3.00 | 4055.99 | 3.00 | -0.42 | 2/0/1 |
| r209_21 | 3893.08 | 3.00 | 3885.32 | 3.00 | -0.20 | 2/0/1 |
| rc102_21 | 15872.40 | 14.33 | 15536.70 | 14.00 | -2.03 | 2/0/1 |
| rc106_21 | 15423.75 | 14.00 | 14406.06 | 13.00 | -6.60 | 3/0/0 |
| rc202_21 | 5250.07 | 4.00 | 4975.45 | 3.67 | -5.23 | 3/0/0 |
| rc206_21 | 4850.37 | 3.67 | 4214.33 | 3.00 | -12.51 | 3/0/0 |

- Corridas pareadas: 36; factibles (juez oficial): hma_ld_llenar 36/36, afin+pool+elim 36/36.
- Vehículos totales (pares factibles): hma_ld_llenar 300, afin+pool+elim 290 (Δ -10).
- ΔTC medio por par: -2.827 % (mín -18.15 %, máx +0.29 %).
- afin+pool+elim mejor / igual / peor: 18/10/8.
- Prueba de signos (bilateral, sin empates): p = 0.076.
- Wilcoxon de rangos con signo (bilateral, diferencias de TC sin empates, n = 26): p = 0.00093.

Pequeñas de desarrollo (12 instancias, semilla 1, 105 s) frente a `base/resultados/hma_ld`: 12/12 factibles, mismos vehículos (27); 11 empates y r201C10 mejora de 1265,05 a 1263,76 (`resultados/peq_dev_vs_hmald.md`). No se rompe nada.

### 5.2 Prueba final en el conjunto reservado (nunca usado para ajustar)
44 instancias de 100 clientes × semillas 1 y 2, 120 s. La referencia `hma_ld_llenar` se corrió con el mismo envoltorio de `base` (`--llenar`) en `resultados/res_hma_ld_llenar`; el método final está en `resultados/res_final`. CPU medio por corrida: referencia 122,1 s (máx. 136,6); final 113,1 s (máx. 119,1).

| instancia | TC medio hma_ld_llenar | K medio hma_ld_llenar | TC medio final | K medio final | ΔTC medio (%) | mejor/igual/peor |
|---|---|---|---|---|---|---|
| c102_21 | 12035.14 | 11.00 | 12032.89 | 11.00 | -0.02 | 1/1/0 |
| c103_21 | 10964.48 | 10.00 | 10963.65 | 10.00 | -0.01 | 1/1/0 |
| c104_21 | 10886.01 | 10.00 | 10887.47 | 10.00 | +0.01 | 1/0/1 |
| c105_21 | 12029.82 | 11.00 | 12029.82 | 11.00 | +0.00 | 0/2/0 |
| c107_21 | 11528.82 | 10.50 | 11040.75 | 10.00 | -4.07 | 2/0/0 |
| c108_21 | 11022.79 | 10.00 | 11017.79 | 10.00 | -0.05 | 2/0/0 |
| c109_21 | 10944.22 | 10.00 | 10928.84 | 10.00 | -0.14 | 2/0/0 |
| c201_21 | 4642.84 | 4.00 | 4642.84 | 4.00 | +0.00 | 0/2/0 |
| c203_21 | 4642.84 | 4.00 | 4641.07 | 4.00 | -0.04 | 2/0/0 |
| c204_21 | 4638.08 | 4.00 | 4635.80 | 4.00 | -0.05 | 2/0/0 |
| c205_21 | 4639.88 | 4.00 | 4639.88 | 4.00 | +0.00 | 0/2/0 |
| c207_21 | 4639.88 | 4.00 | 4639.88 | 4.00 | +0.00 | 0/2/0 |
| c208_21 | 4639.88 | 4.00 | 4639.88 | 4.00 | +0.00 | 0/2/0 |
| r101_21 | 19612.37 | 18.00 | 18682.28 | 17.00 | -4.74 | 2/0/0 |
| r103_21 | 15236.04 | 14.00 | 14250.74 | 13.00 | -6.47 | 2/0/0 |
| r104_21 | 13069.27 | 12.00 | 12574.79 | 11.50 | -3.78 | 1/0/1 |
| r105_21 | 16370.19 | 15.00 | 15391.61 | 14.00 | -5.98 | 2/0/0 |
| r106_21 | 14287.87 | 13.00 | 14287.51 | 13.00 | -0.00 | 1/0/1 |
| r107_21 | 13127.28 | 12.00 | 13125.01 | 12.00 | -0.02 | 2/0/0 |
| r109_21 | 14197.72 | 13.00 | 13207.04 | 12.00 | -6.98 | 2/0/0 |
| r110_21 | 13094.64 | 12.00 | 13090.50 | 12.00 | -0.03 | 1/0/1 |
| r111_21 | 13106.83 | 12.00 | 13088.12 | 12.00 | -0.14 | 2/0/0 |
| r112_21 | 13042.17 | 12.00 | 12042.02 | 11.00 | -7.67 | 2/0/0 |
| r201_21 | 5160.31 | 4.00 | 4273.88 | 3.00 | -17.18 | 2/0/0 |
| r203_21 | 3938.97 | 3.00 | 3919.87 | 3.00 | -0.48 | 2/0/0 |
| r204_21 | 3738.86 | 3.00 | 3733.27 | 3.00 | -0.15 | 2/0/0 |
| r205_21 | 4006.68 | 3.00 | 3996.44 | 3.00 | -0.25 | 1/0/1 |
| r206_21 | 3957.92 | 3.00 | 3926.80 | 3.00 | -0.79 | 2/0/0 |
| r207_21 | 3830.70 | 3.00 | 3355.60 | 2.50 | -12.44 | 2/0/0 |
| r208_21 | 2780.77 | 2.00 | 2757.00 | 2.00 | -0.85 | 2/0/0 |
| r210_21 | 3872.50 | 3.00 | 3856.29 | 3.00 | -0.42 | 2/0/0 |
| r211_21 | 3790.86 | 3.00 | 3779.80 | 3.00 | -0.29 | 1/0/1 |
| rc101_21 | 17165.15 | 15.50 | 16696.72 | 15.00 | -2.64 | 1/0/1 |
| rc103_21 | 14313.78 | 13.00 | 13395.30 | 12.00 | -6.42 | 2/0/0 |
| rc104_21 | 12203.41 | 11.00 | 12193.03 | 11.00 | -0.09 | 2/0/0 |
| rc105_21 | 15460.64 | 14.00 | 15456.29 | 14.00 | -0.03 | 1/0/1 |
| rc107_21 | 13260.80 | 12.00 | 13263.80 | 12.00 | +0.02 | 0/1/1 |
| rc108_21 | 12217.79 | 11.00 | 12195.51 | 11.00 | -0.18 | 2/0/0 |
| rc201_21 | 5464.03 | 4.00 | 5449.61 | 4.00 | -0.26 | 1/0/1 |
| rc203_21 | 4097.51 | 3.00 | 4083.98 | 3.00 | -0.33 | 2/0/0 |
| rc204_21 | 3901.52 | 3.00 | 3910.68 | 3.00 | +0.23 | 0/0/2 |
| rc205_21 | 5164.83 | 4.00 | 5149.97 | 4.00 | -0.29 | 1/0/1 |
| rc207_21 | 4044.08 | 3.00 | 4025.69 | 3.00 | -0.45 | 1/0/1 |
| rc208_21 | 3877.30 | 3.00 | 3865.44 | 3.00 | -0.31 | 2/0/0 |

- Corridas pareadas: 88; factibles (juez oficial): hma_ld_llenar 88/88, final 88/88.
- Vehículos totales (pares factibles): hma_ld_llenar 706, final 688 (Δ -18).
- ΔTC medio por par: -1.904 % (mín -24.49 %, máx +0.43 %).
- final mejor / igual / peor: 61/13/14.
- Prueba de signos (bilateral, sin empates): p = 3.8e-08.
- Wilcoxon de rangos con signo (bilateral, diferencias de TC sin empates, n = 75): p = 5.4e-09.

Lectura:
- **88/88 factibles en ambos; −18 vehículos (706 → 688); ΔTC medio −1,90 % por par; 61 mejores, 13 iguales, 14 peores; signos p = 3,8·10⁻⁸; Wilcoxon p = 5,4·10⁻⁹.** El resultado de desarrollo se confirma, y con más fuerza estadística.
- Dónde gana: casi todo lo grande viene de ahorrar un vehículo, en r1 (r101, r103, r105, r109, r112, y una semilla de r104), r2 (r201 −17 %, una semilla de r207 −24 %), rc1 (rc103, una semilla de rc101) y c107. A igual K, el método gana distancia pequeña pero consistente en r2/rc2 (−0,2 a −0,9 %).
- Dónde pierde: 14 pares, todos pequeños (peor par +0,43 %); por instancia, rc204_21 (+0,23 %, 0/0/2), rc107_21 (0/1/1); c104, r104, r106, r110, r205, r211, rc101, rc105, rc201, rc205 y rc207 pierden en una semilla y ganan en la otra. En c2 empata.

Pequeñas reservadas (24 instancias, semilla 1, 105 s) frente a `hma_ld`: 24/24 factibles en ambos, mismos costos en las 24 (0/24/0; `resultados/reservado_peq_vs_hmald.md`).

## 6. Límites honestos
1. **La ablación no separa bien la eliminación de vehículos.** En desarrollo aporta −2 vehículos y −0,66 %, pero no es significativa (8/21/7). En el reservado solo se corrió el método final, no afín+pool, así que no se sabe cuánto de la ganancia del reservado se debe a la eliminación y cuánto a afín+pool. Lo más probable es que la mayor parte venga de afín+pool.
2. No se contaron los éxitos del operador de eliminación en el banco: el registro de HMA va a una carpeta temporal que se borra. En las pruebas sueltas tuvo éxito en 1 de 3–4 llamadas en rc106_21 y r102_21, y en 0 de 3 en rc206_21.
3. El reordenamiento intra-ruta consciente de la carga (b) no encontró ninguna mejora y se descartó. La evidencia es una sola corrida corta, no un experimento del banco.
4. Hubo un parámetro ajustado en desarrollo: el umbral de relanzamiento (≥ 10 s en vez de 25 s). Se fijó a priori por la razón de diseño (afín termina antes) y no se barrió. En el reservado no se tocó nada.
5. El presupuesto es de 120 s y no de los 630 s del artículo, y hay pocas semillas (3 en desarrollo, 2 en el reservado). No hay comparación con las soluciones publicadas de HMA (con β = 0,2 son en su mayoría infactibles).
6. La contabilidad del tiempo favorece a la referencia: el envoltorio cobra el tiempo de pared del SP y de los arranques de Python. Aun así, el método usa en promedio unos 9 s menos de CPU que la referencia.
7. En las pequeñas el método no aporta nada (empates). Además usa los 105 s completos por los reinicios, mientras que HMA-LD se detiene en pocos segundos.
8. Hubo dos reinicios del contenedor. Las corridas se reanudaron con `--reanudar` y una corrida interrumpida no deja fila (bench escribe al terminar), así que no hay corridas parciales en los CSV.
9. La novedad es de integración: resúmenes afines (Vidal et al. extendidos), pool + SP (Subramanian et al. 2013) y pila de expulsión (Nagata y Bräysy 2009).
