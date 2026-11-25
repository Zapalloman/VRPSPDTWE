// POOL: volcado de rutas de HMA-LD a un archivo para el set partitioning.
#pragma once
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_set>
#include <unordered_map>
#include "data.h"
struct PoolDump {
    FILE *f = nullptr;
    std::unordered_set<uint64_t> seen;
    std::unordered_map<uint64_t, double> best_by_set; // POOL: mejor distancia por conjunto de clientes
    long n_written = 0, n_seen = 0;
    long max_lines = 3000000;
    std::vector<int> m;
};
inline PoolDump &pool_g() { static PoolDump p; return p; }
inline void pool_open(const std::string &path) { pool_g().f = fopen(path.c_str(), "a"); pool_g().seen.reserve(1 << 20); }
inline uint64_t pool_mix(uint64_t x) { x += 0x9e3779b97f4a7c15ULL; x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL; x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL; return x ^ (x >> 31); }
// Escribe la ruta (expandida con hiperarcos, en ids del problema maestro) si es nueva.
inline void pool_dump_route(const std::vector<int> &nl, Data &data)
{
    PoolDump &P = pool_g();
    if (!P.f || nl.size() < 3 || P.n_written >= P.max_lines) return;
    std::vector<int> &m = P.m;
    m.clear();
    int pre = -1;
    uint64_t hsh = 1469598103934665603ULL;
    for (int node : nl)
    {
        if (pre != -1)
            for (int sub : data.hyperarc[pre][node])
                if (sub >= 0) m.push_back(data.to_master[sub]);
        m.push_back(data.to_master[node]);
        pre = node;
    }
    for (int x : m) { hsh ^= (uint64_t)(x + 1); hsh *= 1099511628211ULL; }
    P.n_seen++;
    if (!P.seen.insert(hsh).second) return;
    // deduplicación por conjunto de clientes: solo se escribe si el conjunto es nuevo
    // o si la secuencia es más corta que la mejor ya escrita
    uint64_t hs = 0; double d = 0.0;
    for (size_t k = 0; k < nl.size(); k++) {
        if (data.node[nl[k]].type == 1) hs += pool_mix((uint64_t)data.to_master[nl[k]]);
        if (k > 0) d += data.dist[nl[k-1]][nl[k]];
    }
    auto it = P.best_by_set.find(hs);
    if (it != P.best_by_set.end() && d >= it->second - 1e-9) return;
    P.best_by_set[hs] = d;
    for (size_t k = 0; k < m.size(); k++)
        fprintf(P.f, k + 1 < m.size() ? "%d " : "%d\n", m[k]);
    P.n_written++;
}
