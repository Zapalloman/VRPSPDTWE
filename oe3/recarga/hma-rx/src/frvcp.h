#pragma once
// HMA-RX: decisión exacta de estaciones y recarga para una secuencia fija.
// Ver /home/user/oe3/recarga/frvcp.py y PROPUESTA.md para la derivación.
//
// Estado (a, b, m): F(A) = min(m, b + (A - a)/(h g)) es la batería máxima (en unidades
// de "distancia restante" RD, como en HMA) con la que el vehículo puede estar listo
// en el instante A >= a. La familia es cerrada bajo arcos, clientes y estaciones.
#include <vector>
#include "data.h"

// Factibilidad exacta O(n) de una lista de nodos con estaciones fijas
// (equivale al programa lineal del juez). Devuelve 1 factible, 2 capacidad,
// 3 ventanas (aun con batería infinita), 4 batería.
int rx_fixed(const std::vector<int> &nl, Data &data);

// Algoritmo de etiquetas: elige estaciones (0..2 por tramo) y recarga para la
// lista dada. keep_existing = true mantiene las estaciones ya presentes y solo
// inserta otras (resultado expresable como inserciones); false las quita y las
// re-decide todas. Devuelve 1 (out = lista óptima, dist = distancia) o 2/3/4.
int rx_dp(const std::vector<int> &nl, Data &data, bool keep_existing,
          std::vector<int> &out, double &dist);

// Estadísticas (para el informe).
extern long long rx_calls_fixed, rx_calls_dp, rx_rescued_fixed, rx_rescued_dp;
