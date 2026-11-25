// HMA-RX: decisión exacta de estaciones y recarga (ver frvcp.h).
#include "frvcp.h"
#include <algorithm>
#include <cmath>

long long rx_calls_fixed = 0, rx_calls_dp = 0, rx_rescued_fixed = 0, rx_rescued_dp = 0;

static const double TB = 1e-7;   // tolerancia de batería (el juez exige >= -1e-5)
static const double TT = 1e-7;   // tolerancia de ventanas (el juez usa 1e-6)
static const int K_PAIR = 6;     // estaciones candidatas para pares consecutivos en un tramo

struct St { double a, b, m; };

static inline bool rx_arc(St &s, int i, int j, double load, Data &data, double hg)
{
    double e = data.edist(i, j, load);
    if (s.m < e - TB) return false;
    if (s.b < e) { s.a += hg * (e - s.b); s.b = e; }
    s.a += data.time[i][j];
    s.b = std::max(0.0, s.b - e);
    s.m -= e;
    return true;
}

static inline bool rx_customer(St &s, int c, Data &data, double hg)
{
    const Point &p = data.node[c];
    if (s.a > p.end + TT) return false;
    s.m = std::min(s.m, s.b + (p.end - s.a) / hg);
    if (s.a < p.start) { s.b = std::min(s.m, s.b + (p.start - s.a) / hg); s.a = p.start; }
    s.a += p.s_time;
    return true;
}

static bool load_ok(const std::vector<int> &nl, Data &data)
{
    double load = 0.0, C = data.vehicle.capacity;
    for (int v : nl) load += data.node[v].delivery;
    if (load > C + 1e-9) return false;
    for (size_t k = 1; k < nl.size(); k++) {
        load = load - data.node[nl[k]].delivery + data.node[nl[k]].pickup;
        if (load > C + 1e-9) return false;
    }
    return true;
}

static bool tw_ok_nobattery(const std::vector<int> &nl, Data &data)
{
    double t = data.start_time;
    int len = nl.size();
    for (int k = 1; k < len; k++) {
        t += data.time[nl[k - 1]][nl[k]];
        if (data.node[nl[k]].type == 2) continue;
        if (t > data.node[nl[k]].end + TT) return false;
        t = std::max(t, data.node[nl[k]].start) + data.node[nl[k]].s_time;
    }
    return true;
}

int rx_fixed(const std::vector<int> &nl, Data &data)
{
    rx_calls_fixed++;
    int len = nl.size();
    if (len <= 2) return 1;
    if (!load_ok(nl, data)) return 2;
    double hg = data.vehicle.consumption_rate * data.vehicle.recharging_rate;
    double load = 0.0;
    for (int v : nl) load += data.node[v].delivery;
    St s{data.start_time, data.max_distance_reachable, data.max_distance_reachable};
    for (int k = 0; k < len - 1; k++) {
        int i = nl[k], j = nl[k + 1];
        if (k > 0) load = load - data.node[i].delivery + data.node[i].pickup;
        if (!rx_arc(s, i, j, load, data, hg)) return tw_ok_nobattery(nl, data) ? 4 : 3;
        if (k + 1 == len - 1) {
            if (s.a > data.node[j].end + TT) return tw_ok_nobattery(nl, data) ? 4 : 3;
            return 1;
        }
        if (data.node[j].type == 2) s.m = data.max_distance_reachable;
        else if (!rx_customer(s, j, data, hg)) return tw_ok_nobattery(nl, data) ? 4 : 3;
    }
    return 1;
}

struct Lab { double d, a, b, m; int prev; int f1, f2; };

static inline bool dominates(const Lab &x, const Lab &y, double hg)
{
    if (x.d > y.d + 1e-9 || x.a > y.a + 1e-9 || x.m < y.m - 1e-9) return false;
    return std::min(x.m, x.b + (y.a - x.a) / hg) >= y.b - 1e-9;
}

