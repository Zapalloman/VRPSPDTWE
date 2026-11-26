# Guion presentación E2: metodología y avance

Acompaña a `Presentacion_VRPSPDTW-E_UNAB_v5.pptx` (18 diapositivas, unos 15 minutos). Versión editable: Claude Doc "Guion presentación E2: metodología y avance".

## Mapa con la rúbrica

| Criterio de la rúbrica (puntos) | Dónde se responde |
| --- | --- |
| Metodología y diseño de evaluación (20) | 6 Metodología, 14 Resultados |
| Plan de trabajo y gestión (15) | 10 Plan de trabajo y gestión |
| Arquitectura y decisiones técnicas (15) | 8 Arquitectura |
| Algoritmos, complejidad e IA (20) | 9 Algoritmos, 13 Método propuesto |
| Fuentes y modelamiento de datos (10) | 7 Fuentes y datos |
| MVP o avance demostrable (15) | 11, 12 y 14 Resultados |
| Comunicación del avance (5) | 15 a 17: conclusiones, límites y próximos pasos |

**Regla de oro:** cada vez que afirmes algo, di el número y cómo lo mediste.

## Diapositivas 1 a 6

**1. Portada (15 s).** "Buenos días. Presento el avance de mi proyecto de título: ruteo de vehículos eléctricos con recogida y entrega simultáneas, ventanas de tiempo y consumo que depende de la carga."

**2. Contenidos (10 s).** "Primero el problema y los objetivos. Después cómo trabajé: metodología, datos, arquitectura, algoritmos y plan. Al final, los resultados."

**3. Introducción (45 s).** "Tres tendencias se juntan en la última milla: flotas eléctricas, logística inversa y ventanas de tiempo. El furgón sale con todas las entregas, en cada cliente deja y recoge, así que **el peso a bordo cambia durante la ruta**. Un vehículo eléctrico gasta más energía mientras más pesa. Por eso el orden de visita cambia la energía, y con ella, si la ruta alcanza o no con la batería."

**4. Discusión bibliográfica (45 s).** "El mejor método publicado para esta variante es HMA, de Zheng y coautores (2025). HMA supone consumo constante. Rastani y Çatay, y Zachariadis y coautores, sí consideran el peso, pero sin recogida y entrega simultáneas o sin batería. **Nadie había juntado las cuatro cosas**: esa es la brecha."

**5. Objetivos (40 s).** "El objetivo general es un método eficiente para esta versión más realista. Lo dividí en tres objetivos específicos. OE1: una base verificable. OE2: medir cuánto falla la referencia. OE3: diseñar un método y demostrar que es mejor."

**6. Metodología (1 min 15 s; 20 puntos).** "Trabajé en cuatro fases, cada una con un entregable. Lo central está abajo:

- **Línea base:** no comparo contra HMA original, porque resuelve otro problema. Adapté HMA al mismo modelo de energía; la llamo HMA-LD. Compite con el mismo tiempo y en las mismas instancias.
- **Métricas:** costo total, vehículos, distancia, porcentaje de soluciones factibles y tiempo de CPU.
- **Pruebas:** Wilcoxon y prueba de signos, pareadas por instancia y semilla.
- **Validación:** ninguna solución cuenta si no pasa un juez independiente que escribí yo. El juez recalcula la recarga óptima con un programa lineal.
- **Contra el sobreajuste:** separé las instancias en desarrollo (12) y reservado (44), y el reservado se usó una sola vez."

## Diapositivas 7 a 10

**7. Fuentes y modelamiento de datos (50 s).** "Uso las instancias públicas del artículo de HMA: akb, con 92 instancias, y jd, con 20 instancias grandes. También uso las 172 soluciones que publicaron sus autores. El valor del parámetro de energía, **β = 0,2, no lo inventé**: viene de mediciones reales de Cieslik y Antczak (2023), donde un furgón cargado gastó 20 % más en ciudad. Para verificar la calidad de los datos, el juez validó las 172 soluciones publicadas. El flujo es: lector propio, modelo con carga y β, división en desarrollo y reservado, y un CSV por corrida."

**8. Arquitectura y decisiones técnicas (1 min; 15 puntos).** "Son cuatro componentes en cadena: las instancias, el solver en C++, el set partitioning en Python con HiGHS, y el juez con el banco de pruebas. Cada tecnología tiene una razón:

- **Eficiencia:** C++ porque la búsqueda evalúa millones de movimientos.
- **Calidad:** Python para el juez, separado del solver, para que el algoritmo nunca se califique a sí mismo.
- **Mantenibilidad:** cada componente se enciende o apaga por parámetro, y en cero reproduce HMA exacto. Así pude medir el aporte de cada pieza.
- **Seguridad y trazabilidad:** son datos públicos, sin datos personales, con semillas fijas y todo versionado en Git."

**9. Algoritmos, complejidad e IA (1 min 15 s; 20 puntos).** "El aporte técnico central es de complejidad. Con consumo constante, HMA evalúa cada movimiento en O(1). Con consumo según la carga, eso parecía perderse: un cambio al inicio de la ruta cambia el peso de todos los tramos siguientes, y la evaluación pasa a ser O(n). **Demostré que la energía es afín en la carga de entrada, así que basta un número extra por tramo para volver a O(1).** Con estaciones, la recarga se decide de forma exacta en O(m). Medido: los movimientos son entre 3,7 y 8,8 veces más rápidos.

Sobre IA: sí uso IA clásica, que es búsqueda metaheurística. No uso aprendizaje automático, y es una decisión justificada. El problema exige soluciones factibles garantizadas, no hay datos de entrenamiento etiquetados, y la literatura muestra que los métodos neuronales todavía no compiten con las metaheurísticas en ruteo con restricciones (Liu y coautores, 2023)."

