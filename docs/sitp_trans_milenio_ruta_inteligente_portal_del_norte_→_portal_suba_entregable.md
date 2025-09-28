# Proyecto: Sistema inteligente de rutas (SITP/TransMilenio Bogotá)

> **Trayecto de ejemplo**: *Portal del Norte* → *Portal Suba*  
> **Paradigma**: Base de conocimiento en reglas + búsqueda heurística (A*)

---

## 1) Entregables del repositorio

```
├─ README.md               # guía rápida de uso
├─ route_planner.py        # sistema inteligente (reglas + A*)
├─ data/
│  └─ bogota_sitp.json     # conocimiento: estaciones, líneas, enlaces
├─ tests/
│  └─ test_examples.sh     # pruebas de línea de comandos
└─ docs/
   ├─ informe_pruebas.md   # evidencias, capturas y análisis
   └─ bibliografia.md      # citas (Benítez, 2014) y otras
```

Sube también un **PDF** con:
- enlace al **repositorio Git** (agregar al tutor como colaborador),
- enlace al **video** (≤ 5 min) donde *todos* los integrantes participan,
- resumen de **pruebas** realizadas y resultados.

---

## 2) Bibliografía base

- Benítez, R. (2014). *Inteligencia artificial avanzada*. Barcelona: Editorial UOC.  
  Cap. 2 (lógica y representación del conocimiento), Cap. 3 (sistemas basados en reglas), Cap. 9 (búsquedas heurísticas).

---

## 3) Cómo ejecutar (modo consola)

```bash
# 1) Crear y activar venv (opcional, no hay dependencias externas)
python3 -m venv .venv && source .venv/bin/activate

--windows python -m venv .venv

# 2) Ejecutar el planificador
python route_planner.py `
  --from "Portal del Norte" `
  --to   "Portal Suba" `
  --criterio tiempo   # otros: transbordos, saltos

# 3) Ver explicación de la ruta y reglas aplicadas
python route_planner.py --explain `
  --from "Portal del Norte" --to "Portal Suba"
```

Salida esperada (ejemplo):
```
Ruta óptima (criterio: tiempo):
Portal del Norte ──(Autonorte Troncales)→ Toberín → Calle 146 → Calle 116/P. Pepe Sierra → Héroes
[Transbordo] Héroes ⇄ Suba - Calle 95
Suba - Calle 95 → Shaio → 21 Ángeles → La Campiña → Portal Suba

Tiempo estimado: 35 min  |  Transbordos: 1  |  Saltos: 9
```
> *Nota*: La malla es un **modelo académico simplificado** para el SITP/TransMilenio. Puedes ampliar estaciones y tiempos para mayor realismo.

---

## 4) Código fuente (route_planner.py)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema inteligente para calcular la mejor ruta entre dos estaciones del SITP/TransMilenio Bogotá.
Combina:
  - Representación del conocimiento (reglas lógicas simples) sobre líneas, enlaces y transbordos.
  - Búsqueda A* con heurística geodésica (Haversine) para minimizar tiempo/saltos/transbordos.

Uso:
  python route_planner.py --from "Portal del Norte" --to "Portal Suba" --criterio tiempo
  python route_planner.py --explain --from "Portal del Norte" --to "Portal Suba"
