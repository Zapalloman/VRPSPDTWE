# Banco de pruebas común del OE3 (agente `base`)

Estado: **HMA-LD y `bench.py` funcionan y están verificados. Las dos referencias de desarrollo (3 semillas) terminaron** (sección 4). La variante multiarranque de HMA-LD (`hma_ld_llenar`, 100 clientes) se completó después (sección 4b).

## 1. HMA-LD: HMA con consumo según la carga

Carpeta: `/home/user/oe3/base/hma-ld/` (copia de `common/hma`, revisión 0ebbcaa). Diferencias respecto del original: `/home/user/oe3/base/hma-ld.diff`.

### Compilar
```bash
cd /home/user/oe3/base/hma-ld
g++ -std=c++11 -O3 -o bin/evrp-tw-spd src/*.cpp          # HMA-LD
# bin/evrp-tw-spd-orig es el HMA original compilado sin cambios (common/hma/src)
```

### Llamar
Igual que HMA (parámetros del README de HMA), más dos opciones nuevas:
- `--beta B` (por defecto **0.2**) y `--rho R` (por defecto **0**): energía del arco e_ij(L) = h·d_ij·(1 + β·(L/C − ρ)).
- `--beta 0` reproduce el HMA original **bit a bit**.

Lo más cómodo es el envoltorio `metodos/hma.py`, que elige los parámetros del README según el tamaño (pequeñas / 100 clientes), usa `--runs 1 --random_seed S`, y copia la solución a un archivo fijo (HMA escribe por su cuenta en `<output><nombre>_timelimit=..._subproblem=1.txt` y en modo *append*):
```bash
python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta 0.2 --rho 0 \
    --instancia /home/user/oe3/common/hma/data/akb_instances/c101_21.txt \
    --salida /tmp/sol.txt --tiempo 120 --semilla 1
```
`--reparar` aplica después a cada ruta infactible la reparación mínima de `common/consumo_carga.py` (invertir / insertar una estación / invertir + insertar), y reescribe la solución con el costo recalculado (así se arma la referencia "HMA original + reparación").

Nota: HMA mide el límite de tiempo en **tiempo de CPU** (`clock()`) y lo revisa solo al final de cada generación, por eso las corridas de 100 clientes duran ~1–5 s más que el límite.

### Qué se cambió (cambio mínimo)
HMA maneja la batería como "distancia restante" RD = energía/h. Se agregó en `Data` (`src/data.h`):
```cpp
double load_beta = 0.2, load_rho = 0.0;
inline double edist(int i, int j, double load) const
{ return dist[i][j] * (1.0 + load_beta * (load / vehicle.capacity - load_rho)); }
```
es decir, el consumo del arco en unidades de RD es e_ij(L)/h. En todo lugar donde HMA restaba `dist[i][j]` a la batería, ahora resta `edist(i, j, L)` con L = carga a bordo en ese arco (entregas pendientes + recogidas ya hechas; las estaciones y el depósito no cambian la carga):
- `src/solution.h`, `Route::check` (comprobación final de HMA): llegada a clientes y estaciones, estaciones alternativas y "energía hasta la próxima estación/depósito" (`f_f0_dist`), que fija la recarga mínima q_{f,0}; esa suma ahora sigue la carga arco por arco.
- `src/eval.cpp`: `update_route_status` (las dos versiones: con y sin ajuste de estación; las usan CLS, ALS, PSI/GA, SSI y la salida), `chk_nl_node_pos_O_n` (versión con batería, usada en la inserción de estaciones y en la construcción; incluye el nodo insertado "virtual" al seguir la carga) y la poda previa de `cal_score_station` (`dep_RD − edist(...) < 0`; antes era `dist`, que con ρ > 0 ya no sería una cota válida).
- El tiempo de recarga sigue siendo (dep_RD − arr_RD)·h·g, consistente porque RD·h es energía.
- `--beta/--rho` en `evrp_tw_spd_solver.cpp`/`data.cpp`, y se copian al subproblema en el constructor de descomposición.

