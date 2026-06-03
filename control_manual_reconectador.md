# Control Manual del Reconectador desde ThingsBoard

**Fecha:** 2026-06-02  
**Proyecto:** Simulador OSM27 — `simulador_osm27/main.py`

---

## Objetivo

Permitir que desde un dashboard de ThingsBoard se pueda abrir o cerrar manualmente el reconectador OSM27, afectando en tiempo real la simulación (corrientes, estados digitales, logs de eventos).

---

## Cambio en el simulador (`main.py`)

Se agregó el siguiente endpoint a la API FastAPI que ya corría en el puerto 8000:

```python
@app.post("/api/control/{accion}")
async def control_manual(accion: str, request: Request):
    estado = request.app.state.estado
    if accion == "abrir":
        estado.estado_fsm = "ESPERA"
        estado.open_prot = True
        estado.tiempo_apertura = time.time()
        estado.log_evento("🔧 APERTURA MANUAL desde dashboard.")
    elif accion == "cerrar":
        estado.estado_fsm = "CERRADO"
        estado.open_prot = False
        estado.bloqueo_lockout = False
        estado.alarma_general = False
        estado.log_evento("🔧 CIERRE MANUAL desde dashboard.")
    return {"status": "ok", "accion": accion}
```

### Por qué cada línea:

**Acción `abrir`:**
- `estado_fsm = "ESPERA"` → pone el reconectador en estado abierto. El motor matemático detecta esto y pone Ia, Ib, Ic = 0 y kW/kVA/kVAr = 0.
- `open_prot = True` → activa el bit de apertura por protección (registro 10036).
- `tiempo_apertura = time.time()` → necesario para que la máquina de estados pueda calcular el dead_time si luego ocurre un reenganche automático.

**Acción `cerrar`:**
- `estado_fsm = "CERRADO"` → el motor matemático reanuda el cálculo de corrientes y potencias.
- `open_prot = False` → desactiva el bit de apertura por protección.
- `bloqueo_lockout = False` y `alarma_general = False` → limpia alarmas para permitir operación normal, igual que hace el reset automático.

---

## Efecto en la simulación

| Acción | Corrientes | Potencias | Bit 10035 (Abierto) | Bit 10075 (Cerrado) |
|--------|-----------|-----------|----------------------|----------------------|
| Abrir  | 0 A       | 0 kW/kVA/kVAr | 1 | 0 |
| Cerrar | Vuelven al nominal × carga | Vuelven al nominal | 0 | 1 |

---

## Cómo conectar con ThingsBoard

### Opción A — Llamada HTTP directa desde Rule Chain

1. En ThingsBoard ir a **Rule Chains → Add new rule chain** (o usar la raíz).
2. Agregar un nodo **REST API Call**:
   - URL: `http://localhost:8000/api/control/abrir` (o `cerrar`)
   - Method: `POST`
3. Conectar ese nodo a un nodo **Message Type Switch** que filtre por RPC Request.

### Opción B — Widget RPC Button en el dashboard (más simple)

1. En el dashboard, agregar widget → buscar **RPC Button** en el bundle *Control Widgets*.
2. Configurar el botón "Abrir":
   - **RPC method:** `abrir`
   - **RPC params:** `{}` (vacío)
3. Configurar el botón "Cerrar":
   - **RPC method:** `cerrar`
   - **RPC params:** `{}` (vacío)
4. En **tb_gateway**, en el archivo de configuración del conector REST o Modbus, agregar el mapping de RPC:

```json
"rpc": {
  "enabled": true,
  "methods": [
    {
      "method": "abrir",
      "url": "http://localhost:8000/api/control/abrir",
      "httpMethod": "POST"
    },
    {
      "method": "cerrar",
      "url": "http://localhost:8000/api/control/cerrar",
      "httpMethod": "POST"
    }
  ]
}
```

5. Reiniciar tb_gateway para que tome la nueva configuración.

### Verificación rápida sin ThingsBoard

Podés probar el endpoint directamente desde terminal:

```bash
# Abrir el reconectador
curl -X POST http://localhost:8000/api/control/abrir

# Cerrar el reconectador
curl -X POST http://localhost:8000/api/control/cerrar
```

Deberías ver en el simulador el log del evento y los valores de corriente cambiar a 0 (abrir) o volver al nominal (cerrar).

---

## Importante

- El endpoint **no persiste** el estado si el simulador se reinicia (vuelve a `CERRADO` por defecto).
- Si hay una **falla permanente activa**, cerrar manualmente no alcanza: hay que primero hacer un reset (`/api/evento/reset`) para limpiar la falla y luego cerrar.