int rx_dp(const std::vector<int> &nl, Data &data, bool keep_existing,
          std::vector<int> &out, double &dist)
{
    rx_calls_dp++;
    // anclas: clientes y depósitos (y estaciones existentes si keep_existing)
    std::vector<int> anc;
    anc.reserve(nl.size());
    for (size_t k = 0; k < nl.size(); k++) {
        int v = nl[k];
        if (data.node[v].type == 2 && !keep_existing) continue;
        if (!anc.empty() && anc.back() == v) continue;
        anc.push_back(v);
    }
    int na = anc.size();
    if (na <= 2) { out = anc; dist = 0.0; if (na == 2) dist = data.dist[anc[0]][anc[1]]; return 1; }
    if (!load_ok(anc, data)) return 2;
    double hg = data.vehicle.consumption_rate * data.vehicle.recharging_rate;
    double Q = data.max_distance_reachable;
    int S0 = data.customer_num + 1, S1 = data.customer_num + data.station_num; // ids de estaciones
    // carga en cada tramo
    std::vector<double> legload(na - 1);
    double load = 0.0;
    for (int v : anc) load += data.node[v].delivery;
    for (int k = 0; k < na - 1; k++) {
        if (k > 0) load = load - data.node[anc[k]].delivery + data.node[anc[k]].pickup;
        legload[k] = load;
    }
    std::vector<double> rem(na, 0.0);
    for (int k = na - 2; k >= 0; k--) rem[k] = rem[k + 1] + data.dist[anc[k]][anc[k + 1]];

    std::vector<Lab> pool;
    pool.reserve(4096);
    std::vector<int> cur, nxt;
    pool.push_back(Lab{0.0, data.start_time, Q, Q, -1, -1, -1});
    cur.push_back(0);
    double ub = INFINITY;
    for (int k = 0; k < na - 1; k++) {
        int u = anc[k], v = anc[k + 1];
        double L = legload[k];
        bool last = (k + 1 == na - 1);
        nxt.clear();
        // candidatos del tramo
        int npair = std::min(K_PAIR, data.station_num);
        for (int li : cur) {
            const Lab base = pool[li];
            St s0{base.a, base.b, base.m};
            // 0: directo, 1: una estación, 2: dos estaciones
            for (int mode = 0; mode < 3; mode++) {
                int n1 = (mode == 0) ? 1 : (S1 - S0 + 1);
                if (mode == 2) n1 = npair;
                for (int x = 0; x < n1; x++) {
                    int f1 = -1;
                    if (mode == 1) f1 = S0 + x;
                    else if (mode == 2) f1 = data.optimal_staion[u][v][x];
                    if (mode >= 1 && (f1 == u || f1 == v)) continue;
                    int n2 = (mode == 2) ? npair : 1;
                    for (int y = 0; y < n2; y++) {
                        int f2 = -1;
                        if (mode == 2) { f2 = data.optimal_staion[u][v][y]; if (f2 == f1 || f2 == v) continue; }
                        double dd;
                        if (mode == 0) dd = data.dist[u][v];
                        else if (mode == 1) dd = data.dist[u][f1] + data.dist[f1][v];
                        else dd = data.dist[u][f1] + data.dist[f1][f2] + data.dist[f2][v];
                        double nd = base.d + dd;
                        if (nd + rem[k + 1] > ub + 1e-9) continue;
                        St s = s0;
                        bool ok;
                        if (mode == 0) ok = rx_arc(s, u, v, L, data, hg);
                        else if (mode == 1) {
                            ok = rx_arc(s, u, f1, L, data, hg);
                            if (ok) { s.m = Q; ok = rx_arc(s, f1, v, L, data, hg); }
                        } else {
                            ok = rx_arc(s, u, f1, L, data, hg);
                            if (ok) { s.m = Q; ok = rx_arc(s, f1, f2, L, data, hg); }
                            if (ok) { s.m = Q; ok = rx_arc(s, f2, v, L, data, hg); }
                        }
                        if (!ok) continue;
                        if (last) { if (s.a > data.node[v].end + TT) continue; }
                        else if (data.node[v].type == 2) s.m = Q;
                        else if (!rx_customer(s, v, data, hg)) continue;
                        Lab nl2{nd, s.a, s.b, s.m, li, f1, f2};
                        if (last) { if (nd < ub) ub = nd; }
                        bool dom = false;
                        for (int q : nxt) if (dominates(pool[q], nl2, hg)) { dom = true; break; }
                        if (dom) continue;
                        size_t w = 0;
                        for (size_t r = 0; r < nxt.size(); r++)
                            if (!dominates(nl2, pool[nxt[r]], hg)) nxt[w++] = nxt[r];
                        nxt.resize(w);
                        pool.push_back(nl2);
                        nxt.push_back(int(pool.size()) - 1);
                    }
                }
            }
        }
        if (nxt.empty()) return tw_ok_nobattery(anc, data) ? 4 : 3;
        cur.swap(nxt);
    }
    int best = cur[0];
    for (int q : cur) if (pool[q].d < pool[best].d) best = q;
    dist = pool[best].d;
    // reconstrucción
    std::vector<int> chain;
    for (int q = best; pool[q].prev != -1; q = pool[q].prev) chain.push_back(q);
    std::reverse(chain.begin(), chain.end());
    out.clear();
    out.push_back(anc[0]);
    for (int k = 0; k < (int)chain.size(); k++) {
        const Lab &l = pool[chain[k]];
        if (l.f1 >= 0) out.push_back(l.f1);
        if (l.f2 >= 0) out.push_back(l.f2);
        out.push_back(anc[k + 1]);
    }
    return 1;
}