### Revisión de podas y evaluaciones O(1)
- **Evaluación O(1) de movimientos** (`Attr`, `connect`, `eval_route`/`eval_move` con `--O_1_eval`): solo trata ventanas de tiempo, capacidad y distancia; **nunca** la batería. La batería se revisa después con evaluación completa O(n) (`update_route_status` + inserción de estaciones) en CLS, o se repara después en ALS. No suponía consumo constante, así que no hubo que cambiarla ni hacerla caer a una evaluación completa.
- **Poda `pm`** (`--pruning`): solo ventanas y capacidad; no cambia.
- **Ranking de estaciones `optimal_staion[a][b]`** (por desvío d_af + d_fb − d_ab): entre a y b la carga es constante (la estación no la cambia), así que el desvío de energía es (1+β(L/C−ρ)) veces el desvío de distancia y **el orden es el mismo**; no cambia.
- **Hiperarcos de Floyd–Warshall** (caminos por estaciones sin recargar, por tiempo): la carga es constante a lo largo del hiperarco, y `dist` ya es la distancia del camino completo, así que `edist` es exacto.
- **Poda en `cal_score_station`**: corregida (ver arriba).
- Costo en tiempo: el cambio agrega una multiplicación por arco y el seguimiento de la carga en los bucles de "mirar hacia adelante" ya existentes; el orden de complejidad no cambia. Con β = 0 las corridas pequeñas de 10 repeticiones tardan lo mismo (p. ej. c103C15: 16,4 s original vs 16,4 s HMA-LD; rc201C10: 8,7 vs 9,1 s, dentro del ruido de una máquina compartida) y en rc201_21 se completa el mismo número de generaciones en 30 s.

### Verificación β = 0 (reproduce HMA original)
- 6 instancias pequeñas (c101C5, c103C15, r102C10, rc108C15, r202C15, rc201C10), 10 corridas, semilla 2026, parámetros del README: los archivos de solución de HMA-LD (`--beta 0`) son **idénticos** a los del binario original y a los de `common/runs_akb_small` (rutas, baterías informadas, costo total y los 10 costos por corrida). Los registros completos (sin las líneas de tiempo) también son idénticos. Archivos en `verif_beta0/`.
- rc201_21 (100 clientes), 30 s, semilla 1: registro idéntico generación por generación (8 generaciones) y mismo costo final 5464,35.

### Validación con el juez oficial (β = 0.2, ρ = 0, `use_reported=False`)
- 36 instancias pequeñas, semilla 1, con β = 0,1, 0,2 y 0,3 (juzgadas con el mismo β): **108/108 soluciones aceptadas** por el juez (`verif_ld/pequenas_b*/corridas.csv`). Prueba de 100 clientes (rc106_21, 60 s): aceptada.
- No se encontró ninguna solución de HMA-LD rechazada por el juez. Riesgo conocido, no observado: HMA tolera batería ≥ −0,001 (`PRECISION`) y el juez exige ≥ −1e−5; no se cambió para no romper la reproducción exacta con β = 0.
- Todas las corridas de HMA-LD del conjunto de desarrollo se juzgan en `bench.py` (columna `factible`).

## 2. `bench.py`

```bash
cd /home/user/oe3/base
python3 bench.py --metodo NOMBRE --cmd 'PLANTILLA' [--conjunto conjuntos/desarrollo.txt] \
   [--semillas 1 2 3] [--t-pequenas 105] [--t-grandes 120] [--beta 0.2] [--rho 0] \
   [--solo pequenas|grandes] [--instancias c101C5 r102_21 ...] [--out carpeta] [--reanudar]
```
- Marcadores de la plantilla: `{instancia}` (ruta del .txt), `{nombre}`, `{salida}` (archivo que el método **debe** escribir), `{tiempo}` (s, entero), `{semilla}`, `{beta}`, `{rho}`. El comando se ejecuta con `cwd=/home/user/oe3/base`.
- Corre una corrida a la vez (respeta el límite de CPU). Si el método se pasa de 2·tiempo + 60 s se corta y cuenta como infactible.
- Salidas en `resultados/<metodo>/` (o `--out`): `corridas.csv` (una fila por corrida: metodo, instancia, n_clientes, semilla, tiempo_limite, **factible**, **K**, **distancia**, **costo_TC**, **energia** (con β, ρ), costo_informado, **tiempo_pared**, tiempo_cpu, codigo_salida, errores del juez), `resumen.csv` y `resumen.md` (por instancia: factibles, costo medio y mínimo entre las factibles, K medio, tiempo medio), `soluciones/` y `logs/`.
- Factible = pasa `check_solution(I, rutas, total, beta, rho, use_reported=False)` de `common/evrp.py`. Sin archivo, archivo ilegible o costo informado distinto del recalculado (> 0,01) ⇒ infactible.

