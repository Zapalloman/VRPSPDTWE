# Verificación independiente y prueba de concepto

Código propio, escrito a partir de la definición del problema y sin reutilizar código de HMA.

| Archivo | Qué hace |
| --- | --- |
| `evrp.py` | Lector de instancias y soluciones, evaluador de rutas y comprobador independiente. El plan de recarga de una secuencia fija se decide con un programa lineal exacto. Soporta consumo dependiente de la carga `e_ij(L) = h·d_ij·(1 + β(L/C − ρ))`. |
| `validar_publicadas.py` | Valida las 172 soluciones publicadas por los autores de HMA (akb y jd). |
| `pruebas_mutacion.py` | Inyecta cinco tipos de error en las 92 soluciones akb y comprueba que el verificador los detecte. |
| `comparar_replica.py` | Compara la réplica local de las 36 instancias pequeñas con los valores publicados y valida cada solución. |
| `consumo_carga.py` | Re-evalúa las soluciones publicadas con consumo dependiente de la carga (β = 0 a 0,4; ρ = 0 y 0,5) y aplica una reparación mínima. |
| `resumir.py` | Genera las tablas resumidas y la figura de infactibilidad. |

Requiere Python 3 con `numpy`, `scipy` y `matplotlib`. Se asume una copia del repositorio de HMA en la revisión `0ebbcaa` (la que descarga `reproduccion/hma/replicar.py` en `reproduccion/hma/.local/upstream`).

```bash
H=reproduccion/hma/.local/upstream
cd verificacion
python3 validar_publicadas.py ../$H
python3 pruebas_mutacion.py ../$H
python3 comparar_replica.py ../$H ../reproduccion/hma/resultados/akb_pequenas_linux
python3 consumo_carga.py ../$H publicadas consumo_publicadas.json   # ~20 min con 4 núcleos
python3 resumir.py consumo_publicadas.json publicadas
```

## Resultados principales (noviembre de 2026)

- **Comprobador:** 172/172 soluciones publicadas factibles y con costo coincidente (< 0,01). Con las recargas informadas en los archivos, 18 muestran diferencias ≤ 0,022 por el redondeo a dos decimales. Detecta 458/460 errores inyectados; los 2 restantes generan otra solución factible de igual costo.
- **Réplica de HMA, 36 instancias pequeñas, 10 corridas, semilla 2026:** 35/36 mejores costos y 34/36 promedios iguales a los publicados. En `rc201C10` se obtuvo 2323,06 (2 vehículos) frente a 1412,86 (1 vehículo); con la semilla 123 se obtiene 1412,86, por lo que la diferencia depende de la semilla.
- **Consumo dependiente de la carga (β = 0,2; ρ = 0):** dejan de ser factibles 11/36 soluciones pequeñas y 52/56 de 100 clientes, con aumentos de energía de solo 2–3 % y 6,4 %. Insertar una estación recupera 111 de 200 rutas infactibles de 100 clientes; 33/56 soluciones siguen infactibles sin re-optimizar. Con β = 0,1 ya son 40/56; con β = 0,3, 52/56. Con ρ = 0,5 la energía total baja, pero 4/56 soluciones de 100 clientes igualmente dejan de ser factibles.

β = 0,2 se calibra con Cieslik y Antczak (2023, *Energies* 16(2), 775): un furgón eléctrico de 2115 kg con 850 kg de carga consumió casi 20 % más en ciudad (≈8 % en carretera). β = 0,1 y 0,3 son las cotas del análisis de sensibilidad.
