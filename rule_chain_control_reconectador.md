# Rule Chain: Control Manual del Reconectador OSM27 en ThingsBoard

**Fecha:** 2026-06-02

---

## Objetivo

Permitir que desde un dashboard de ThingsBoard se envíe un comando RPC para abrir o cerrar el reconectador OSM27, el cual es procesado por una Rule Chain que llama a la API REST del simulador.

---

## Flujo completo

```
Dashboard (botón RPC)
        │
  ThingsBoard recibe RPC
        │
  Rule Chain: Control Reconectador
        │
  [Message Type Switch]
        │ RPC Request to device
  [Script Filtro: abrir?]
   True │              │ False
        │         [Script Filtro: cerrar?]
        │          True │
        │               │
[REST API Call]   [REST API Call]
 /api/control/     /api/control/
    abrir             cerrar
        │               │
  Simulador OSM27 (puerto 8000)
```

---

## Paso a paso de la Rule Chain

### Nodo 1 — Message Type Switch

- **Tipo:** Message Type Switch
- **Propósito:** Clasificar el mensaje entrante. Solo deja pasar los mensajes de tipo RPC enviados desde el dashboard hacia el dispositivo.
- **Relación de salida usada:** `RPC Request to device`
- **Por qué este tipo:** Cuando un botón RPC del dashboard envía un comando, ThingsBoard genera internamente un mensaje de tipo `RPC Request to device`. Las otras relaciones (Post telemetry, Post attributes, etc.) corresponden a otros tipos de mensajes que no nos interesan aquí.

---

### Nodo 2 — Script Filtro "es abrir?"

- **Tipo:** Script (Filtro)
- **Script:**
```javascript
return msg.method === 'abrir';
```
- **Propósito:** Verificar si el método RPC recibido es `abrir`.
- **Salida True:** conectada al REST API Call de apertura.
- **Salida False:** conectada al siguiente filtro.
- **Por qué filtro y no script de transformación:** El nodo filtro devuelve `True`/`False` para rutear el mensaje. El nodo de transformación modifica el contenido del mensaje pero no rutea.

---

### Nodo 3 — Script Filtro "es cerrar?"

- **Tipo:** Script (Filtro)
- **Script:**
```javascript
return msg.method === 'cerrar';
```
- **Propósito:** Verificar si el método RPC recibido es `cerrar`.
- **Salida True:** conectada al REST API Call de cierre.
- **Salida False:** no conectada (se ignora).

---

### Nodo 4 — REST API Call "Abrir"

- **Tipo:** REST API Call
- **URL:** `http://localhost:8000/api/control/abrir`
- **Method:** POST
- **Propósito:** Llamar al endpoint del simulador para forzar la apertura del reconectador. El simulador pone `estado_fsm = "ESPERA"`, lo que hace que las corrientes y potencias caigan a 0 en los registros Modbus.

---

### Nodo 5 — REST API Call "Cerrar"

- **Tipo:** REST API Call
- **URL:** `http://localhost:8000/api/control/cerrar`
- **Method:** POST
- **Propósito:** Llamar al endpoint del simulador para cerrar el reconectador. El simulador pone `estado_fsm = "CERRADO"` y limpia alarmas, reanudando el cálculo de corrientes y potencias.

---

## Configuración del widget en el dashboard

1. Editar el dashboard → **Add widget**
2. Bundle: **Control Widgets**
3. Widget: **Command Button** (o Round Switch)
4. Configurar botón "Abrir":
   - Target device: dispositivo OSM27
   - RPC method: `abrir`
   - Params: `{}`
5. Repetir para botón "Cerrar":
   - RPC method: `cerrar`
   - Params: `{}`

---

## Vincular la Rule Chain al dispositivo

1. Ir a **Device Profiles** → perfil del OSM27
2. Campo **Rule chain** → seleccionar `Control Reconectador`
3. Guardar

---

## Comportamiento esperado

| Acción | Estado FSM | Ia, Ib, Ic | kW / kVA / kVAr | Bit Abierto (10035) | Bit Cerrado (10075) |
|--------|-----------|------------|-----------------|----------------------|----------------------|
| Abrir  | ESPERA    | 0 A        | 0               | 1                    | 0                    |
| Cerrar | CERRADO   | nominal × carga | nominal    | 0                    | 1                    |

---

## Limitación conocida

La apertura es **transitoria**: al estar en estado `ESPERA`, la máquina de estados del simulador tiene activo el temporizador de dead time (5 segundos). Si no hay falla activa, después de 5 segundos el reconectador intenta cerrar automáticamente.

Para una apertura manual permanente se requiere agregar el estado `ABIERTO_MANUAL` a la máquina de estados (pendiente de implementación).
