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

import os, json

def load_data_from_json(path="data/bogota_sitp.json"):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

DATA = load_data_from_json("data/bogota_sitp.json") or DATA  # fallback al embebido si no está

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