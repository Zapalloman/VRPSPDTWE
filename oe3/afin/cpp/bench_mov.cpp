// Banco de aceleración: evaluación de movimientos (relocate, swap, 2-opt*) entre rutas con
// estaciones, consumo según la carga. Compara evaluación completa O(n) (construir la
// lista de nodos + simulación estilo HMA) con concatenación de resúmenes (prefijo/sufijo).
// Uso: bench_mov <instancia> <solución> [beta] [volcado.txt]
#include "afin.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
using namespace afin;

struct RouteS {
    std::vector<int> nl;
    std::vector<Seg> P, S;  // P[k] = nl[0..k], S[k] = nl[k..end]
};

static void build(const Inst &I, RouteS &r) {
    int n = r.nl.size();
    r.P.resize(n); r.S.resize(n);
    node_seg(I, r.nl[0], r.P[0]);
    Seg x;
    for (int k = 1; k < n; k++) { node_seg(I, r.nl[k], x); cat(I, r.P[k - 1], x, r.P[k]); }
    node_seg(I, r.nl[n - 1], r.S[n - 1]);
    for (int k = n - 2; k >= 0; k--) { node_seg(I, r.nl[k], x); cat(I, x, r.S[k + 1], r.S[k]); }
}

int main(int argc, char **argv) {
    Inst I;
    if (!read_instance(argv[1], I)) { fprintf(stderr, "no instancia\n"); return 1; }
    if (argc > 3) { I.beta = atof(argv[3]); I.finalize(); }
    FILE *dump = argc > 4 ? fopen(argv[4], "w") : nullptr;
    auto sol = read_solution(argv[2]);
    std::vector<RouteS> R(sol.size());
    for (size_t i = 0; i < sol.size(); i++) { R[i].nl = sol[i]; build(I, R[i]); }
    int nr = R.size();
    long cnt[3] = {0, 0, 0}, feas_f[3] = {0, 0, 0}, feas_c[3] = {0, 0, 0}, mism = 0;
    double tf[3] = {0, 0, 0}, tc[3] = {0, 0, 0};
    std::vector<int> a, b; a.reserve(256); b.reserve(256);
    int REP = 1;
    for (int op = 0; op < 3; op++) {
        // pasada 1: evaluación completa; pasada 2: concatenación. Se guardan resultados.
        std::vector<char> rf, rc;
        for (int pass = 0; pass < 2; pass++) {
            auto t0 = std::chrono::high_resolution_clock::now();
            long c = 0, fe = 0; double sink = 0;
            for (int rep = 0; rep < REP; rep++)
            for (int r1 = 0; r1 < nr; r1++) for (int r2 = 0; r2 < nr; r2++) {
                if (r1 == r2) continue;
                if (op != 0 && r2 < r1) continue;  // swap y 2-opt* simétricos
                const RouteS &A = R[r1], &B = R[r2];
                int na = A.nl.size(), nb = B.nl.size();
                for (int i = (op == 2 ? 0 : 1); i < na - 1; i++) {
                    if (op != 2 && I.typ[A.nl[i]] != 1) continue;
                    for (int j = (op == 1 ? 1 : 0); j < nb - 1; j++) {
                        if (op == 1 && I.typ[B.nl[j]] != 1) continue;
                        bool ok1, ok2; double d1, d2;
                        if (pass == 0) {
                            a.clear(); b.clear();
                            if (op == 0) {        // relocate A[i] tras B[j]
                                for (int k = 0; k < na; k++) if (k != i) a.push_back(A.nl[k]);
                                for (int k = 0; k <= j; k++) b.push_back(B.nl[k]);
                                b.push_back(A.nl[i]);
                                for (int k = j + 1; k < nb; k++) b.push_back(B.nl[k]);
                            } else if (op == 1) { // swap A[i] <-> B[j]
                                a = A.nl; a[i] = B.nl[j]; b = B.nl; b[j] = A.nl[i];
                            } else {              // 2-opt*: A[0..i]+B[j+1..], B[0..j]+A[i+1..]
                                for (int k = 0; k <= i; k++) a.push_back(A.nl[k]);
                                for (int k = j + 1; k < nb; k++) a.push_back(B.nl[k]);
                                for (int k = 0; k <= j; k++) b.push_back(B.nl[k]);
                                for (int k = i + 1; k < na; k++) b.push_back(A.nl[k]);
                            }
                            ok1 = eval_full(I, a.data(), a.size(), d1);
                            ok2 = ok1 && eval_full(I, b.data(), b.size(), d2);
                            if (dump && rep == 0 && (c % 97 == 0)) {
                                for (int x : a) fprintf(dump, "%d ", x); fprintf(dump, "\n");
                                for (int x : b) fprintf(dump, "%d ", x); fprintf(dump, "\n");
                            }
                        } else {
                            Seg s1, s2, x;
                            if (op == 0) {
                                if (!cat(I, A.P[i - 1], A.S[i + 1], s1)) continue;
                                ok1 = eval_route(I, s1, d1);
                                if (ok1) {
                                    node_seg(I, A.nl[i], x);
                                    cat(I, B.P[j], x, s2); cat(I, s2, B.S[j + 1], s2);
                                    ok2 = eval_route(I, s2, d2);
                                } else ok2 = false;
                            } else if (op == 1) {
                                node_seg(I, B.nl[j], x);
                                cat(I, A.P[i - 1], x, s1); cat(I, s1, A.S[i + 1], s1);
                                ok1 = eval_route(I, s1, d1);
                                if (ok1) {
                                    node_seg(I, A.nl[i], x);
                                    cat(I, B.P[j - 1], x, s2); cat(I, s2, B.S[j + 1], s2);
                                    ok2 = eval_route(I, s2, d2);
                                } else ok2 = false;
                            } else {
                                cat(I, A.P[i], B.S[j + 1], s1);
                                ok1 = eval_route(I, s1, d1);
                                if (ok1) { cat(I, B.P[j], A.S[i + 1], s2); ok2 = eval_route(I, s2, d2); }
                                else ok2 = false;
                            }
                        }
                        bool ok = ok1 && ok2;
                        if (ok) sink += d1 + d2;
                        if (rep == 0) (pass == 0 ? rf : rc).push_back(ok);
                        fe += ok; c++;
                    }
                }
            }
            double el = std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - t0).count();
            if (pass == 0) { tf[op] = el; feas_f[op] = fe / REP; cnt[op] = c / REP; }
            else { tc[op] = el; feas_c[op] = fe / REP; }
            if (sink == 12345.678) printf(" ");
            if (pass == 0 && el < 0.3 && REP < 1000) { REP *= std::max(2, int(0.3 / std::max(el, 1e-6))); pass = -1; rf.clear(); continue; }
        }
        for (size_t k = 0; k < rf.size(); k++) mism += rf[k] != rc[k];
    }
    const char *nm[3] = {"relocate", "swap", "2opt*"};
    for (int op = 0; op < 3; op++)
        printf("%s %s movs=%ld fact_full=%ld fact_cat=%ld ns_full=%.1f ns_cat=%.1f acel=%.2f\n",
               argv[1], nm[op], cnt[op], feas_f[op], feas_c[op],
               1e9 * tf[op] / (cnt[op] * (double)REP), 1e9 * tc[op] / (cnt[op] * (double)REP), tf[op] / tc[op]);
    printf("discrepancias=%ld\n", mism);
    if (dump) fclose(dump);
    return 0;
}
