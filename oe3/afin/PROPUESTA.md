# PROPUESTA del agente `afin`: evaluación concatenable exacta con consumo según la carga

*(documento vivo; los números de la sección 6 son los del juez oficial)*

## 1. Idea en una frase
Con consumo e_ij(L) = h·d_ij·(1 + β(L/C − ρ)), la energía de cualquier segmento de ruta es una **función afín de su carga de entrada**, E(σ, L) = a_σ + b_σ·L, y se concatena en O(1) con **un solo escalar nuevo** (W = Σ d_k·Δ_k) además de los campos de carga y ventanas de Vidal et al.; sumado a una regla de recarga parcial que **demostramos exacta** ("lo obligatorio + todo lo que quepa gratis en la holgura"), toda ruta con estaciones fijas se evalúa en O(m) (m = estaciones) a partir de resúmenes de sus piernas, y la inserción **óptima** de 1–3 estaciones cuesta O(1) por candidato. Eso reemplaza la inserción heurística de estaciones de HMA (PSSI: algoritmo genético + inserción secuencial, O(n) por candidato), que con consumo según la carga es el cuello de botella.

## 2. Mecanismo (por qué funciona)

### 2.1 Resumen de segmento (exacto, O(1) por concatenación)
Para una secuencia σ (sin estaciones interiores) se guarda:

| campo | significado | concatenación σ = A ⊕ B por el arco (x, y) |
|---|---|---|
| d | distancia interna | d_A + d_xy + d_B |
| U | suma de entregas | U_A + U_B |
| Δ | variación neta de carga Σ(v − u) | Δ_A + Δ_B |
| H | máximo prefijo de la variación (≥ 0) | max(H_A, Δ_A + H_B) |
| **W** | Σ_arcos d_k·Δ_k (Δ_k = variación acumulada antes del arco k) | **W_A + W_B + Δ_A·(d_xy + d_B)** |
| D, TE, TL | duración y ventana de inicio (Vidal et al. 2013, sin *time warp*) | fórmulas de Vidal |

Si L es la carga al **llegar** al primer nodo de σ, la carga del arco k es L + Δ_k, y

  **E(σ, L) = h·[(1 − βρ)·d + (β/C)·(W + L·d)]**   (afín en L: b_σ = hβd/C ≥ 0).

Capacidad: la ruta sale con L0 = U (todas sus entregas) y es factible en carga si L0 + H ≤ C (equivale a C_E/C_H/C_L de HMA). Como la energía de cada arco es ≥ 0, la batería solo baja entre recargas: **una pierna sin estaciones es factible en batería si y solo si E(pierna, L_entrada) ≤ batería al salir**; el máximo de prefijos coincide con el total, así que no hace falta guardar una envolvente.

Lo nuevo respecto de los resúmenes de carga/ventanas: (i) la energía depende de la carga de entrada, que en SPD depende de **toda** la ruta (L0 = suma de entregas), y aun así basta con W para concatenar; (ii) no se requiere evaluar arco por arco.

### 2.2 Recarga parcial con ventanas: dónde se pierde O(1) y cómo se recupera
Con estaciones, la ruta es depósito ⊕ pierna_0 ⊕ f_1 ⊕ pierna_1 ⊕ … ⊕ f_m ⊕ pierna_m ⊕ depósito. Cada pierna_k (que empieza en la estación f_k, nodo sin ventana y servicio 0) tiene resumen O(1): energía E_k (afín en su carga de entrada L0 + Σ_{j<k} Δ_j) y (D_k, TE_k, TL_k). La decisión de **cuánto cargar en cada estación** no es local (interactúa con ventanas y esperas), así que no cabe en un resumen de tamaño constante para m arbitrario. Pero dada la secuencia, se resuelve **exactamente en O(m)** con la regla:

  q_k = max( need_k , min( libre_k , resto_k − b_k , Q − b_k ) )

donde b_k es la batería al llegar a f_k, need_k = max(0, E_k − b_k) (lo obligatorio para llegar a la próxima oportunidad de recarga), libre_k = max(0, (TE_k − t_k)/g) (lo que se carga sin retrasar el final de la pierna, porque en el formalismo de Vidal salir antes de TE solo convierte la espera en carga) y resto_k = Σ_{j≥k} E_j. Luego t ← max(t_k + g·q_k, TE_k) + D_k, exigiendo t_k + g·q_k ≤ TL_k.

