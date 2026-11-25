#pragma once
#include "data.h"
#include <vector>
// Inserción exacta (mínimo desvío) de 0, 1 o 2 estaciones en una lista de clientes,
// evaluando cada candidato en O(1) con resúmenes concatenables afines en la carga.
bool afin_station_insertion(Data &data, const std::vector<int> &cl, std::vector<int> &out, double &dist_out);
extern long afin_calls, afin_found, afin_fallback, afin_fallback_ok;