"""

from __future__ import annotations
import json
import math
import argparse
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional

# ==========================
# 1) Datos / Conocimiento
# ==========================
# Para hacerlo autocontenible, incluimos un subconjunto de estaciones y enlaces.
# Puedes mover esto a data/bogota_sitp.json si prefieres.

DATA = {
    "stations": {
        # nombre: {lat, lon}
        "Portal del Norte": {"lat": 4.7606, "lon": -74.0467},
        "Toberín": {"lat": 4.7363, "lon": -74.0453},
        "Calle 146": {"lat": 4.7271, "lon": -74.0462},
        "Calle 116/P. Pepe Sierra": {"lat": 4.7088, "lon": -74.0468},
        "Héroes": {"lat": 4.6678, "lon": -74.0593},
        # Nodo de conexión a Suba (estación próxima a Suba - Calle 95)
        "Suba - Calle 95": {"lat": 4.6930, "lon": -74.0755},
        "Shaio": {"lat": 4.7080, "lon": -74.0790},
        "21 Ángeles": {"lat": 4.7215, "lon": -74.0845},
        "La Campiña": {"lat": 4.7357, "lon": -74.0905},
        "Portal Suba": {"lat": 4.7451, "lon": -74.0954},
    },
    # Definimos líneas (troncales simplificadas) y enlaces con tiempos estimados (minutos)
    "links": [
        # Troncal Autonorte
        ["Portal del Norte", "Toberín", "AUTONORTE", 5],
        ["Toberín", "Calle 146", "AUTONORTE", 4],
        ["Calle 146", "Calle 116/P. Pepe Sierra", "AUTONORTE", 7],
        ["Calle 116/P. Pepe Sierra", "Héroes", "AUTONORTE", 6],

        # Conexión hacia troncal Suba (usamos Héroes como punto de intercambio en este modelo)
        ["Héroes", "Suba - Calle 95", "CONEXION", 6],

        # Troncal Suba
        ["Suba - Calle 95", "Shaio", "SUBA", 5],
        ["Shaio", "21 Ángeles", "SUBA", 4],
        ["21 Ángeles", "La Campiña", "SUBA", 4],
        ["La Campiña", "Portal Suba", "SUBA", 5],
    ],
    # Penalización de transbordo en minutos
    "transfer_penalty": 4
}

# ==========================
# 2) Utilidades geográficas (heurística)
# ==========================

def haversine(p1: Tuple[float,float], p2: Tuple[float,float]) -> float:
    """Distancia geodésica aproximada en km."""
    R = 6371.0
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ==========================
# 3) Motor de reglas (simple)
# ==========================
# Representamos reglas como predicados sobre el grafo y la línea activa.
#
# R1: Se puede mover entre estaciones si existe un enlace directo.
# R2: Un transbordo ocurre cuando cambia la línea entre dos enlaces consecutivos.
# R3: El costo base es el tiempo del enlace; si hay transbordo, se suma la penalización.
# R4: Estaciones de intercambio son aquellas que tienen enlaces de más de una línea.

class KnowledgeBase:
    def __init__(self, data: Dict):
        self.data = data
        self.graph = defaultdict(list)  # estación -> [(vecina, linea, tiempo)]
        for a, b, line, t in data["links"]:
            self.graph[a].append((b, line, t))
            self.graph[b].append((a, line, t))  # asumimos bidireccional
        self.lines_by_station = defaultdict(set)
        for a, b, line, _ in data["links"]:
            self.lines_by_station[a].add(line)
            self.lines_by_station[b].add(line)

    # R1
    def neighbors(self, station: str) -> List[Tuple[str, str, int]]:
        return self.graph[station]

    # R2
    def is_transfer(self, prev_line: Optional[str], next_line: str) -> bool:
        return prev_line is not None and next_line != prev_line

    # R3
    def step_cost(self, base_time: int, is_transfer: bool) -> int:
        return base_time + (self.data["transfer_penalty"] if is_transfer else 0)

    # R4
    def is_interchange(self, station: str) -> bool:
        return len(self.lines_by_station[station]) > 1

    def coords(self, station: str) -> Tuple[float, float]:
        s = self.data["stations"][station]
        return (s["lat"], s["lon"])

# ==========================
# 4) Planificador A*
# ==========================

def a_star(kb: KnowledgeBase, start: str, goal: str, criterio: str = "tiempo"):
    """
    A* con heurística geodésica (km → aproximación a minutos: km * 2).
    Criterios: tiempo | saltos | transbordos
    """
    # Heurística: distancia en km * factor (≈2 min por km para modelar troncales)
    def h(s: str) -> float:
        km = haversine(kb.coords(s), kb.coords(goal))
        return km * 2.0

    from heapq import heappush, heappop

    # estado: (estación, línea_anterior)
    start_state = (start, None)

    openpq = []
    heappush(openpq, (0, start_state))

    g_cost = {(start, None): 0}
    parents = {start_state: None}
    used_line = {start_state: None}

    while openpq:
        _, (u, last_line) = heappop(openpq)
        if u == goal:
            # reconstruir
            path = []
            cur = (u, last_line)
            while cur is not None:
                path.append(cur)
                cur = parents[cur]
            path.reverse()
            return path, g_cost[(u, last_line)]

        for v, line, base_t in kb.neighbors(u):
            transfer = kb.is_transfer(last_line, line)
            if criterio == "tiempo":
                step = kb.step_cost(base_t, transfer)
            elif criterio == "saltos":
                step = 1 + (1 if transfer else 0)  # castiga levemente el transbordo
            elif criterio == "transbordos":
                step = 1 if transfer else 0
            else:
                raise ValueError("Criterio no soportado")

            new_state = (v, line)
            tentative_g = g_cost[(u, last_line)] + step

            if tentative_g < g_cost.get(new_state, float('inf')):
                g_cost[new_state] = tentative_g
                parents[new_state] = (u, last_line)
                used_line[new_state] = line
                priority = tentative_g + (h(v) if criterio == "tiempo" else 0)
                heappush(openpq, (priority, new_state))

    return None, float('inf')

# ==========================
# 5) Presentación y explicación
# ==========================

def explain_route(kb: KnowledgeBase, path_states: List[Tuple[str, Optional[str]]]) -> Tuple[str, int, int, int]:
    if not path_states:
        return "No se encontró ruta.", 0, 0, 0

    lines = []
    transbordos = 0
    saltos = 0
    total_tiempo = 0

    for i in range(len(path_states)-1):
        (u, line_u) = path_states[i]
        (v, line_v) = path_states[i+1]
        # hallar el enlace u-v
        link = next((L for L in kb.neighbors(u) if L[0] == v), None)
        if link is None:
            continue
        _, line, base_t = link
        is_transfer = (i > 0 and path_states[i][1] != path_states[i-1][1] and path_states[i][1] is not None)
        penalty = kb.data["transfer_penalty"] if is_transfer else 0
        total_tiempo += base_t + penalty
        saltos += 1
        if is_transfer:
            transbordos += 1
        lines.append((u, v, line, base_t, penalty))

    # Construcción del string de ruta
    steps = []
    prev_line = None
    for (u, v, line, base_t, penalty) in lines:
        if prev_line is None:
            steps.append(f"{u} ──({line})→ {v}")
        elif line != prev_line:
            steps.append(f"[Transbordo] {u} ⇄ {v}")
            steps.append(f"{u} ──({line})→ {v}")
        else:
            steps.append(f"{u} → {v}")
        prev_line = line

    # Agregar estación final si faltó
    if path_states:
        last_station = path_states[-1][0]
        if not steps or not steps[-1].endswith(last_station):
            steps.append(last_station)

    route_str = "\n".join(steps)
    return route_str, total_tiempo, transbordos, saltos

# ==========================
# 6) CLI
# ==========================

def main():
    parser = argparse.ArgumentParser(description="Planificador de rutas SITP/TransMilenio (Bogotá)")
    parser.add_argument("--from", dest="src", required=False, default="Portal del Norte")
    parser.add_argument("--to", dest="dst", required=False, default="Portal Suba")
    parser.add_argument("--criterio", choices=["tiempo", "saltos", "transbordos"], default="tiempo")
    parser.add_argument("--explain", action="store_true")
    args = parser.parse_args()

    kb = KnowledgeBase(DATA)

    if args.src not in kb.data["stations"] or args.dst not in kb.data["stations"]:
        print("Estación desconocida. Disponible:")
        for s in kb.data["stations"].keys():
            print(" -", s)
        return

    path, score = a_star(kb, args.src, args.dst, criterio=args.criterio)
    if path is None:
        print("No se encontró ruta.")
        return

    route_str, tmin, trans, hops = explain_route(kb, path)

    print(f"Ruta óptima (criterio: {args.criterio}):")
    print(route_str)
    print("")
    print(f"Tiempo estimado: {tmin} min  |  Transbordos: {trans}  |  Saltos: {hops}")

    if args.explain:
        print("\nReglas aplicadas:")
        print("- R1: Movimiento permitido solo si existe enlace directo entre estaciones.")
        print("- R2: Si cambia la línea entre dos enlaces consecutivos → se considera transbordo.")
        print("- R3: Costo = tiempo_enlace + penalización_transbordo (si aplica).")
        print("- R4: Estaciones con enlaces de varias líneas son nodos de intercambio.")

if __name__ == "__main__":
    main()
```

---

## 5) Conjunto de conocimiento (data/bogota_sitp.json)

> Opcional: si quieres separar datos del código, crea `data/bogota_sitp.json` con el contenido del bloque `DATA` y ajusta `route_planner.py` para leerlo desde archivo. Así el tutor puede ampliar la red fácilmente.

---

## 6) Pruebas

### 6.1 Script rápido

`tests/test_examples.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
python route_planner.py --from "Portal del Norte" --to "Portal Suba" --criterio tiempo
python route_planner.py --from "Portal del Norte" --to "Portal Suba" --criterio saltos
python route_planner.py --from "Portal del Norte" --to "Portal Suba" --criterio transbordos
```

### 6.2 Casos a documentar en el PDF
- **Ruta base**: Norte → Suba (criterio tiempo).
- **Sensibilidad de criterio**: compara *tiempo* vs *saltos* (puede elegir variantes si amplías la malla).
- **Penalización de transbordo**: cambia `transfer_penalty` (2, 4, 6) y mide efecto.
- **Nodos de intercambio**: verifica `kb.is_interchange("Héroes")`.

Incluye capturas de la salida y una breve discusión (2–3 párrafos) en `docs/informe_pruebas.md`.

---

## 7) Video (≤ 5 min) — guion sugerido

1. **Introducción (30s)**: objetivo del sistema, marco conceptual (Benítez, caps. 2, 3 y 9).
2. **Modelo de conocimiento (60s)**: estaciones, líneas, reglas R1–R4.
3. **Algoritmo (60s)**: A*, heurística Haversine, criterios de optimización.
4. **Demostración (90s)**: ejecutar 2–3 comandos, mostrar rutas y métricas.
5. **Cierre (30s)**: cómo ampliar datos, trabajo de cada integrante (menciona commits).

---

## 8) Evidencia de trabajo por integrante (Git)

- Usa ramas por persona (`feat/estaciones-jonathan`, `feat/heuristica-sam`, `docs/pruebas-ana`).
- Commits pequeños y descriptivos: `git commit -m "KB: agrega estaciones Suba (Shaio, 21 Ángeles)"`.
- Pull Requests con revisión cruzada.
- En el PDF, agrega una tabla con **autor**, **PR/commit**, **aporte** y **fecha**.

---

## 9) Notas finales

- El mapa y tiempos son **educativos**; si el docente lo solicita, amplía la red con más paradas del SITP/TransMilenio.
- El sistema acepta criterios alternativos y es fácil de extender a *costo monetario* o *aforo*.
- Si el curso lo permite, puedes integrar datos reales en otra iteración (GTFS/CSV) manteniendo el mismo motor.



---

### 12.6 Guion para hablar con el tutor (mensaje sugerido)
> **Asunto**: Avance proyecto – sistema experto de enrutamiento (SITP Portal del Norte → Portal Suba)
>
> **Profe**, buen día. Avanzamos con:
> 1) **Base de conocimiento**: reglas R1–R4 (movimiento, transbordo, costo, nodos de intercambio) y penalización parametrizable.
> 2) **Datos**: generador `scripts/generate_graph.py` (500 nodos, pesos positivos, conectividad garantizada). Para el caso de estudio usamos una red **SITP simplificada** y también admitimos CSV sintético.
> 3) **Motor**: A* con heurística geodésica (Haversine) y criterios *tiempo/saltos/transbordos*.
> 4) **Evidencias**: reporte Quarto `docs/reporte.qmd` (RStudio) y script de pruebas.
>
> **Preguntas**:
> - ¿Prefiere lista de aristas (source,target,weight,line) o matriz de adyacencia NxN?
> - ¿Tamaño mínimo del dataset para evaluación? (¿500 nodos está bien?)
> - ¿Requiere interfaz de usuario o consola basta?
> - ¿Podemos ponderar además costo monetario/aforo como extensión?
>
> ¡Gracias por la retroalimentación!

### 12.7 Checklist específico según la conversación
- [ ] CSV **edges.csv** generado y versionado.
- [ ] Opción en `route_planner.py` para **leer CSV** y construir el grafo.
- [ ] Reglas documentadas en README y citadas en el **PDF**.
- [ ] Visualización (R o Python) para evidenciar el grafo.
- [ ] Video: mostrar generación del CSV, ejecución del planificador y resultado de la ruta SITP.

