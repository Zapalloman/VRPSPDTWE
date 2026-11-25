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
#include <algorithm>
#include <cmath>

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
        double E[4], L = L0, rem = 0;
        for (int k = 0; k < n; k++) { E[k] = energy(leg[k], L); L += leg[k].Dl; if (k) rem += E[k]; }
        if (!leg[0].ok || E[0] > Q + 1e-7) return false;
        double t = leg[0].TE + leg[0].D, b = Q - E[0];
        for (int k = 1; k < n; k++) {
            const P &p = leg[k];
            if (!p.ok || E[k] > Q + 1e-7) return false;
            double need = std::max(0.0, E[k] - b);
            double fr = std::max(0.0, (p.TE - t) / g);
            double q = std::max(need, std::min(fr, std::min(rem - b, Q - b)));
            t += g * q;
            if (t > p.TL) return false;
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
    if (ok) afin_found++; else afin_fallback++;
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
    if (c.energy(full, L0) <= c.Q + 1e-7) { out = cl; dist_out = base; return true; }

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
            cd.hok = cd.head.ok && c.energy(cd.head, L0) <= c.Q + 1e-7;
            c.cat(fn, Sf[p + 1], cd.tail);
            if (!cd.tail.ok) continue;
            cand.push_back(cd);
            if (cd.hok && cd.det < best) {
                P leg[2] = {cd.head, cd.tail};
                if (c.eval(leg, 2, L0)) { best = cd.det; bp = p; bf = f; }
            }
        }
    }
    // dos y tres estaciones. Candidatos agrupados por arco; para una 1.ª estación u se avanza
    // la posición de la siguiente estación mientras la pierna f1 ⊕ M[p1+1][p2] siga cabiendo
    // en Q y sea factible en ventanas (ambas cosas son monótonas: al alargar la pierna solo
    // sube la energía y solo se estrecha la ventana), así los casos infactibles se descartan
    // pronto. Cada evaluación de ruta completa es O(1) (3 o 4 piernas).
    int b1 = -1, b2 = -1, c1 = -1, c2 = -1;
    std::sort(cand.begin(), cand.end(), [](const Cand &u, const Cand &v) { return u.det < v.det; });
    const int nc = int(cand.size());
    if (nc >= 2) {
        static thread_local std::vector<std::vector<int>> byp;
        static thread_local std::vector<char> tok;
        byp.assign(n, std::vector<int>());
        tok.assign(nc, 0);
        double mindet = cand[0].det;
        for (int j = 0; j < nc; j++) {
            tok[j] = c.energy(cand[j].tail, L0 + Pf[cand[j].p].Dl) <= c.Q + 1e-7;
            byp[cand[j].p].push_back(j);  // dentro de cada arco, en orden de desvío
        }
        static thread_local std::vector<P> M;
        M.resize(n * n);
        for (int i = 1; i < n - 1; i++) {
            c.node(cl[i], M[i * n + i]);
            for (int j = i + 1; j < n - 1; j++) { c.node(cl[j], x); c.cat(M[i * n + j - 1], x, M[i * n + j]); }
        }
        P f1n, f2n, f3n, s1, s2, mid1, mid2;
        long evals = 0;
        for (int pass = 2; pass <= 3; pass++) {
            if (pass == 3 && (bp >= 0 || data.afin_max3 <= 0 || nc < 3)) break;
            for (int i = 0; i < nc; i++) {
                const Cand &u = cand[i];
                if (u.det + (pass - 1) * mindet >= best) break;
                if (!u.hok) continue;
                c.node(u.f, f1n);
                const double L1 = L0 + Pf[u.p].Dl;
                for (int p2 = u.p + 1; p2 < n - 1; p2++) {
                    c.cat(f1n, M[(u.p + 1) * n + p2], s1);
                    if (!s1.ok || c.energy(s1, L1) > c.Q + 1e-7) break;
                    for (int j : byp[p2]) {
                        const Cand &v = cand[j];
                        if (u.det + v.det + (pass - 2) * mindet >= best) break;
                        c.node(v.f, f2n); c.cat(s1, f2n, mid1);
                        if (!mid1.ok || c.energy(mid1, L1) > c.Q + 1e-7) continue;
                        if (pass == 2) {
                            if (!tok[j]) continue;
                            P leg[3] = {u.head, mid1, v.tail};
                            if (c.eval(leg, 3, L0)) { best = u.det + v.det; bp = u.p; bf = u.f; b1 = v.p; b2 = v.f; }
                            continue;
                        }
                        const double L2 = L0 + Pf[v.p].Dl;
                        for (int p3 = p2 + 1; p3 < n - 1 && evals < data.afin_max3; p3++) {
                            c.cat(f2n, M[(p2 + 1) * n + p3], s2);
                            if (!s2.ok || c.energy(s2, L2) > c.Q + 1e-7) break;
                            for (int k : byp[p3]) {
                                const Cand &w = cand[k];
                                if (u.det + v.det + w.det >= best) break;
                                if (++evals > data.afin_max3) break;  // tope de trabajo (cada candidato cuenta)
                                if (!tok[k]) continue;
                                c.node(w.f, f3n); c.cat(s2, f3n, mid2);
                                if (!mid2.ok || c.energy(mid2, L2) > c.Q + 1e-7) continue;
                                P leg[4] = {u.head, mid1, mid2, w.tail};
                                if (c.eval(leg, 4, L0)) { best = u.det + v.det + w.det; bp = u.p; bf = u.f; b1 = v.p; b2 = v.f; c1 = w.p; c2 = w.f; }
                            }
                        }
                    }
                }
            }
        }
    }
    if (bp < 0) return false;
    out.clear(); out.reserve(n + 2);
    for (int k = 0; k < n; k++) {
        out.push_back(cl[k]);
        if (k == bp) out.push_back(bf);
        if (b1 >= 0 && k == b1) out.push_back(b2);
        if (c1 >= 0 && k == c1) out.push_back(c2);
    }
    dist_out = base + best;
    return true;
}