**Por qué es exacta (esbozo de demostración).** Sea un plan factible cualquiera.
1. *Carga total mínima.* Si la batería final es > 0, se puede reducir la carga de la última estación con carga positiva sin violar nada (ninguna hora se atrasa y la batería posterior sigue ≥ 0). Hay un plan óptimo que no "sobra".
2. *Diferir la carga "pagada".* Una unidad que en f_k se carga más allá de libre_k retrasa en g la llegada a f_{k+1}; cargarla en f_{k+1} produce la misma hora de salida de f_{k+1} (o una anterior si allí hay holgura) y no arriesga TL_k. Si la batería lo permite (lo garantiza need_k), diferir domina débilmente.
3. *La carga gratis nunca daña.* Cargar hasta libre_k no cambia ninguna hora posterior y reduce las cargas futuras, que solo pueden adelantar horas.
Con 1–3, la regla anterior es factible si y solo si existe algún plan factible. HMA ya usa esta misma regla en `update_route_status` (con la holgura calculada recorriendo la pierna, O(n_k)); aquí se obtiene del resumen TE_k en O(1).

**Comprobación empírica contra el juez (programa lineal de `common/evrp.py`)** — ver sección 6.1: 0 discrepancias en 34 647 rutas (β = 0,1/0,2/0,3) y en 5 520 rutas de estrés con 1–3 estaciones insertadas y batería reducida, donde la política "cargar lo justo lo más tarde posible" pierde 34 de 394 rutas factibles.

### 2.3 Inserción óptima de estaciones en O(1) por candidato, y CLS sin copiar la solución
Para una lista de clientes [0, c1, …, cn, 0] se calculan prefijos P[p] y sufijos S[p] (O(n)) y los intermedios M[i][j] (O(n²), igual que la matriz `Attr` que HMA ya mantiene). Entonces:
- 0 estaciones: E(ruta, U) ≤ Q, O(1).
- 1 estación f en el arco p: piernas P[p] ⊕ f y f ⊕ S[p+1]: O(1) por par (p, f).
- k ≥ 2 estaciones: búsqueda en profundidad exacta por profundización (k = 2, 3, …, hasta 9). Desde una estación en el arco p, la siguiente se busca avanzando p' mientras la pierna f ⊕ M[p+1][p'] **quepa en Q y sea factible en ventanas** (ambas condiciones son monótonas al alargar la pierna, así que se corta en cuanto fallan), con cota por desvío (desvío acumulado + (estaciones que faltan)·desvío mínimo ≥ mejor ⇒ cortar). Cada ruta completa se evalúa en O(k). k = 2 siempre se explora (puede ser más barato que 1 estación); k ≥ 3 solo si no hay solución con menos, desde la cota inferior ⌈E/Q⌉ − 1, y con un tope de trabajo (10 000 candidatos por nivel).
Las estaciones candidatas por arco son las de HMA (`optimal_staion[a][b][0..sr−1]`). Sin tope, el resultado es la inserción de **mínimo desvío** entre esas candidatas (consecutivas en un mismo arco no se consideran; ver límites).

Además, en la búsqueda local conservadora (CLS) de HMA cada movimiento que mejora en VRPSPDTW se verifica en batería **copiando la solución completa**, aplicando el movimiento y corriendo PSSI. Con resúmenes basta armar las (hasta) dos listas de clientes nuevas desde las secuencias del movimiento y llamar a la inserción exacta: no se copia la solución (`--afin 2`).
## 3. Qué la hace nueva
- **HMA (Zheng, Liu y Ong 2025):** su evaluación O(1) (`Attr`/`connect`) cubre solo ventanas, capacidad y distancia; la batería se resuelve después con evaluación completa O(n) y una inserción heurística de estaciones (PSSI). Aquí la batería —con consumo según la carga y recarga parcial— entra en los resúmenes, y la inserción de estaciones pasa a ser exacta y O(1) por candidato.
- **Vidal et al. (2013, 2014):** resúmenes concatenables para ventanas, duración, capacidad (y, en 2014, un marco general de "recursos" concatenables). No tratan energía dependiente de la carga en SPD, ni recarga parcial con ventanas. La aportación es mostrar que la energía afín en la carga cabe con un escalar (W) y que la recarga parcial se resuelve exactamente con los TE de Vidal de cada pierna.
- **Zachariadis, Tarantilis y Kiranoudis (2015, LDVRP y su extensión con recogida y entrega):** usan costos dependientes de la carga (costo = distancia × carga) con evaluación de movimientos eficiente vía cantidades acumuladas, pero el costo es objetivo, sin batería, sin estaciones ni recarga. Aquí la dependencia de la carga es una **restricción** de batería que interactúa con la recarga parcial y las ventanas.
- **Rastani y Çatay (2023):** EVRP con consumo según la carga y recarga parcial resueltos con evaluación arco a arco (ALNS); no proponen resúmenes concatenables.
- La demostración de exactitud de la regla "obligatoria + holgura" frente al PL del juez para secuencia fija con ventanas no la encontramos explícita en la literatura citada (HMA la usa como heurística de cálculo de carga). *Advertencia: no se revisó exhaustivamente la literatura de "resource extension functions" para EVRPTW con recarga parcial (p. ej. Desaulniers et al. 2016), donde hay resultados afines para etiquetado; la novedad debe acotarse a la formulación concatenable y a su uso en búsqueda local con SPD y consumo según la carga.*

