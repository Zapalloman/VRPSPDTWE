// Movimientos conscientes de la carga (agente combinado).
//
// (a) elim_ruta: eliminación dirigida de un vehículo. Se ordenan las rutas por "facilidad de
//     eliminación" (menos clientes; a igualdad, menor carga transportada) y, para cada una de las
//     `data.elim` primeras, se expulsan sus clientes y se reinsertan en las demás rutas con
//     inserción de arrepentimiento (regret-2). Cada inserción candidata se evalúa con la
//     factibilidad EXACTA (ventanas, capacidad y batería con consumo según la carga, con
//     re-inserción óptima de estaciones) mediante los resúmenes afines (afin_station_insertion):
//     el costo de insertar incluye el desvío a estaciones que provoca la carga extra.
//     Si todos los clientes caben, la solución tiene K-1 rutas y reemplaza a la vigente si es
//     más barata.
// (b) reord_rutas: reordenamiento intra-ruta evaluado con el costo REAL (distancia + estaciones).
//     HMA evalúa sus movimientos intra-ruta en el espacio relajado (sin batería), de modo que
//     nunca acepta un reordenamiento que alarga un poco la secuencia de clientes pero reduce la
//     energía (p. ej. adelantar una entrega grande o atrasar una recogida grande) y con ello
//     ahorra el desvío a una estación. Aquí cada reubicación intra-ruta de un cliente se evalúa
//     con afin_station_insertion (estaciones re-decididas de forma óptima) y se acepta la
//     primera que mejora el costo real.
#include "mov_carga.h"
#include "afin_hma.h"
#include <algorithm>
#include <cmath>
#include <vector>
#include <ctime>

long elim_calls = 0, elim_wins = 0, reord_calls = 0, reord_wins = 0, elim_iters = 0;
double elim_time = 0, reord_time = 0;

static void customers_of(Data &data, const std::vector<int> &nl, std::vector<int> &cl)
{
    cl.clear();
    for (int x : nl) if (data.node[x].type != 2) cl.push_back(x);
}

static void set_route(Data &data, Route &r, const std::vector<int> &nl)
{
    r.node_list = nl;
    r.customer_list.clear();
    for (int x : nl) if (data.node[x].type != 2) r.customer_list.push_back(x);
    r.update(data);
    r.total_cost = r.cal_cost(data);
}

// mejor posición para insertar c en la lista de clientes cl (depósitos en los extremos)
static bool best_pos(Data &data, const std::vector<int> &cl, int c, double cur_d,
                     double &delta, std::vector<int> &best_out, double &best_d)
{
    static thread_local std::vector<int> tmp, out;
    bool found = false;
    delta = 1e30;
    const int n = int(cl.size());
    for (int p = 1; p < n; p++)
    {
        // poda barata por ventana: no se puede llegar a c desde cl[p-1] a tiempo
        const Point &a = data.node[cl[p - 1]];
        if (a.type == 1 && a.start + a.s_time + data.time[cl[p - 1]][c] > data.node[c].end) continue;
        // poda barata por distancia: el desvío sin estaciones ya es peor que el mejor
        double dd0 = data.dist[cl[p - 1]][c] + data.dist[c][cl[p]] - data.dist[cl[p - 1]][cl[p]];
        if (found && dd0 >= delta) continue;
        tmp.assign(cl.begin(), cl.begin() + p);
        tmp.push_back(c);
        tmp.insert(tmp.end(), cl.begin() + p, cl.end());
        double d;
        if (!afin_station_insertion(data, tmp, out, d)) continue;
        if (d - cur_d < delta) { delta = d - cur_d; best_out = out; best_d = d; found = true; }
    }
    return found;
}

