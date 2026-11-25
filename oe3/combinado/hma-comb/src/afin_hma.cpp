// Inserción exacta de estaciones mediante resúmenes de segmento concatenables (agente afin).
//
// Para una lista de clientes (sin estaciones) cl = [0, c1, ..., cn, 0] se construyen los
// resúmenes de prefijo P[k] y sufijo S[k]. Cada resumen guarda, además de los campos de
// Vidal et al. (2013) para ventanas (D, TE, TL), la variación neta de carga Dl, el máximo
// prefijo H, la distancia d y W = sum_k d_k * Dl_k, con lo que la energía de la pierna
// (en unidades de "distancia restante", como HMA) es AFÍN en la carga de entrada L:
//     E(L) = (1 - beta rho) d + beta/C (W + L d).
// Una ruta con estaciones se evalúa en O(m) (m = estaciones) concatenando piernas y
// aplicando la regla de recarga "obligatoria + gratis en la holgura TE", que es exacta
// (coincide con el programa lineal del juez en 100 % de las pruebas, ver PROPUESTA.md).
// Así, cada candidato (posición, estación) para 1 estación y cada par para 2 estaciones
// se evalúa en O(1), y se obtiene la MEJOR inserción (mínimo desvío) con <= 2 estaciones
// entre las estaciones candidatas de HMA (optimal_staion[a][b][0..sr-1]).
#include "afin_hma.h"
#include "pooldump.h"
#include <algorithm>
#include <cmath>

#define AFIN_MAXLEG 10
// Margen de seguridad: la evaluación afín acepta una ruta solo si cumple con holgura, de modo
// que la comprobación final de HMA (que usa simulación directa y tolerancia PRECISION) nunca
// la rechace por diferencias de redondeo acumuladas en la concatenación.
#define TOL 1e-4
namespace {
struct P {
    int first, last;
    double d, U, Dl, H, W, D, TE, TL;
    bool ok;
};

struct Ctx {
    Data &data;
    double k0, k1, Q, g, C;
    explicit Ctx(Data &dt) : data(dt) {
        C = dt.vehicle.capacity;
        k0 = 1.0 - dt.load_beta * dt.load_rho;
        k1 = dt.load_beta / C;
        Q = dt.max_distance_reachable;
        g = dt.vehicle.consumption_rate * dt.vehicle.recharging_rate;
    }
    inline void node(int i, P &p) const {
        const Point &n = data.node[i];
        p.first = p.last = i; p.d = 0; p.W = 0; p.ok = true;
        if (n.type == 1) {
            p.U = n.delivery; p.Dl = n.pickup - n.delivery; p.H = std::max(0.0, p.Dl);
            p.D = n.s_time; p.TE = n.start; p.TL = n.end;
        } else if (n.type == 0) {
            p.U = p.Dl = p.H = 0; p.D = 0; p.TE = data.start_time; p.TL = data.end_time;
        } else {
            p.U = p.Dl = p.H = 0; p.D = 0; p.TE = 0; p.TL = 1e30;
        }
    }
    inline void cat(const P &a, const P &b, P &r) const {
        const double dxy = data.dist[a.last][b.first], txy = data.time[a.last][b.first];
        const double delta = a.D + txy;
        const double wt = std::max(b.TE - delta - a.TL, 0.0);
        r.ok = a.ok && b.ok && (a.TE + delta <= b.TL);
        r.first = a.first; r.last = b.last;
        r.W = a.W + b.W + a.Dl * (dxy + b.d);
        r.d = a.d + dxy + b.d;
        r.U = a.U + b.U;
        r.H = std::max(a.H, a.Dl + b.H);
        r.Dl = a.Dl + b.Dl;
        r.D = a.D + b.D + txy + wt;
        r.TE = std::max(b.TE - delta, a.TE) - wt;
        r.TL = std::min(b.TL - delta, a.TL);
    }
    inline double energy(const P &p, double L) const { return k0 * p.d + k1 * (p.W + L * p.d); }
    // Evalúa piernas leg[0..n-1] (leg[0] empieza en el depósito); L0 = carga inicial.
    bool eval(const P *leg, int n, double L0) const {
        double E[AFIN_MAXLEG], L = L0, rem = 0;
        for (int k = 0; k < n; k++) { E[k] = energy(leg[k], L); L += leg[k].Dl; if (k) rem += E[k]; }
        if (!leg[0].ok || E[0] > Q - TOL) return false;
        double t = leg[0].TE + leg[0].D, b = Q - E[0];
        for (int k = 1; k < n; k++) {
            const P &p = leg[k];
            if (!p.ok || E[k] > Q - TOL) return false;
            double need = std::max(0.0, E[k] - b);
            double fr = std::max(0.0, (p.TE - t) / g);
            double q = std::max(need, std::min(fr, std::min(rem - b, Q - b)));
            t += g * q;
            if (t > p.TL - TOL) return false;
            t = std::max(t, p.TE) + p.D;
            b += q - E[k]; rem -= E[k];
        }
        return true;
    }
};
}  // namespace