**10. Plan de trabajo y gestión (1 min; 15 puntos).** "Las cuatro fases están completas. Lo único pendiente es correr con 630 segundos, como el artículo. Registré las decisiones:

- β calibrado con mediciones reales.
- 120 segundos por corrida, porque el equipo de cómputo es compartido.
- Después de una primera ronda con tres ideas separadas, ninguna ganaba de forma significativa, así que decidí combinar las dos mejores.

Riesgos y su mitigación: el sobreajuste se controla con el conjunto reservado; el azar, con varias semillas; la incertidumbre de β, con un análisis de sensibilidad. Todo queda trazado en Git, con pull requests. Responsables: yo en el desarrollo y los experimentos, y el profesor guía en la revisión."

## Diapositivas 11 a 18

**11. Resultados: base verificable (45 s).** "Primero comprobé que la base fuera confiable. Al replicar HMA obtuve 35 de 36 mejores costos iguales a los publicados; el caso restante depende de la semilla, lo verifiqué con cinco semillas. El juez aceptó las 172 soluciones publicadas y detectó 458 de 460 errores que le introduje a propósito. **Sin este paso, ningún número posterior sería creíble.**"

**12. Resultados: prueba de concepto (50 s).** "Después tomé las soluciones publicadas de HMA y las recalculé considerando el peso. Con solo 6 % más de energía, **52 de 56 soluciones de 100 clientes ya no se pueden ejecutar**, porque HMA recarga justo lo necesario y no deja holgura. Insertar una estación no basta en 33 de ellas. Un algoritmo exacto de recarga demostró que la causa es el orden de los clientes, no la recarga. Conclusión: la carga tiene que entrar en la búsqueda."

**13. Método propuesto (1 min).** "El método tiene tres piezas:

1. La evaluación afín, que mantiene la búsqueda en O(1) y libera alrededor de 40 % del tiempo.
2. Un pool que guarda todas las rutas factibles que encuentra la búsqueda. Cada 25 segundos, un modelo exacto de set partitioning elige la mejor combinación.
3. Un operador que intenta vaciar la ruta más fácil de eliminar, porque cada vehículo cuesta 1000.

La idea en una frase: **la carga entra en cada movimiento de la búsqueda, no como reparación final.**"

**14. Resultados: método propuesto (1 min 15 s; avance demostrable).** "Lo probé en las 44 instancias reservadas, que nunca usé para ajustar, con 2 semillas y el mismo tiempo que HMA-LD. Las 88 soluciones son factibles según el juez. Resultado: **18 vehículos menos y 1,9 % menos de costo en promedio**, con casos de hasta −24 %. Gana en 61 pares, empata en 13 y pierde en 14, siempre por menos de 0,5 %. El valor p de Wilcoxon es 5·10⁻⁹. Además, el estudio por componentes en desarrollo muestra que cada pieza suma."

**15. Conclusiones (40 s).** "Los tres objetivos están cumplidos con evidencia: una base verificada, un diagnóstico cuantificado y un método que supera a la referencia de forma significativa."

**16. Limitaciones (30 s).** "Lo digo con honestidad:

- Corrí 120 segundos y no 630.
- Usé 2 a 3 semillas.
- En las instancias pequeñas el método empata con HMA.
- β se apoya en pocas mediciones.
- El aporte está en cómo integré piezas que ya existían por separado."

**17. Próximos pasos (30 s).** "Primero, repetir con 630 segundos, más semillas y las instancias jd grandes. Después: recarga no lineal, precios de electricidad variables y validación con datos reales."

**18. Gracias (5 s).** "Gracias. Quedo atento a sus preguntas."

## Preguntas probables y respuestas cortas

**¿Por qué 120 segundos y no 630 como el artículo?** Porque el equipo tiene 4 núcleos compartidos y necesitaba cientos de corridas. Las dos versiones tuvieron exactamente el mismo tiempo, así que la comparación es justa. Repetir con 630 s es el primer próximo paso.

**¿No le ganas solo porque tu HMA-LD está mal adaptado?** Con β = 0, HMA-LD reproduce exactamente a HMA original, y con β = 0,1, 0,2 y 0,3 sus 108 soluciones pasan el juez. Además, la referencia usa multiarranque para gastar todo el tiempo disponible, igual que mi método.

**¿Qué es lo nuevo, si las piezas ya existían?** La forma afín de la energía con un solo número extra, que mantiene O(1) aunque el consumo dependa de la carga, y su combinación con un pool verificado de forma exacta. Nadie lo había aplicado a esta variante con recogida y entrega simultáneas.

**¿Por qué β = 0,2?** Lo midieron Cieslik y Antczak (2023) en un furgón eléctrico de reparto: 20 % más de consumo urbano a carga completa. También probé 0,1 y 0,3. Con 0,1, igual dejan de ser factibles 40 de 56 soluciones de HMA.

**¿Por qué la mejora es solo 1,9 %?** Porque en este problema el vehículo domina el costo: vale 1000, mientras que la distancia de una ruta es de unos cientos. Ahorrar 18 vehículos es la ganancia real. Cuando el método elimina un vehículo, el costo baja entre 5 % y 24 %.

**¿Cómo sé que las soluciones son correctas?** Cada una pasa un juez independiente que recalcula todo y resuelve la recarga óptima con un programa lineal. Ese juez detectó 458 de 460 errores introducidos a propósito.

**¿Dónde se puede ver el avance?** En el repositorio de GitHub: código, resultados por corrida, tablas y el informe v4, con la historia de commits.
