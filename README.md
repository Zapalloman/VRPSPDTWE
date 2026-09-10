# Investigación de tesis: VRPSPDTW-E

**Investigador: Javier Farías**

Universidad Andrés Bello

Investigación sobre el ruteo de vehículos eléctricos con recogida y entrega simultáneas y ventanas de tiempo (**VRPSPDTW-E**, también denominado **EVRP-TW-SPD**).

El problema consiste en planificar rutas desde un depósito para entregar y recoger mercancía en una misma visita. Las rutas deben respetar la capacidad del vehículo, los horarios de los clientes y la autonomía de la batería, incluyendo estaciones y recargas parciales cuando sean necesarias.

## Etapa actual

La tesis está en su etapa inicial. El primer objetivo es reproducir un método publicado, comprender su implementación y comparar los resultados antes de proponer modificaciones propias.

El paper incluido en este repositorio proviene de un trabajo académico anterior y sirve como antecedente. Se conserva sin cambios, incluida su autoría original; no representa una tesis terminada.

## Primera réplica: HMA

Se utilizó el código original del algoritmo HMA de Zubin Zheng, Shengcai Liu y Yew-Soon Ong, descrito en [Hybrid Memetic Search for Electric Vehicle Routing with Time Windows, Simultaneous Pickup-Delivery, and Partial Recharges](https://arxiv.org/html/2410.19580v2).

El [repositorio oficial de HMA](https://github.com/0SliverBullet/EVRP-TW-SPD-HMA) proporciona el código y los datos. Esta investigación conserva la atribución a sus autores; el código del algoritmo no es un desarrollo propio.

Se compiló el código sin modificarlo y se ejecutó la instancia `c101C5`, de cinco clientes, diez veces, con semilla inicial 2026 y un límite de 105 segundos por corrida.

| Medida | Publicado en la tabla II | Resultado local |
| --- | ---: | ---: |
| Mejor costo | 2257.75 | 2257.75 |
| Costo promedio | 2257.75 | 2257.75 |
| Vehículos de la mejor solución | 2 | 2 |

La solución pasó la comprobación interna del programa. Esta primera réplica cubre una instancia; aún falta validar las restricciones de forma independiente y reproducir más resultados. Los tiempos no se comparan directamente porque el hardware es diferente.

HMA utiliza consumo constante por distancia y un objetivo de costo de vehículos más transporte. La extensión con consumo dependiente de la carga planteada en el paper previo queda fuera de esta reproducción inicial.

## Cómo repetir el experimento

Se requieren Python 3, Git y un compilador compatible con C++11 disponible como `g++`.

Desde la raíz del repositorio:

```bash
python3 reproduccion/hma/replicar.py
```

El script descarga una revisión fija del código original, compila y ejecuta diez corridas. Cada ejecución guarda sus resultados, comandos y metadatos en una carpeta nueva. El código descargado y el ejecutable quedan en una carpeta local excluida de Git.

Consulta la [guía de reproducción](reproduccion/hma/README.md) para revisar el protocolo, sus limitaciones y los archivos generados.

## Contenido

- [`reproduccion/hma/`](reproduccion/hma/): script, documentación y registros de la primera réplica.
- [`paper.pdf`](paper.pdf): paper del trabajo académico previo.
- [`latex/`](latex/): fuente LaTeX y versión compilada del paper previo.
- Los dos pósteres PDF presentan el contexto del problema y la revisión anterior.

## Próximos pasos

1. Estudiar el artículo de HMA y relacionar sus componentes con el código.
2. Preparar una validación independiente de las soluciones.
3. Ampliar la réplica a las 36 instancias pequeñas del conjunto `akb`.
4. Comparar los resultados con la publicación y documentar las diferencias.
5. Definir una pregunta de tesis a partir de la evidencia obtenida.
