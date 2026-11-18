#!/bin/bash
# Uso: comando.sh <ruta-al-repo-HMA-en-0ebbcaa> <instancia, p. ej. c101C5> <carpeta-salida>
# Compilado con: g++ -std=c++11 -O3 (g++ 13.3, Linux x86_64)
cd "$1"
./bin/evrp-tw-spd --problem ./data/akb_instances/$2.txt --output "$3/" --pruning --time 105 --runs 10 --random_seed 2026 --g_1 20 --pop_size 9 --init rcrs --cross_repair regret --parent_selection circle --replacement one_on_one --O_1_eval --two_opt --two_opt_star --or_opt 2 --two_exchange 2 --elo 1 --related_removal --removal_lower 0.2 --removal_upper 0.4 --regret_insertion --individual_search --population_search --parallel_insertion --conservative_local_search --aggressive_local_search --station_range 1.0 --subproblem_range 1