## 4. Por qué sería memorable
El mensaje es simple y contraintuitivo: **pasar a consumo según la carga no obliga a abandonar la evaluación O(1)**. La energía sigue siendo concatenable (un escalar extra) y la recarga parcial con ventanas se decide exactamente con los resúmenes de Vidal. Con ello, el componente más caro de HMA con consumo según la carga (la inserción de estaciones) se vuelve exacto y varias veces más rápido, sin tocar el resto del algoritmo.

## 5. Implementación
- `resumen.py`: prototipo en Python (resúmenes, concatenación general con estaciones, evaluación O(m)).
- `prueba_resumen.py`, `prueba_estres.py`: pruebas aleatorias contra `eval_route` del juez.
- `cpp/afin.h`, `cpp/afin.cpp`: implementación C++ (resúmenes con hasta 8 piernas, evaluación O(m), evaluación completa O(n) estilo HMA); `cpp/bench_mov.cpp`: aceleración en relocate/swap/2-opt*; `cpp/check_routes.cpp` + `prueba_cpp.py`: validación del C++ contra el juez.
- `hma-afin/`: copia de HMA-LD (agente `base`) con `src/afin_hma.cpp` (inserción exacta de estaciones con resúmenes). Cambios en HMA-LD: (1) al comienzo de `parallel_sequential_station_insertion` (PSSI) se llama a la inserción exacta; (2) en `eval_move`, rama CLS, la evaluación de batería se hace con la inserción exacta sin copiar la solución. Opciones: `--afin 0` (= HMA-LD; salida idéntica a la de `base` comprobada en rc108C15), `--afin 1` (solo (1), con PSSI original como respaldo si no hay solución), `--afin 2` (método propuesto: (1) sin respaldo + (2)); `--afin_kmax` (máx. estaciones, 9), `--afin_max3` (tope de trabajo para k ≥ 3, 10 000). El resto de HMA (operadores, ALS, población, criterios de parada, parámetros) no se cambió.
  Compilar: `cd hma-afin && g++ -std=c++11 -O3 -o bin/evrp-tw-spd src/*.cpp`. (`bin/evrp-afin-v2` = versión anterior, ≤ 3 estaciones.)
- `metodos/hma_afin.py`: envoltorio de `base/metodos/hma.py` con `--afin` (y `--g1`). `metodos/hma_afin_llenar.py`: copia del envoltorio actual de `base` (con `--llenar`, multiarranque hasta agotar 120 s de CPU) que además pasa `--afin`; es el mismo protocolo que la referencia `hma_ld_llenar` de `base`.
- `comparar.py`: tabla de comparación por instancia y semilla entre dos `corridas.csv` de `bench.py`.

## 6. Resultados medidos
Todo lo de abajo es con β = 0,2 y ρ = 0, y la factibilidad siempre la decide el **juez oficial** `common/evrp.py: check_solution(..., use_reported=False)`.

### 6.1 Exactitud de la evaluación (prototipo Python vs. juez)
`prueba_resumen.py` toma las rutas de las 92 soluciones publicadas de HMA en las instancias akb y les aplica mutaciones aleatorias (intercambio, reubicación, inversión, quitar/insertar estación, 2-opt* entre rutas, insertar un cliente de otra ruta), y compara el veredicto del resumen con `eval_route` (programa lineal exacto del juez):

