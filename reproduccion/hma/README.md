# Primera reproducción de HMA

Fecha: 10 de septiembre de 2026.

## Elección del trabajo

Comenzamos con **Hybrid Memetic Search for Electric Vehicle Routing with Time Windows, Simultaneous Pickup-Delivery, and Partial Recharges**, de Zubin Zheng, Shengcai Liu y Yew-Soon Ong.

- [Artículo, versión arXiv v2](https://arxiv.org/html/2410.19580v2).
- [Repositorio de los autores](https://github.com/0SliverBullet/EVRP-TW-SPD-HMA).
- Revisión fijada: `0ebbcaa4c2b8385c2c9bff06d60689cb2c64229d`.

HMA permite empezar con código C++ y datos publicados, instrucciones de compilación y archivos de soluciones de referencia. La copia local está en `.local/upstream`, excluida del control de versiones; el script puede descargarla nuevamente.

Para Adapt-CMSA verificamos el [artículo de 2024](https://link.springer.com/article/10.1007/s10479-024-06295-9) y su [repositorio de instancias](https://github.com/manilakbay/EVRP-TW-SPD-Instances). No confirmamos un repositorio del algoritmo. HMA, sección V-B, indica que sus autores tomaron los resultados de Adapt-CMSA de las publicaciones porque el código no era público. El método CMSA utiliza CPLEX en sus experimentos. Esto hace que HMA sea la opción más accesible para nuestra primera reproducción; no demuestra que CMSA sea imposible de obtener actualmente.

## Qué estamos reproduciendo

HMA utiliza consumo energético constante por distancia y costo de despacho más costo de transporte. El modelo con consumo dependiente de la carga y cuatro criterios del paper del proyecto es diferente. Conservamos el modelo original para que la comparación tenga sentido.

El artículo de HMA ya incorpora búsqueda en los dominios eléctrico y no eléctrico (CDNS). Una futura propuesta de realimentación entre ambos dominios tendría que compararse con ese componente antes de considerarse un aporte nuevo.

## Resultado local

Compilamos el código original sin modificarlo y ejecutamos el ejemplo pequeño con semilla inicial explícita 2026, diez corridas y límite de 105 segundos por corrida.

| Medida en c101C5 | HMA publicado, tabla II | Ejecución local |
| --- | ---: | ---: |
| Vehículos de la mejor solución | 2 | 2 |
| Mejor costo | 2257.75 | 2257.75 |
| Costo medio de diez corridas | 2257.75 | 2257.75 |

Los diez costos locales coinciden con el valor publicado a dos decimales. El resumen interno registra costo 2257.747452: 2000 por despacho más 257.747452 de transporte. La solución final pasó el comprobador interno del programa; todavía no hicimos una validación independiente de todas las restricciones.

Archivos de esta ejecución:

- `resultados/20260910T163702334537Z/metadatos.json`: revisión, plataforma, compilador, comandos, hashes de instancia y ejecutable.
- `resultados/20260910T163702334537Z/compilacion.log`: salida del compilador.
- `resultados/20260910T163702334537Z/ejecucion.log`: registro completo del programa.
- `resultados/20260910T163702334537Z/c101C5_timelimit=105_subproblem=1.txt`: rutas y diez resultados.

Entorno local: macOS ARM64, Apple Clang 21.0.0, C++11 y optimización `-O3`. Se emitieron dos advertencias de formato de `printf` en el bloque de medición de evaluaciones de movimientos; no impidieron compilar y quedaron registradas. No cambiamos el código para silenciarlas.

Las corridas terminaron antes de agotar el límite. El archivo registra 0.22 segundos en la primera y 0.19 en las nueve restantes. No interpretamos esto como una mejora de velocidad sobre el artículo: el hardware y compilador son diferentes, y debe revisarse la semántica de medición de tiempo del código. Tampoco afirmamos coincidencia de semillas con las usadas por los autores: fijamos nuestra semilla inicial para registrar el experimento, y el programa gestiona las corridas internamente.

## Cómo repetir

Se requieren Python 3, git y un compilador disponible como `g++` con soporte C++11. En este Mac ese comando corresponde a Apple Clang.

```bash
python3 reproduccion/hma/replicar.py
```

El script descarga la revisión fijada si falta, comprueba que la copia original esté limpia, compila y crea una carpeta nueva por ejecución. El máximo configurado es de 105 segundos por corrida, diez corridas. No modifica los datos ni las soluciones originales. Si falla, conservar los registros para diagnosticarlo.

## Alcance y siguiente etapa

Esto confirma que podemos ejecutar el código original y recuperar el costo publicado en una instancia pequeña. Aún no reproduce las tablas completas, los análisis estadísticos ni las conclusiones generales del artículo.

Propuesta de primer hito para conversar con el profesor:

> Reproducir HMA con el código de los autores sobre las 36 instancias pequeñas del conjunto akb, registrar diez corridas por instancia y contrastar mejor costo, costo medio y factibilidad con la tabla II. Documentar el entorno y las diferencias respecto del protocolo original.

Antes del lote completo: leer conjuntamente las secciones III–V, revisar la correspondencia del pseudocódigo con el código y preparar un validador independiente. Después, ampliar a instancias de 100 clientes. La extensión del modelo y la búsqueda de un aporte propio vendrán sobre esta base comprobada.
