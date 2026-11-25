# PROPUESTA del agente `recarga`: decisión exacta de estaciones y recarga para una secuencia fija

*(Estado: terminado. Todas las cifras salen del juez oficial `common/evrp.py`, con β = 0,2, ρ = 0 y `use_reported=False`.)*

## 1. Idea en una frase
Para una secuencia de clientes fija, el conjunto de estados (instante listo, batería) que puede alcanzar un vehículo eléctrico con ventanas de tiempo, recarga parcial lineal y consumo según la carga se describe **exactamente con tres números** (a, b, m). Eso permite (i) decidir la factibilidad de recarga de una ruta en **O(n) sin programa lineal** y (ii) elegir estaciones y cantidades de forma **exacta** con un algoritmo de etiquetas con dominancia exacta, que sustituye a la regla de recarga y a la inserción heurística de estaciones de HMA.

## 2. Subproblema y mecanismo
**Subproblema (FRVCP-TW-LD).** Datos: la secuencia 0 = c₀, c₁, …, c_m, c_{m+1} = 0. Hay que decidir qué estaciones visitar en cada tramo (c_k, c_{k+1}), entre 0 y 2 por tramo, y cuánta energía q cargar en cada una, de modo que la distancia sea mínima y se cumplan: batería en [0, Q], inicio de atención dentro de [e_i, l_i], regreso antes de l₀, tiempo de recarga g·q y energía de arco h·d·(1 + β(L/C − ρ)).

Las estaciones no cambian la carga. Por eso la carga L_k es constante en todo el tramo k, y el consumo dentro del tramo es proporcional a la distancia con un factor φ_k = h(1 + β(L_k/C − ρ)) **conocido de antemano**. El consumo según la carga solo cambia los coeficientes, no la estructura del problema.

**Función de compromiso de 3 parámetros.** Sea F(A) la batería máxima con que el vehículo puede estar listo en el instante A. Entonces F(A) = min(m, b + (A − a)/g) para A ≥ a, donde:
- a es el instante más temprano;
- b es la batería en a, cargando lo mínimo;
- m es la batería máxima a la que se llega postergando la salida.

La familia es cerrada bajo las cuatro operaciones del problema:
- **arco (t, e):** si m < e, no hay plan factible; a ← a + t + g·max(0, e − b); b ← max(b, e) − e; m ← m − e;
- **cliente [e_i, l_i], s_i:** si a > l_i, no hay plan factible; m ← min(m, b + (l_i − a)/g); si a < e_i, entonces b ← min(m, b + (e_i − a)/g) y a ← e_i (durante la espera se recarga «gratis»); al final, a ← a + s_i;
- **estación:** m ← Q. F tiene pendiente ≤ 1/g y recargar es la forma más rápida de ganar batería, así que llegar antes y cargar más domina a llegar después;
- **depósito final:** es factible si a ≤ l₀.

Por eso la factibilidad con estaciones fijas cuesta O(n). Para elegir las estaciones se usa un algoritmo de etiquetas sobre la secuencia. Cada etiqueta es (dist, a, b, m), y una etiqueta domina a otra si dist ≤ dist′, a ≤ a′, m ≥ m′ y F(a′) ≥ b′. Esta condición equivale a F ≥ F′ punto a punto, así que la dominancia es exacta. En cada tramo se prueban todas las estaciones solas y los pares formados con las 6 mejor ubicadas (en C++; en Python, todos los pares). La complejidad es O(m · (S + p²) · Λ²), con Λ el número de etiquetas no dominadas por tramo, que en la práctica es pequeño.

**Por qué debería funcionar (hipótesis inicial).** La regla de HMA carga lo justo para llegar a la próxima estación más la holgura de espera hacia adelante. Esa regla rechaza rutas factibles (según CONTEXTO, 42 de las 172 soluciones publicadas con «cargar lo más tarde posible»), y la inserción de estaciones es voraz. Una decisión exacta debería aceptar más vecinos y abaratar los aceptados.

