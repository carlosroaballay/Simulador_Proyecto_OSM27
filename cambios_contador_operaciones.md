# Cambios: Contador de Operaciones de Reconexión — OSM27

**Fecha:** 2026-06-02  
**Proyecto:** Simulador OSM27 — `simulador_osm27/`

---

## Contexto

El simulador del reconectador OSM27 maneja dos variables relacionadas con las operaciones de reenganche:

- `intentos`: cuenta los intentos del ciclo actual (0 a 3, se resetea en cada ciclo de falla).
- `operaciones_totales`: cuenta el total acumulado de disparos desde que arrancó el simulador.

El registro Modbus **30075** (leído por `tb_gateway` como `contador_operaciones`) publicaba `intentos`, lo cual no sirve como contador histórico ya que su valor máximo es 3 y se resetea constantemente.

---

## Cambios realizados

### 1. `estado.py` — Inicialización de `operaciones_totales`

**Antes:**
```python
self.operaciones_totales = 150
```

**Después:**
```python
self.operaciones_totales = 0
```

**Por qué:** El valor 150 era arbitrario y no representaba ninguna operación real. Arrancando desde 0 el contador refleja correctamente las operaciones ocurridas desde el inicio del simulador, sin datos falsos previos.

---

### 2. `main.py` — Registro Modbus 30075

**Antes:**
```python
esclavo.setValues(4, 30075, [c16(estado_global.intentos)])
```

**Después:**
```python
esclavo.setValues(4, 30075, [c16(estado_global.operaciones_totales)])
```

**Por qué:** El registro 30075 es el que ThingsBoard Gateway lee y publica como telemetría `contador_operaciones`. Publicando `intentos` el valor oscilaba entre 0 y 3 sin información útil. Publicando `operaciones_totales` ThingsBoard recibe el acumulado real de disparos, lo que permite:

- Mostrar el total en un widget **Value Card**.
- Ver la evolución histórica con un **Timeseries chart**.
- Contar operaciones por día con agregación en ThingsBoard.

---

## Impacto

- `operaciones_totales` solo se usa en `estado.py` (inicialización, incremento y log). No interviene en ninguna lógica de control del reconectador, por lo que el cambio es seguro.
- El valor se incrementa cada vez que el reconectador dispara por sobrecorriente (`estado_fsm` pasa de `CERRADO` a `ESPERA`).
- El contador se resetea a 0 al reiniciar el simulador (no es persistente en disco).