| β | rutas | factibles (juez) | coinciden | falsos positivos | falsos negativos | error máx. energía afín |
|---|---|---|---|---|---|---|
| 0,1 | 11 549 | 3 399 | 11 549 | 0 | 0 | 2,3·10⁻¹³ |
| 0,2 | 11 549 | 2 841 | 11 549 | 0 | 0 | 1,7·10⁻¹³ |
| 0,3 | 11 549 | 2 528 | 11 549 | 0 | 0 | 2,3·10⁻¹³ |

Además, construir el resumen con un **árbol de concatenación aleatorio** da el mismo veredicto y la misma distancia en las 34 647 rutas (0 diferencias): la concatenación es asociativa, como debe ser para usarla en movimientos.

`prueba_estres.py` fuerza el caso difícil: inserta 1–3 estaciones cercanas al azar y reduce la batería (Q × U(0,6; 1,0)) para que haya recarga en varias estaciones. Sobre 5 520 rutas (4 684 con ≥ 2 estaciones), 394 factibles según el juez: el resumen **coincide en 5 520/5 520**, mientras que la política "cargar lo justo, lo más tarde posible" (sin aprovechar la holgura) solo reconoce 360 y **pierde 34 de las 394** rutas factibles. Es decir, la parte "gratis en la holgura" de la regla no es un detalle: sin ella se descartan rutas que sí son factibles.

La implementación C++ (`cpp/`) se validó igual contra el juez: 7 869 rutas (publicadas + mutadas), coincidencia 7 869/7 869 tanto para la evaluación completa O(n) como para la de resúmenes.

### 6.2 Aceleración de la evaluación de movimientos (C++, `cpp/bench_mov.cpp`)
Para cada una de las 56 instancias akb de 100 clientes, se enumeran todos los movimientos entre pares de rutas de la solución publicada y se evalúa cada uno de las dos formas: (a) evaluación completa (armar las dos listas de nodos y simular hacia adelante, estilo HMA, con el mismo cálculo de recarga) y (b) concatenación de resúmenes de prefijo/sufijo. Las dos pasadas dan **el mismo veredicto en los 1 068 841 movimientos** (0 discrepancias):

| movimiento | movimientos | ns/mov. completa | ns/mov. resúmenes | aceleración |
|---|---|---|---|---|
| relocate | 529 248 | 49,6 | 9,5 | **5,2×** |
| swap | 222 793 | 120,6 | 33,0 | **3,7×** |
| 2-opt* | 316 800 | 264,4 | 30,0 | **8,8×** |

(Los resúmenes de prefijo/sufijo se construyen una vez por ruta, O(n); el costo amortizado ya está incluido en la enumeración completa de vecindarios, que es como se usa en la búsqueda local.)

### 6.3 Dentro de HMA: conjunto de desarrollo, protocolo estándar (105 s / 120 s, 3 semillas)
**HMA-LD-afín** (`--afin 2`, versión final con margen `TOL`) frente a la referencia **HMA-LD** del agente `base` (`base/resultados/hma_ld`): mismas 24 instancias, semillas 1–3, mismos parámetros y presupuesto. Datos: `resultados/hma_ld_afin_tol/corridas.csv`; tabla: `resultados/tabla_estandar_final.md`.