## 3. Qué la hace nueva
- **Frente a HMA (Zheng, Liu y Ong, 2025).** HMA fija la cantidad con una regla (q_{f,0} + holgura) y elige estaciones con una inserción voraz por ranking (SSI) o con un AG de posiciones (PSI). Aquí la cantidad y las estaciones son óptimas para la secuencia, hasta 2 estaciones por tramo. Con la evaluación de la función de compromiso, la factibilidad es exacta, no una condición suficiente.
- **Frente a Keskin y Çatay (2016).** Su recarga parcial se decide con reglas dentro de una ALNS, y la optimización exacta de la recarga se hace aparte con un modelo matemático. Aquí es un procedimiento combinatorio exacto de tiempo casi lineal, que se puede llamar millones de veces dentro de la búsqueda.
- **Frente a Rastani y Çatay (2023), consumo según la carga con «reparación óptima».** Resuelven la reparación con un solver. Aquí se aprovecha que la carga es constante por tramo, y el subproblema con consumo según la carga se resuelve con la misma maquinaria que el de consumo constante, sin PL ni MIP.
- **Frente a Montoya et al. (2017) y Froger et al. (2019), FRVCP con recarga no lineal.** Ellos no tienen ventanas de tiempo en el FRVCP; Montoya lo resuelve con un MILP y Froger con etiquetas. Aquí hay ventanas, y la observación clave es que con recarga **lineal** la función de compromiso se reduce a 3 números.
- **Relación honesta.** La idea de funciones de compromiso tiempo-batería en algoritmos de etiquetas viene de los métodos exactos de ramificación y precios (Desaulniers et al., 2016). Lo nuevo aquí es: el resultado de cierre en 3 parámetros para TW + recarga parcial lineal + consumo según la carga en recogida y entrega simultáneas, y su uso como evaluador y reparador dentro de HMA.

## 4. Implementación
- `frvcp.py`: evaluador O(n) `feasible_fixed` y algoritmo de etiquetas `frvcp`, en Python.
- `test_fixed.py`: evaluador O(n) contra el PL del juez.
- `test_bruteforce.py`: etiquetas contra fuerza bruta.
- `efecto_aislado.py` y `resumen_aislado.py`: paso 2, sobre las soluciones publicadas.
- `hma-rx/`: copia de HMA-LD (base) con `src/frvcp.{h,cpp}` y la opción `--rx`:
  - `--rx 0` reproduce HMA-LD **bit a bit**: se verificó en rc108C15, con archivo de solución idéntico;
  - `--rx 1`: cuando la regla de HMA (`update_route_status`) declara una ruta infactible por ventanas o batería, se re-decide con la evaluación exacta O(n). La comprobación final (`Solution::check`) acepta las rutas que el plan exacto valida;
  - `--rx 2`: lo anterior, más el algoritmo de etiquetas, que reemplaza a PSI/SSI en `parallel_sequential_station_insertion` (quita las estaciones y las re-decide) y a la inserción voraz en `sequential_station_insertion` (mantiene las existentes e inserta las óptimas). También hay un pulido final, que re-decide las estaciones de cada ruta de la mejor solución. Si la DP no encuentra plan, se usa como respaldo el procedimiento original de HMA.
- Envoltorio `metodos/hma_rx.py`: copia de `base/metodos/hma.py` con `--rx`. Las corridas se hicieron con `base/bench.py`.

## 5. Resultados medidos

### 5.1 Corrección
- **Evaluador O(n) contra el PL del juez.** Se probaron 7566 casos: rutas publicadas akb y perturbaciones (quitar, insertar o cambiar estación), con β ∈ {0; 0,2; 0,3}. Coincide en **7566/7566**. Tiempo: 0,13 s frente a 16,7 s del PL, unas **127 veces** más rápido en Python.
- **Etiquetas contra fuerza bruta.** Se generaron 800 casos aleatorios: secuencias de 2 a 4 clientes de las instancias pequeñas, con batería, capacidad y g perturbadas. La fuerza bruta recorre todas las asignaciones de estaciones por tramo en orden de distancia, y las primeras 400 se evalúan con el PL. Coincide en **800/800**: 79 óptimos con estaciones y el resto infactibles en ambos.

### 5.2 Efecto aislado sobre las soluciones publicadas de HMA (β = 0,2)
Se quitaron las estaciones de cada ruta y se re-decidieron con las etiquetas exactas, con la misma secuencia y también con la secuencia inversa.

| | pequeñas (36) | 100 clientes (56) |
|---|---|---|
| publicada tal cual | 25 factibles | 4 factibles |
| reparación mínima (`consumo_carga.py`) | 30 factibles (6 rutas sin reparar) | 23 factibles (89 rutas) |
| etiquetas exactas | 30 factibles (6 rutas sin plan) | 23 factibles (87 rutas sin plan) |
| etiquetas exactas, secuencia o inversa | 30 | 23 |
| distancia extra frente a la publicada (en las que ambas resuelven) | reparación +69,36 / etiquetas +68,52 | reparación +98,83 / etiquetas +83,03 (más barata en 13 de 23) |

