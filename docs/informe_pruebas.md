
# Proyecto: Sistema inteligente de rutas (SITP/TransMilenio Bogotá)

> **Trayecto de ejemplo**: *Portal del Norte* → *Portal Suba*  
> **Paradigma**: Base de conocimiento en reglas + búsqueda heurística (A*)




---
# Test resultado prueba ejecucion 
#1 *Portal del Norte* → *Portal Suba*
```
PS C:\Users\jonat\Downloads\IA SITP> python route_planner.py --explain `
>>   --from "Portal del Norte" --to "Portal Suba"
Ruta óptima (criterio: tiempo):
Portal del Norte ──(AUTONORTE)→ Toberín
Toberín → Calle 146
Calle 146 → Calle 116/P. Pepe Sierra
Calle 116/P. Pepe Sierra → Héroes
[Transbordo] Héroes ⇄ Suba - Calle 95
Héroes ──(CONEXION)→ Suba - Calle 95
[Transbordo] Suba - Calle 95 ⇄ Shaio
Suba - Calle 95 ──(SUBA)→ Shaio
Shaio → 21 Ángeles
21 Ángeles → La Campiña
La Campiña → Portal Suba

Tiempo estimado: 58 min  |  Transbordos: 3  |  Saltos: 9

Reglas aplicadas:
- R1: Movimiento permitido solo si existe enlace directo entre estaciones.
- R2: Si cambia la línea entre dos enlaces consecutivos → se considera transbordo.
- R3: Costo = tiempo_enlace + penalización_transbordo (si aplica).
- R4: Estaciones con enlaces de varias líneas son nodos de intercambio.
PS C:\Users\jonat\Downloads\IA SITP>

```
---
#2 *Portal del Norte* → *Calle 95*
->aparece lo siguiente por pantalla
```
  python route_planner.py --explain `
>>   --from "Portal del Norte" --to "Calle 95"
Estación desconocida. Disponible:
 - Portal del Norte
 - Toberín
 - Calle 146
 - Calle 116/P. Pepe Sierra
 - Virrey
 - Héroes
 - Calle 100
 - Calle 85
 - Calle 72
 - Suba - Calle 95
 - Shaio
 - 21 Ángeles
 - La Campiña
 - Portal Suba
 - Portal 80
 - Quirigua
 - Av. 68 (C80)
 - Portal Américas
 - Biblioteca Tintal
 - Banderas
 - Marsella
 - Portal Sur
 - Perdomo
 - Sevillana
 - General Santander
 - Portal Tunal
 - Venecia
 - Alquería
 - Portal Usme
 - Molinos
 - Country Sur
 - Portal 20 de Julio
 - El Consuelo
PS C:\Users\jonat\Downloads\IA SITP>

```
---
#3 *Portal del Norte* → *Calle 85*
->aparece lo siguiente por pantalla
```
PS C:\Users\jonat\Downloads\IA SITP> python route_planner.py --explain `
>>   --from "Portal del Norte" --to "Calle 85"
Ruta óptima (criterio: tiempo):
Portal del Norte ──(AUTONORTE)→ Toberín
Toberín → Calle 146
Calle 146 → Calle 116/P. Pepe Sierra
[Transbordo] Calle 116/P. Pepe Sierra ⇄ Virrey
Calle 116/P. Pepe Sierra ──(CONEXION)→ Virrey
[Transbordo] Virrey ⇄ Calle 85
Virrey ──(NQS)→ Calle 85

Tiempo estimado: 32 min  |  Transbordos: 2  |  Saltos: 5

Reglas aplicadas:
- R1: Movimiento permitido solo si existe enlace directo entre estaciones.
- R2: Si cambia la línea entre dos enlaces consecutivos → se considera transbordo.
- R3: Costo = tiempo_enlace + penalización_transbordo (si aplica).
- R4: Estaciones con enlaces de varias líneas son nodos de intercambio.
PS C:\Users\jonat\Downloads\IA SITP>

```