| instancia | fact afin | fact hmald | TC medio afin | TC medio hmald | mejor afin | mejor hmald | t medio afin (s) | t medio hmald (s) |
|---|---|---|---|---|---|---|---|---|
| c101C5 | 3/3 | 3/3 | 2257.75 | 2257.75 | 2257.75 | 2257.75 | 0.4 | 0.5 |
| c104C10 | 3/3 | 3/3 | 2273.93 | 2273.93 | 2273.93 | 2273.93 | 1.1 | 1.2 |
| c103C15 | 3/3 | 3/3 | 3374.43 | 3374.43 | 3374.43 | 3374.43 | 7.5 | 5.9 |
| c202C15 | 3/3 | 3/3 | 2383.62 | 2383.62 | 2383.62 | 2383.62 | 0.5 | 0.7 |
| r104C5 | 3/3 | 3/3 | 2136.69 | 2136.69 | 2136.69 | 2136.69 | 0.4 | 0.7 |
| r102C10 | 3/3 | 3/3 | 3285.18 | 3285.18 | 3285.18 | 3285.18 | 0.9 | 1.4 |
| r201C10 | 3/3 | 3/3 | 1264.26 | 1265.05 | 1264.26 | 1265.05 | 1.4 | 2.6 |
| r105C15 | 3/3 | 3/3 | 4352.72 | 4352.72 | 4352.72 | 4352.72 | 1.6 | 0.9 |
| rc105C5 | 3/3 | 3/3 | 2241.30 | 2241.30 | 2241.30 | 2241.30 | 0.4 | 1.2 |
| rc204C5 | 3/3 | 3/3 | 1176.39 | 1176.39 | 1176.39 | 1176.39 | 0.1 | 0.1 |
| rc201C10 | 3/3 | 3/3 | 2323.50 | 2323.50 | 2323.50 | 2323.50 | 0.6 | 1.0 |
| rc108C15 | 3/3 | 3/3 | 3370.37 | 3370.37 | 3370.37 | 3370.37 | 0.7 | 1.0 |
| c101_21 | 3/3 | 3/3 | 13047.08 | 13047.08 | 13046.30 | 13046.30 | 5.6 | 8.5 |
| c106_21 | 3/3 | 3/3 | 12026.81 | 12026.81 | 12022.89 | 12022.89 | 25.7 | 52.8 |
| c202_21 | 3/3 | 3/3 | 4641.07 | 4641.07 | 4641.07 | 4641.07 | 11.3 | 27.7 |
| c206_21 | 3/3 | 3/3 | 4639.88 | 4639.88 | 4639.88 | 4639.88 | 16.2 | 29.9 |
| r102_21 | 3/3 | 3/3 | 17435.86 | 17763.91 | 17435.34 | 17432.56 | 20.3 | 38.1 |
| r108_21 | 3/3 | 3/3 | 12045.04 | 12039.08 | 12039.44 | 12033.90 | 123.4 | 123.3 |
| r202_21 | 3/3 | 3/3 | 4081.64 | 4081.37 | 4070.16 | 4062.00 | 36.3 | 120.6 |
| r209_21 | 3/3 | 3/3 | 3885.32 | 3893.36 | 3877.67 | 3883.65 | 76.7 | 123.6 |
| rc102_21 | 3/3 | 3/3 | 15865.28 | 15858.57 | 15527.74 | 15528.69 | 66.5 | 89.7 |
| rc106_21 | 3/3 | 3/3 | 14410.61 | 15094.02 | 14406.46 | 14405.27 | 65.1 | 87.3 |
| rc202_21 | 3/3 | 3/3 | 5244.48 | 5248.52 | 5240.98 | 5246.67 | 38.7 | 91.7 |
| rc206_21 | 3/3 | 3/3 | 4231.04 | 4536.75 | 4220.19 | 4236.24 | 75.5 | 108.7 |

Por corrida (misma instancia y semilla): afin mejor en 15, hmald mejor en 13, empates 44.
Diferencia relativa media de TC (afin − hmald)/hmald: -0.515 %  (mín -17.235 %, máx +6.454 %)
Tiempo medio total: afin 576.8 s, hmald 918.9 s (razón 1.59)


Resumen:
- Factibles según el juez: **72/72** en ambos métodos.
- Pequeñas (12 instancias): mismos costos en 11; en r201C10 afín obtiene **1 264,26** en las 3 semillas, frente a 1 265,05 de HMA-LD (la ruta necesita 6 estaciones y la inserción exacta encuentra una más corta que PSSI).
- 100 clientes, **tiempo de CPU medio por corrida: 46,2 s (afín) frente a 73,9 s (HMA-LD)**, con el mismo criterio de parada de HMA (20 generaciones sin mejora): el método afín llega al punto de parada en un 37 % menos de tiempo. En c202_21, r202_21 y rc202_21 la reducción es de 2,4× a 3,3×.
- Costo: por corrida, afín mejor en 15, HMA-LD mejor en 13, 44 empates; diferencia relativa media **−0,52 %** (de −17,2 % a +6,5 %). Las grandes diferencias a favor (rc106_21 y rc206_21: −4,5 % y −6,7 % en el promedio, y r102_21) vienen de corridas en que HMA-LD terminó con un vehículo más. Con 3 semillas eso no es estadísticamente distinguible de la variabilidad entre semillas.

**Advertencia de protocolo.** Con la parada por 20 generaciones sin mejora ninguno de los dos consume el presupuesto completo, así que esta tabla mide *tiempo hasta el mismo punto de parada*, no *calidad a igual tiempo*. Para eso está la sección 6.4.