**Lectura.** Re-decidir las estaciones de forma exacta **no recupera ninguna solución más** que la reparación mínima: solo recupera 2 rutas más y reduce un 16 % la distancia extra. Las etiquetas *demuestran* que las 33 soluciones de 100 clientes que siguen infactibles lo son por la secuencia de clientes: ninguna elección de estaciones (≤ 2 por tramo) ni de cantidades las hace factibles. Esto descarta la hipótesis de que las soluciones de HMA se pierden por decidir mal la recarga.

### 5.3 Dentro de la búsqueda: HMA-RX (`--rx 2`) frente a HMA-LD
Conjunto de desarrollo (12 pequeñas y 12 de 100 clientes), semillas 1, 2 y 3. Presupuesto: 105 s para las pequeñas y 120 s para las de 100 clientes, el mismo de la referencia, con una corrida a la vez y el juez oficial. Referencia: `base/resultados/hma_ld/corridas.csv`. HMA-RX: `resultados/hma_rx2/corridas.csv`. La tabla por instancia está en `tabla_rx2_vs_hmald.md` y se genera con `comparar.py`.

| grupo | método | factibles | K medio | TC medio | tiempo medio |
|---|---|---|---|---|---|
| pequeñas | HMA-LD | 36/36 | 2,250 | 2536,74 | 1,4 s |
| pequeñas | **HMA-RX** | 36/36 | 2,250 | 2536,64 | 1,3 s |
| 100 clientes | HMA-LD | 36/36 | 8,306 | 9405,87 | 75,2 s |
| 100 clientes | **HMA-RX** | 36/36 | **8,222** | **9323,59** | 75,1 s |

Comparación por pares (misma instancia y semilla):
- **Pequeñas.** ΔTC medio −0,008 %; HMA-RX es mejor en 3 pares y peor en 0; K total 81 → 81. La única mejora visible es r201C10, de 1265,05 a 1263,76.
- **100 clientes.** ΔTC medio **−0,84 %**; HMA-RX es mejor en 17 pares y peor en 11; K total **299 → 296**. Los vehículos ahorrados están en r102_21, rc106_21 y rc206_21: son semillas en que HMA-LD usó un vehículo más.
- **Semillas 4 y 5 (solo 100 clientes, mismas condiciones).** ΔTC medio −1,27 %; mejor en 10 pares y peor en 8; K total 200 → 197 (rc102, rc106, rc206).
- **Las 60 semillas-instancia de 100 clientes juntas.** K total **499 → 493**, ΔTC medio ≈ −1,0 %, mejor en 27 pares y peor en 19. Una prueba de signos con 27 contra 19 **no es significativa** (p ≈ 0,3). La mejora media viene casi solo de evitar, en algunas semillas, un vehículo extra en instancias rc. En distancia, a igual K, hay empate.
- **Variante `--rx 1`** (solo la evaluación exacta O(n), sin etiquetas; 100 clientes, semillas 1–3): ΔTC −0,25 %, mejor en 10 pares y peor en 18, K 299 → 299. Lo que aporta algo es la elección exacta de estaciones (etiquetas), no la corrección de la cantidad de recarga.
- **Frente a HMA original + reparación mínima** (`base/resultados/hma_orig_reparado`): HMA-RX es factible en 36/36 + 36/36, contra 23/36 y 18/36. Esto se debe sobre todo a que la búsqueda considera β, algo que HMA-LD ya hace.

## 6. Límites honestos
- **La mejora no es memorable.** Frente a HMA-LD con el mismo presupuesto, HMA-RX logra −0,8 % a −1,3 % de TC medio en 100 clientes (−6 vehículos en 60 corridas), pero sin significancia estadística, y empata en las pequeñas. Como herramienta, vale más como evaluador exacto y certificado de infactibilidad que como fuente de mejora del costo.
- En el benchmark akb, la decisión de recarga **no es el cuello de botella**. La regla de HMA (con la corrección de base para el consumo según la carga) ya es casi óptima en las rutas que la búsqueda genera. La pérdida de factibilidad con β > 0 está en las secuencias, es decir, en el ruteo, no en la recarga.
- El algoritmo de etiquetas limita a 2 estaciones por tramo, y en C++ los pares salen de las 6 estaciones mejor ubicadas. Es exacto dentro de ese espacio, que cubre todo lo que generan HMA y las soluciones publicadas.
- La novedad teórica es moderada: la función de compromiso existe en la literatura de métodos exactos. Lo propio es la reducción a 3 parámetros para esta variante y la verificación.