// Eliminación con "pool de expulsión" (inspirada en Nagata y Bräysy 2009, simplificada):
// los clientes de la ruta elegida entran a una pila; cada uno se inserta en su mejor posición
// factible (evaluación exacta afín); si no cabe en ninguna ruta, se inserta expulsando UN cliente
// w de alguna ruta (el de menor contador de expulsiones p[w], luego menor desvío), y w entra a la
// pila. Se detiene al vaciar la pila (éxito: K-1 rutas) o al agotar data.elim_t segundos de CPU.
bool elim_ruta(Solution &s, Data &data)
{
    if (data.elim <= 0 || s.len() < 2) return false;
    elim_calls++;
    const clock_t t0 = std::clock();
    const clock_t tmax = clock_t(data.elim_t * CLOCKS_PER_SEC);
    const int K = s.len();
    std::vector<std::vector<int>> cls(K);
    std::vector<double> dist(K);
    std::vector<std::pair<double, int>> order;
    for (int i = 0; i < K; i++)
    {
        customers_of(data, s.get(i).node_list, cls[i]);
        dist[i] = s.get(i).self.dist;
        int nc = 0; double load = 0;
        for (int x : cls[i]) if (data.node[x].type == 1) { nc++; load += data.node[x].delivery + data.node[x].pickup; }
        if (nc == 0) continue;
        order.push_back({nc + load / (2.0 * data.vehicle.capacity + 1e-9), i});
    }
    if (order.empty()) return false;
    std::sort(order.begin(), order.end());
    const int tries = std::min(int(order.size()), data.elim);
    const int R = order[(elim_calls - 1) % tries].second;
    std::vector<std::vector<int>> cl = cls, nl(K);
    std::vector<double> d = dist;
    for (int i = 0; i < K; i++) nl[i] = s.get(i).node_list;
    std::vector<int> EP;
    for (int x : cls[R]) if (data.node[x].type == 1) EP.push_back(x);
    const int nu0 = int(EP.size());
    std::vector<int> pen(data.node_num, 1);
    std::vector<int> o, bo, tmp;
    long iters = 0;
    while (!EP.empty())
    {
        if (std::clock() - t0 > tmax) break;
        iters++;
        int u = EP.back();
        // 1) inserción directa
        double bdel = 1e30, bdd = 0; int bj = -1;
        for (int j = 0; j < K; j++)
        {
            if (j == R) continue;
            double dl, dd;
            if (best_pos(data, cl[j], u, d[j], dl, o, dd) && dl < bdel) { bdel = dl; bdd = dd; bj = j; bo = o; }
        }
        if (bj >= 0)
        {
            EP.pop_back();
            nl[bj] = bo; d[bj] = bdd; customers_of(data, nl[bj], cl[bj]);
            continue;
        }
        // 2) inserción con una expulsión
        int bw = -1, bpen = 1 << 30; bj = -1; bdel = 1e30;
        for (int j = 0; j < K; j++)
        {
            if (j == R) continue;
            const int n = int(cl[j].size());
            for (int k = 1; k < n - 1; k++)
            {
                int w = cl[j][k];
                if (data.node[w].type != 1 || pen[w] > bpen) continue;
                tmp.assign(cl[j].begin(), cl[j].begin() + k);
                tmp.insert(tmp.end(), cl[j].begin() + k + 1, cl[j].end());
                double dl, dd;
                if (!best_pos(data, tmp, u, d[j], dl, o, dd)) continue;
                if (pen[w] < bpen || dl < bdel) { bpen = pen[w]; bdel = dl; bdd = dd; bj = j; bw = w; bo = o; }
            }
            if (std::clock() - t0 > tmax) break;
        }
        if (bj < 0) break;  // ni con una expulsión: se abandona
        EP.pop_back();
        pen[u]++;
        nl[bj] = bo; d[bj] = bdd; customers_of(data, nl[bj], cl[bj]);
        EP.push_back(bw);
    }
    elim_iters += iters;
    elim_time += double(std::clock() - t0) / CLOCKS_PER_SEC;
    if (!EP.empty()) return false;
    double newcost = 0;
    for (int i = 0; i < K; i++) if (i != R) newcost += data.vehicle.d_cost + d[i] * data.vehicle.unit_cost;
    if (newcost - s.cost >= -PRECISION) return false;
    Solution ns(data);
    for (int i = 0; i < K; i++)
    {
        if (i == R) continue;
        Route r = s.get(i);
        set_route(data, r, nl[i]);
        if (!r.isempty()) ns.append(r);
    }
    ns.cal_cost(data);
    if (ns.cost - s.cost >= -PRECISION) return false;
    printf("ELIM: ruta %d (%d clientes) eliminada en %ld iteraciones: %.2f -> %.2f\n", R, nu0, iters, s.cost, ns.cost);
    s = ns;
    elim_wins++;
    return true;
}

bool reord_rutas(Solution &s, Data &data)
{
    if (data.reord <= 0) return false;
    reord_calls++;
    const clock_t t0 = std::clock();
    bool any = false;
    std::vector<int> cl, tmp, out, best;
    for (int i = 0; i < s.len(); i++)
    {
        Route &r = s.get(i);
        // solo rutas con estaciones: en las demás el costo real es la distancia relajada
        bool hasf = false;
        for (int x : r.node_list) if (data.node[x].type == 2) { hasf = true; break; }
        if (!hasf) continue;
        double cur = r.self.dist;
        bool improved = true;
        int rounds = 0;
        while (improved && rounds++ < 5)
        {
            improved = false;
            customers_of(data, r.node_list, cl);
            const int n = int(cl.size());
            for (int a = 1; a < n - 1 && !improved; a++)
            {
                for (int b = 1; b < n - 1 && !improved; b++)
                {
                    if (b == a) continue;
                    // reubicar cl[a] para que quede en la posición b
                    tmp = cl;
                    int c = tmp[a];
                    tmp.erase(tmp.begin() + a);
                    tmp.insert(tmp.begin() + b, c);
                    double d;
                    if (!afin_station_insertion(data, tmp, out, d)) continue;
                    if (d < cur - 1e-6) { cur = d; best = out; improved = true; }
                }
            }
            if (improved) { set_route(data, r, best); any = true; reord_wins++; }
        }
    }
    if (any) s.cal_cost(data);
    reord_time += double(std::clock() - t0) / CLOCKS_PER_SEC;
    return any;
}