Ejemplo, método en C++ (HMA-LD):
```bash
python3 bench.py --metodo hma_ld --semillas 1 2 3 \
  --cmd 'python3 metodos/hma.py --bin hma-ld/bin/evrp-tw-spd --beta {beta} --rho {rho} --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla}'
# o directamente un binario propio que acepte esos argumentos:
#  --cmd '/home/user/oe3/<agente>/bin/mi_solver {instancia} {salida} {tiempo} {semilla}'
```
Ejemplo, método en Python:
```bash
python3 bench.py --metodo mi_metodo --solo pequenas --semillas 1 \
  --cmd 'python3 /home/user/oe3/<agente>/mi_metodo.py --instancia {instancia} --salida {salida} --tiempo {tiempo} --semilla {semilla} --beta {beta} --rho {rho}'
```

### Formato de la solución (el de HMA, lo lee `evrp.read_solution`)
```
route 0, node_num 7, cost 151.49, nodes: 0 8 5 1 6 4 0
route 1, node_num 5, cost 106.26, nodes: 0 2 7 3 0
Total cost: 2257.75
```
- Una línea por ruta que empiece con `route` y contenga `nodes:`; después, los ids separados por espacios, empezando y terminando en 0 e incluyendo las estaciones visitadas. Cada nodo puede llevar `(y, Y)` (se ignora con `use_reported=False`). Lo que va entre `route` y `nodes:` no se usa.
- `Total cost: X` con X = μ1·K + μ2·D (conviene escribirlo con 2 decimales; tolerancia 0,01).
- Las demás líneas se ignoran. **No hace falta informar la recarga**: el juez calcula el plan de recarga exacto (programa lineal) para cada secuencia.
- En Python basta con `metodos/hma.py: escribir_solucion(path, I, rutas)` (rutas = listas de ids; I = `evrp.read_instance(...)`).

## 3. Conjuntos (archivos en `conjuntos/`)
- `desarrollo.txt` (24): **pequeñas** c101C5, c104C10, c103C15, c202C15, r104C5, r102C10, r201C10, r105C15, rc105C5, rc204C5, rc201C10, rc108C15 (4 de c, r y rc; 4 de 5, 10 y 15 clientes; incluye tipo 1 y 2; 7 de ellas tienen solución publicada que deja de ser factible con β = 0,2) y **100 clientes** c101_21, c106_21, c202_21, c206_21, r102_21, r108_21, r202_21, r209_21, rc102_21, rc106_21, rc202_21, rc206_21 (2 de cada c1, c2, r1, r2, rc1, rc2).
- `reservado.txt` (68): el resto de akb (24 pequeñas + 44 de 100 clientes). No usar para ajustar.
- `todas_pequenas.txt`: las 36 pequeñas (usado en la validación).
- Presupuestos por defecto: **105 s** (pequeñas, igual que el artículo) y **120 s** (100 clientes; el artículo usa 630 s, se acorta por el CPU compartido). HMA en las pequeñas termina antes por su criterio de 20 generaciones sin mejora.

## 4. Resultados de las referencias (desarrollo, 3 semillas: 1, 2, 3; β = 0,2, ρ = 0; juez oficial)
(a) **HMA-LD** (`resultados/hma_ld/`); (b) **HMA original + reparación mínima posterior** de `common/consumo_carga.py` (`resultados/hma_orig_reparado/`). Una corrida de HMA por semilla (`--runs 1`), presupuesto 105 s / 120 s de CPU. Script: `correr_referencias.sh`; tabla: `resultados/tabla_referencias.md`. TC y K medios se calculan solo sobre las corridas factibles.