long afin_calls = 0, afin_found = 0, afin_fallback = 0, afin_fallback_ok = 0;

static bool afin_core(Data &data, const std::vector<int> &cl, std::vector<int> &out, double &dist_out);

bool afin_station_insertion(Data &data, const std::vector<int> &cl0, std::vector<int> &out, double &dist_out) {
    afin_calls++;
    // si la lista trae estaciones, se quitan y se reinsertan de forma óptima (<= 2)
    static thread_local std::vector<int> cl;
    cl.clear();
    for (size_t k = 0; k < cl0.size(); k++)
        if (data.node[cl0[k]].type != 2) cl.push_back(cl0[k]);
    bool ok = afin_core(data, cl, out, dist_out);
    if (ok) { afin_found++; if (data.pool_afin) pool_dump_route(out, data); } else afin_fallback++;
    return ok;
}

static bool afin_core(Data &data, const std::vector<int> &cl, std::vector<int> &out, double &dist_out) {
    const int n = int(cl.size());
    if (n < 3) return false;
    Ctx c(data);
    static thread_local std::vector<P> Pf, Sf;
    Pf.resize(n); Sf.resize(n);
    P x;
    c.node(cl[0], Pf[0]);
    for (int k = 1; k < n; k++) { c.node(cl[k], x); c.cat(Pf[k - 1], x, Pf[k]); }
    c.node(cl[n - 1], Sf[n - 1]);
    for (int k = n - 2; k >= 0; k--) { c.node(cl[k], x); c.cat(x, Sf[k + 1], Sf[k]); }
    const P &full = Pf[n - 1];
    const double L0 = full.U;
    if (!full.ok || L0 + full.H > c.C + 1e-9) return false;
    const double base = full.d;
    if (c.energy(full, L0) <= c.Q - TOL) { out = cl; dist_out = base; return true; }

    const int sr = data.station_range;
    // candidatos (arco p -> p+1, estación f) con cabeza factible: P[p] ⊕ f
    struct Cand { int p, f; double det; bool hok; P head, tail; };
    static thread_local std::vector<Cand> cand;
    cand.clear();
    P fn;
    double best = 1e30; int bp = -1, bf = -1;
    for (int p = 0; p < n - 1; p++) {
        const int a = cl[p], b = cl[p + 1];
        for (int k = 0; k < sr; k++) {
            int f = data.optimal_staion[a][b][k];
            if (f == a || f == b) continue;
            if (p == 0 && data.dist[a][f] == 0) continue;
            if (p == n - 2 && data.dist[f][b] == 0) continue;
            Cand cd; cd.p = p; cd.f = f;
            cd.det = data.dist[a][f] + data.dist[f][b] - data.dist[a][b];
            c.node(f, fn);
            c.cat(Pf[p], fn, cd.head);
            // la cabeza (depósito -> f) solo importa si f es la PRIMERA estación
            cd.hok = cd.head.ok && c.energy(cd.head, L0) <= c.Q - TOL;
            c.cat(fn, Sf[p + 1], cd.tail);
            if (!cd.tail.ok) continue;
            cand.push_back(cd);
            if (cd.hok && cd.det < best) {
                P leg[2] = {cd.head, cd.tail};
                if (c.eval(leg, 2, L0)) { best = cd.det; bp = p; bf = f; }
            }
        }
    }
    // k >= 2 estaciones: búsqueda en profundidad exacta, por profundización (k = 2, 3, ...).
    // Candidatos agrupados por arco; desde una estación se avanza la posición de la siguiente
    // mientras la pierna f ⊕ M[p+1][p'] siga cabiendo en Q y sea factible en ventanas (ambas
    // monótonas), con cota por desvío. Cada ruta completa se evalúa en O(k) con k+1 piernas.
    std::sort(cand.begin(), cand.end(), [](const Cand &u, const Cand &v) { return u.det < v.det; });
    const int nc = int(cand.size());
    static thread_local std::vector<int> bestSt;  // (p, f) de la mejor solución
    bestSt.clear();
    if (bp >= 0) { bestSt.push_back(bp); bestSt.push_back(bf); }
    if (nc >= 2) {
        // cota inferior del número de estaciones: energía sin estaciones / Q
        const double Etot = c.energy(full, L0);
        int kmin = std::max(2, int(std::ceil(Etot / c.Q - 1e-9)) - 1);
        static thread_local std::vector<std::vector<int>> byp;
        static thread_local std::vector<char> tok;
        byp.assign(n, std::vector<int>());
        tok.assign(nc, 0);
        const double mindet = cand[0].det;
        for (int j = 0; j < nc; j++) {
            tok[j] = c.energy(cand[j].tail, L0 + Pf[cand[j].p].Dl) <= c.Q - TOL;
            byp[cand[j].p].push_back(j);
        }
        static thread_local std::vector<P> M;
        M.resize(n * n);
        for (int i = 1; i < n - 1; i++) {
            c.node(cl[i], M[i * n + i]);
            for (int j = i + 1; j < n - 1; j++) { c.node(cl[j], x); c.cat(M[i * n + j - 1], x, M[i * n + j]); }
        }
        long work = 0;
        P leg[AFIN_MAXLEG];
        int pick[AFIN_MAXLEG];
        // dfs(d, j): la estación d-ésima (1..K) es cand[j]; leg[0..d-1] ya fijadas
        struct DFS {
            const Ctx &c; const std::vector<int> &cl; int n, K; double L0, Q, &best; long &work, cap;
            std::vector<Cand> &cand; std::vector<std::vector<int>> &byp; std::vector<char> &tok;
            std::vector<P> &M; std::vector<P> &Pf; double mindet; P *leg; int *pick; std::vector<int> &bestSt;
            void go(int d, int j, double det) {
                const Cand &u = cand[j];
                pick[d - 1] = j;
                if (d == K) {
                    if (!tok[j] || det >= best) return;
                    leg[d] = u.tail;
                    if (c.eval(leg, K + 1, L0)) {
                        best = det; bestSt.clear();
                        for (int t = 0; t < K; t++) { bestSt.push_back(cand[pick[t]].p); bestSt.push_back(cand[pick[t]].f); }
                    }
                    return;
                }
                P fn, s, mid; c.node(u.f, fn);
                const double Lu = L0 + Pf[u.p].Dl;
                for (int p2 = u.p + 1; p2 < n - 1; p2++) {
                    c.cat(fn, M[(u.p + 1) * n + p2], s);
                    if (!s.ok || c.energy(s, Lu) > Q - TOL) break;
                    for (int k : byp[p2]) {
                        const Cand &v = cand[k];
                        if (det + v.det + (K - d - 1) * mindet >= best) break;
                        if (++work > cap) return;
                        P f2; c.node(v.f, f2); c.cat(s, f2, mid);
                        if (!mid.ok || c.energy(mid, Lu) > Q - TOL) continue;
                        leg[d] = mid;
                        go(d + 1, k, det + v.det);
                        if (work > cap) return;
                    }
                }
            }
        };
        const int kmax = std::min(AFIN_MAXLEG - 1, data.afin_kmax);
        for (int K = kmin; K <= kmax && (K <= 2 || bestSt.empty()); K++) {
            work = 0;
            DFS dfs{c, cl, n, K, L0, c.Q, best, work, (K <= 2 ? (long)1e9 : data.afin_max3), cand, byp, tok, M, Pf, mindet, leg, pick, bestSt};
            for (int i = 0; i < nc && work <= dfs.cap; i++) {
                const Cand &u = cand[i];
                if (u.det + (K - 1) * mindet >= best) break;
                if (!u.hok) continue;
                leg[0] = u.head;
                dfs.go(1, i, u.det);
            }
        }
    }
    if (bestSt.empty()) return false;
    out.clear(); out.reserve(n + bestSt.size() / 2);
    for (int k = 0; k < n; k++) {
        out.push_back(cl[k]);
        for (size_t t = 0; t < bestSt.size(); t += 2) if (bestSt[t] == k) out.push_back(bestSt[t + 1]);
    }
    dist_out = base + best;
    return true;
}