### 6.4 Dentro de HMA: presupuesto igual (multiarranque, 120 s de CPU) — la comparación principal
Ambos métodos usan el mismo protocolo `--llenar` del agente `base`: HMA se reinicia con semillas semilla·1000 + k hasta agotar 120 s de CPU y se devuelve la mejor solución aceptada por el juez. Referencia: `base/resultados/hma_ld_llenar`; afín: `resultados/hma_ld_afin_llenar` (`--afin 2`, versión final). 12 instancias de 100 clientes del conjunto de desarrollo, semillas 1–3. Tabla: `resultados/tabla_llenar.md`.

| instancia | fact afin | fact hmald | TC medio afin | TC medio hmald | mejor afin | mejor hmald | t medio afin (s) | t medio hmald (s) |
|---|---|---|---|---|---|---|---|---|
| c101_21 | 3/3 | 3/3 | 13046.30 | 13046.30 | 13046.30 | 13046.30 | 119.4 | 121.2 |
| c106_21 | 3/3 | 3/3 | 12021.37 | 12024.03 | 12018.34 | 12022.89 | 121.8 | 122.6 |
| c202_21 | 3/3 | 3/3 | 4641.07 | 4641.07 | 4641.07 | 4641.07 | 121.6 | 128.9 |
| c206_21 | 3/3 | 3/3 | 4639.88 | 4639.88 | 4639.88 | 4639.88 | 121.9 | 121.2 |
| r102_21 | 3/3 | 3/3 | 17434.80 | 17429.83 | 17434.54 | 17428.36 | 123.0 | 122.7 |
| r108_21 | 3/3 | 3/3 | 12041.01 | 12033.77 | 12028.79 | 12026.34 | 122.5 | 123.6 |
| r202_21 | 3/3 | 3/3 | 4051.47 | 4073.16 | 4051.47 | 4054.15 | 122.0 | 126.3 |
| r209_21 | 3/3 | 3/3 | 3888.07 | 3893.08 | 3879.78 | 3882.33 | 123.6 | 133.0 |
| rc102_21 | 3/3 | 3/3 | 16193.12 | 15872.40 | 15527.74 | 15535.30 | 121.9 | 123.0 |
| rc106_21 | 3/3 | 3/3 | 14415.58 | 15423.75 | 14406.31 | 15419.75 | 122.3 | 122.6 |
| rc202_21 | 3/3 | 3/3 | 5241.50 | 5250.07 | 5240.98 | 5247.31 | 121.7 | 123.2 |
| rc206_21 | 3/3 | 3/3 | 4236.00 | 4850.37 | 4211.14 | 4295.71 | 121.6 | 124.1 |

Por corrida (misma instancia y semilla): afin mejor en 17, hmald mejor en 8, empates 11.
Diferencia relativa media de TC (afin − hmald)/hmald: -1.443 %  (mín -17.326 %, máx +6.387 %)
Tiempo medio total: afin 1463.3 s, hmald 1492.4 s (razón 1.02)


Resumen:
- Factibles según el juez: **36/36** en ambos.
- Por corrida (misma instancia y semilla): **afín mejor en 17, HMA-LD mejor en 8**, 11 empates. Diferencia relativa media de TC: **−1,44 %** (de −17,3 % a +6,4 %).
- Vehículos: afín usa **menos vehículos que HMA-LD en 5 corridas y más en 1** (K medio 8,22 frente a 8,33). Ahí está casi toda la ganancia, porque μ1 = 1000: rc106_21 (14 415,6 frente a 15 423,8, un vehículo menos en las 3 semillas) y rc206_21 (4 236,0 frente a 4 850,4). La única corrida con un vehículo más es de rc102_21.
- En distancia, a igual número de vehículos, las diferencias son pequeñas y en ambos sentidos: afín es mejor en r202_21, r209_21, rc202_21 y c106_21, y peor en r102_21 y r108_21 (≤ 0,06 %).
- Prueba de signo sobre las 25 corridas no empatadas (17 contra 8): p ≈ 0,11 (bilateral). **La tendencia favorece a afín, pero con 3 semillas y 12 instancias no es significativa al 5 %.**