| instancia | HMA-LD: fact. | HMA-LD: TC medio | HMA-LD: K medio | HMA orig. + reparación: fact. | HMA orig. + reparación: TC medio | HMA orig. + reparación: K medio |
|---|---|---|---|---|---|---|
| c101C5 | 3/3 | 2257.75 | 2 | 3/3 | 2257.75 | 2 |
| c104C10 | 3/3 | 2273.93 | 2 | 3/3 | 2273.93 | 2 |
| c103C15 | 3/3 | 3374.43 | 3 | 0/3 | — | — |
| c202C15 | 3/3 | 2383.62 | 2 | 3/3 | 2383.62 | 2 |
| r104C5 | 3/3 | 2136.69 | 2 | 3/3 | 2136.69 | 2 |
| r102C10 | 3/3 | 3285.18 | 3 | 0/3 | — | — |
| r201C10 | 3/3 | 1265.05 | 1 | 0/3 | — | — |
| r105C15 | 3/3 | 4352.72 | 4 | 3/3 | 4352.72 | 4 |
| rc105C5 | 3/3 | 2241.3 | 2 | 0/3 | — | — |
| rc204C5 | 3/3 | 1176.39 | 1 | 3/3 | 1176.39 | 1 |
| rc201C10 | 3/3 | 2323.5 | 2 | 2/3 | 2323.56 | 2 |
| rc108C15 | 3/3 | 3370.37 | 3 | 3/3 | 3370.37 | 3 |
| c101_21 | 3/3 | 13047.08 | 12 | 3/3 | 13049.39 | 12 |
| c106_21 | 3/3 | 12026.81 | 11 | 0/3 | — | — |
| c202_21 | 3/3 | 4641.07 | 4 | 0/3 | — | — |
| c206_21 | 3/3 | 4639.88 | 4 | 0/3 | — | — |
| r102_21 | 3/3 | 17763.91 | 16.33 | 3/3 | 17446.67 | 16 |
| r108_21 | 3/3 | 12039.08 | 11 | 0/3 | — | — |
| r202_21 | 3/3 | 4081.37 | 3 | 3/3 | 4380.05 | 3.33 |
| r209_21 | 3/3 | 3893.36 | 3 | 3/3 | 3899.15 | 3 |
| rc102_21 | 3/3 | 15858.57 | 14.33 | 0/3 | — | — |
| rc106_21 | 3/3 | 15094.02 | 13.67 | 0/3 | — | — |
| rc202_21 | 3/3 | 5248.52 | 4 | 3/3 | 5252.63 | 4 |
| rc206_21 | 3/3 | 4536.75 | 3.33 | 3/3 | 4542.76 | 3.33 |

- HMA-LD: 72/72 corridas factibles (juez oficial, beta=0.2, rho=0).
- HMA orig. + reparación: 41/72 corridas factibles (juez oficial, beta=0.2, rho=0).

Lectura:
- HMA-LD: **72/72** factibles. Con la reparación posterior solo **41/72** (pequeñas 23/36, 100 clientes 18/36); 6 de las 12 instancias de 100 clientes (c106, c202, c206, r108, rc102, rc106) quedan sin ninguna corrida factible.
- Donde ambas son factibles, los costos son casi iguales en las pequeñas; HMA-LD paga algo más de distancia donde la solución original deja de ser factible (p. ej. c103C15: 3374,43 frente a 3348,46 de HMA original, que el juez rechaza aun reparada; r201C10: 1265,05 frente a 1241,51).
- En 100 clientes, r102_21 y r202_21 muestran variación entre semillas (r102_21 HMA-LD: 16,33 vehículos medios frente a 16 con reparación; r202_21: HMA-LD es mejor, 4081 vs 4380).

**Ojo con el presupuesto:** HMA termina una corrida cuando lleva 20 generaciones sin mejora (`--g_1 20`), así que en varias instancias usa mucho menos que el presupuesto (tiempo medio de HMA-LD: c101_21 8,5 s; c202_21 28 s; c206_21 30 s; r102_21 38 s; c106_21 53 s; las pequeñas 0,1–6 s). Para comparar un método que usa los 120 s completos es más justo usar la variante multiarranque (4b).

### 4b. HMA-LD multiarranque (`--llenar`, solo 100 clientes)
`metodos/hma.py --llenar` relanza HMA-LD (semillas semilla·1000+k) con el tiempo de CPU restante hasta agotar el presupuesto y se queda con la mejor solución aceptada por el juez. Resultados en `resultados/hma_ld_llenar/`.

*(se completa al terminar)*

## 5. Limitaciones y notas honestas
- La reproducción exacta con β = 0 se verificó en 6 pequeñas (10 corridas cada una) y en una de 100 clientes por 30 s; las de 100 clientes no son deterministas en general porque el corte es por tiempo de CPU.
- Presupuesto de 120 s en 100 clientes (el artículo usa 630 s): los costos de 100 clientes **no** son comparables con los publicados.
- HMA tolera batería ≥ −0,001 en unidades de distancia; el juez exige ≥ −1e−5. No se observó ningún rechazo (180/180 soluciones de HMA-LD aceptadas), pero no está garantizado.
- La variante "HMA original + reparación + multiarranque" no se corrió (CPU); la referencia (b) usa una corrida por semilla.
- `tiempo_pared` incluye el sobrepaso de HMA (revisa el reloj al final de cada generación: hasta ~4 s en 100 clientes) y el arranque del envoltorio.
