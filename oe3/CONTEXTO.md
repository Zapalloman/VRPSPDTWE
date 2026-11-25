# Contexto común para los agentes del OE3

Tesis de pregrado (UNAB) de Javier: ruteo de vehículos eléctricos con recogida y entrega simultáneas en una visita, ventanas de tiempo, recarga parcial lineal y **consumo de energía dependiente de la carga** (VRPSPDTW-E / EVRP-TW-SPD con consumo según la carga). Escribe todo lo que entregues en **español**.

## Problema (modelo de la tesis)
- Depósito 0, clientes con entrega u_i y recogida v_i en la misma visita, ventana [e_i, l_i] para *iniciar* la atención, servicio s_i. Flota homogénea: capacidad C, batería Q, consumo h por distancia, g = tiempo por unidad de energía recargada. Estaciones (tipo `f`) con recarga parcial lineal.
- La ruta sale con todas sus entregas; tras el cliente i la carga es L − u_i + v_i ≤ C.
- Energía del arco (i,j) recorrido con carga L: **e_ij(L) = h · d_ij · (1 + β · (L/C − ρ))**, con **β = 0,2 y ρ = 0** (caso central, calibrado con Cieslik y Antczak 2023: +20 % de consumo urbano a carga completa). Cotas de sensibilidad: β = 0,1 y 0,3.
- Objetivo (igual que HMA): TC = μ1·K + μ2·D (μ1 = costo por vehículo, típicamente 1000; μ2 = 1 por distancia). La energía no entra en el objetivo, solo en la factibilidad.

## Lo que ya existe
- `hma/`: código C++ original de HMA (Zheng, Liu y Ong 2025, arXiv:2410.19580), revisión 0ebbcaa, **consumo constante**. Instancias en `hma/data/akb_instances` (36 pequeñas de 5/10/15 clientes, 56 de 100 clientes con 21 estaciones) y `hma/data/jd_instances`. Soluciones publicadas en `hma/solution/`. Compilar: `g++ -std=c++11 -O3 -o bin/evrp-tw-spd src/*.cpp` (ver hma/README.md para los parámetros por tamaño). En HMA la batería se maneja como "distancia restante" (consumo constante), ver `src/eval.cpp`, `src/solution.h`.
- `evrp.py`: comprobador independiente en Python. `read_instance`, `read_solution` (formato de salida de HMA), `eval_route(I, nodes, beta, rho)` (plan de recarga exacto por programa lineal para una secuencia fija), `check_solution(I, routes, total, beta, rho, use_reported=False)`. **Es el juez oficial**: una solución solo cuenta si pasa `check_solution(..., beta=0.2, rho=0.0, use_reported=False)`.
- `consumo_carga.py`: re-evaluación de las soluciones publicadas de HMA con consumo según la carga + reparación mínima (invertir ruta / insertar una estación).

## Hallazgos que motivan el OE3 (β = 0,2, ρ = 0)
- Re-evaluadas con consumo según la carga, **dejan de ser factibles 11/36 soluciones pequeñas y 52/56 de 100 clientes**, con solo +2–3 % y +6,4 % de energía: las soluciones de HMA recargan exactamente lo necesario y no dejan holgura.
- Insertar una estación recupera 111 de 200 rutas infactibles de 100 clientes; **33/56 soluciones siguen infactibles** sin re-optimizar.
- Para una secuencia fija, la política "cargar lo más tarde posible" rechaza 42 de 172 soluciones publicadas que sí son factibles: con ventanas, *cuánto y dónde* recargar interactúa con la secuencia (las esperas permiten recargar "gratis").
- En las instancias akb la ocupación media es baja en las pequeñas (10–13 % de C) y mayor en las de 100 clientes (≈33 %, máx. 91 %).

## Recursos de cómputo (IMPORTANTE)
La máquina tiene **4 núcleos compartidos por todos los agentes**. Ejecuta **un solo proceso pesado a la vez** (nada de xargs -P ni multiprocessing con más de 1 worker), salvo que el coordinador te diga otra cosa. Limita tus corridas: para instancias de 100 clientes usa límites cortos (p. ej. 60–120 s) y pocas semillas durante el desarrollo.

## Reglas de la competencia
- Cada agente trabaja SOLO en su carpeta `/home/user/oe3/<su-nombre>/`. No modifiques `common/` (cópialo si necesitas cambiarlo).
- Escribe y mantén actualizado `/home/user/oe3/<su-nombre>/PROPUESTA.md`: idea en una frase, por qué debería funcionar (mecanismo), qué la hace nueva respecto de HMA y de Rastani y Çatay (2023) / Zachariadis et al. (2015), cómo se implementó, resultados medidos con el juez oficial y límites honestos.
- Toda afirmación de mejora debe venir con números del juez oficial, mismas instancias y mismo presupuesto de tiempo que la referencia. Nada de cifras inventadas ni de resultados que no hayas corrido.
- El banco de pruebas común (referencia HMA adaptada + script de evaluación) lo construye el agente `base` en `/home/user/oe3/base/`. Cuando exista `base/LISTO.md`, úsalo para tus comparaciones.