Lectura: a igual presupuesto, la evaluación concatenable permite más reinicios o más generaciones en el mismo tiempo. El efecto visible es que **encuentra con más frecuencia soluciones con un vehículo menos**, en instancias con ventanas holgadas (rc2, r2) y en rc106_21. Esto es coherente con la hipótesis, pero falta confirmarlo en el conjunto reservado y con más semillas.

## 7. Límites honestos
1. **La ganancia medida es sobre todo de tiempo, no de costo.** Con el protocolo estándar la diferencia media de TC es −0,52 % y el reparto por corrida es 15 a 13: eso es ruido. Lo que sí es claro y repetible es el tiempo de CPU hasta el mismo criterio de parada en las instancias de 100 clientes (46,2 s vs. 73,9 s). La tesis puede sostener "misma calidad en ~60 % del tiempo". A igual tiempo (sección 6.4) la ventaja es −1,44 % en TC y 17 contra 8 corridas, explicada casi entera por 5 corridas con un vehículo menos: es prometedora pero **no significativa** (prueba de signo p ≈ 0,11) y no se ha medido en el conjunto reservado. No es todavía la "mejora notoria" que pide la tesis.
2. **La recarga parcial no cabe en un resumen de tamaño constante.** La parte exacta y O(1) es la energía, la carga y las ventanas; con m estaciones la decisión de recarga cuesta O(m) a partir de los resúmenes de las piernas (y m es pequeño en estas instancias: casi siempre 1–3). No hay un "resumen O(1) de toda la ruta con estaciones".
3. **La exactitud de la regla de recarga está demostrada de forma informal** (argumento de intercambio, sección 2.2) y verificada empíricamente contra el programa lineal del juez en ~40 000 rutas, no con una demostración formal revisada. Si se escribe en la tesis, debe presentarse como proposición con su demostración detallada.
4. **El espacio de inserción de estaciones es el de HMA, no todo el espacio.** Solo se consideran las estaciones preseleccionadas por arco (`optimal_staion[a][b][0..sr−1]`, con sr = 50 % de las estaciones en las instancias de 100 clientes) y a lo más una estación por arco; no se consideran dos estaciones consecutivas en el mismo arco (HMA sí puede generarlas mediante su paso de refinamiento). Por eso "inserción exacta" significa *óptima dentro de ese conjunto de candidatos*, y es la razón de que a veces la trayectoria de búsqueda sea distinta (y peor) que la de HMA-LD: ver rc102_21.
5. **En las rutas donde no hay solución con ≤ 9 estaciones (o se agota el tope de trabajo para k ≥ 3), `--afin 2` declara el movimiento infactible**, mientras que HMA-LD intentaría con PSSI. En r202_21, con el tope quitado, afín resuelve 2 876/2 876 llamadas; con el tope por omisión se rechazan algunas. `--afin 1` existe precisamente para usar PSSI como respaldo, pero entonces se pierde parte de la ventaja de tiempo.
6. **La versión C++ dentro de HMA acepta con un margen de 10⁻⁴** (`TOL`) para que la comprobación final de HMA, que simula hacia adelante con otra aritmética, no rechace una ruta que el resumen aceptó al límite. Esto la hace ligeramente conservadora: puede rechazar rutas factibles con holgura menor que 10⁻⁴. En la versión sin margen hubo una corrida (rc206_21, semilla 2) en que HMA abortó al escribir la solución por una ventana cumplida con igualdad exacta (71/72 factibles); con el margen, 72/72.
7. **Solo un conjunto de desarrollo, 3 semillas, 120 s.** El artículo de HMA usa 630 s y 10 corridas; las 68 instancias reservadas no se tocaron. Las diferencias por instancia (hasta ±6 %) son del orden de la variabilidad entre semillas, así que el conjunto es demasiado chico para afirmar superioridad en costo.
8. **No se exploró el otro uso natural de los resúmenes**: evaluar los movimientos *con batería* dentro de la búsqueda local agresiva (ALS) y no solo al verificar un movimiento que ya mejora en VRPSPDTW. Ahí podría estar la ganancia de calidad, porque HMA busca en un vecindario relajado (sin batería) y repara después. Es el trabajo futuro más prometedor y también la mayor debilidad de lo entregado: la idea se usó para *acelerar* la verificación, no para *cambiar* el vecindario.
9. La "novedad" frente a la literatura de etiquetado (funciones de extensión de recursos para EVRPTW con recarga parcial) no se verificó con búsqueda bibliográfica, solo contra los cuatro trabajos citados.
