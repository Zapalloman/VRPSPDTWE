# OE3: método que considera el consumo según la carga durante la búsqueda

Experimentos del objetivo específico 3. Todos los resultados se midieron con el juez oficial `verificacion/evrp.py`:

```python
check_solution(I, rutas, total, beta=0.2, rho=0.0, use_reported=False)
```

Este llamado calcula el plan de recarga exacto con un programa lineal.

## Resultado principal

**Método final:** HMA-LD-afín + pool de rutas con *set partitioning* + eliminación de vehículos (carpeta `combinado/`).

**Prueba:** 44 instancias akb de 100 clientes del conjunto reservado, semillas 1 y 2, 120 s de CPU por corrida. Se compara con HMA-LD multiarranque, que usa el mismo presupuesto.

| | HMA-LD (multiarranque) | Método final |
|---|---|---|
| Corridas factibles | 88/88 | 88/88 |
| Vehículos totales | 706 | 688 (−18) |
| ΔTC medio por par | | −1,90 % (de −24,5 % a +0,43 %) |
| Mejor / igual / peor | | 61 / 13 / 14 |
| Prueba de signos / Wilcoxon | | p = 3,8·10⁻⁸ / p = 5,4·10⁻⁹ |

En las 24 instancias pequeñas reservadas, los costos son idénticos a los de HMA-LD.

## Carpetas

| Carpeta | Contenido |
|---|---|
| `CONTEXTO.md` | Problema, reglas comunes y conjuntos de prueba. |
| `base/` | HMA-LD: HMA (Zheng, Liu y Ong 2025, rev. 0ebbcaa) adaptado a consumo según la carga. Con β = 0 reproduce el original. También contiene `bench.py`, los conjuntos de desarrollo y reservado (`conjuntos/`) y los resultados de referencia. |
| `afin/` | Idea A: la energía es afín en la carga de entrada. Los resúmenes concatenables permiten evaluar en O(1) y elegir estaciones de forma exacta. |
| `recarga/` | Idea B: algoritmo de etiquetas exacto para estaciones y cantidades con una secuencia fija. Evalúa en O(n). |
| `pool/` | Idea C: pool de rutas factibles y *set partitioning* (HiGHS) dentro de HMA-LD. |
| `combinado/` | Método final (A + C + eliminación de vehículos), con la ablación en desarrollo y la prueba en el reservado. |

Cada carpeta tiene un `PROPUESTA.md` con la idea, el mecanismo, la novedad, la implementación, los resultados y los límites.

## Notas para reproducir

- Los scripts usan rutas absolutas `/home/user/oe3/...`. Copia o enlaza esta carpeta ahí, o ajusta las rutas.
- `common/` corresponde a `verificacion/` de este repositorio, más una copia de HMA en `common/hma`.
- Las instancias (`data/`) y los binarios no se incluyen. Las instancias vienen del repositorio de HMA, que descarga `reproduccion/hma/replicar.py`. Para compilar, en cada carpeta `hma-*`:

  ```bash
  g++ -std=c++11 -O3 -o bin/evrp-tw-spd src/*.cpp
  ```

- Las corridas se hicieron en una máquina de 4 núcleos compartida, con un proceso de un hilo por corrida. El presupuesto se mide en tiempo de CPU.
