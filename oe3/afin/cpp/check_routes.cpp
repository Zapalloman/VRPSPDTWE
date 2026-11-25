// Lee rutas (una por línea) e imprime "full cat" (0/1) para comparar con el juez Python.
#include "afin.h"
#include <cstdio>
#include <sstream>
#include <fstream>
#include <iostream>
using namespace afin;
int main(int argc, char **argv) {
    Inst I; read_instance(argv[1], I); I.beta = atof(argv[3]); I.finalize();
    std::ifstream f(argv[2]); std::string line;
    while (std::getline(f, line)) {
        std::stringstream ss(line); std::vector<int> r; int x; while (ss >> x) r.push_back(x);
        double d; bool a = eval_full(I, r.data(), r.size(), d);
        Seg s, y; node_seg(I, r[0], s); for (size_t k = 1; k < r.size(); k++) { node_seg(I, r[k], y); cat(I, s, y, s); }
        bool b = eval_route(I, s, d);
        printf("%d %d\n", a, b);
    }
}
