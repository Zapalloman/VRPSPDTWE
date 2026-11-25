#pragma once
#include "data.h"
#include "solution.h"
bool elim_ruta(Solution &s, Data &data);
bool reord_rutas(Solution &s, Data &data);
extern long elim_calls, elim_wins, reord_calls, reord_wins, elim_iters;
extern double elim_time, reord_time;
