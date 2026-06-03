import asyncio
import logging
import random
import math
import uvicorn
import time
from fastapi import FastAPI, Request
from pymodbus.server import StartAsyncTcpServer
from datastore import inicializar_memoria_noja
from estado import EstadoSimulador

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

app = FastAPI(title="Simulador OSM27 Avanzado")
cola_alertas = asyncio.Queue()

async def worker_notificaciones():
    while True:
        alerta = await cola_alertas.get()
        _logger.warning(f"🚀 [ALERTA MULTICANAL DESPACHADA] -> {alerta}")
        cola_alertas.task_done()

# Función auxiliar de protección contra desbordamientos (Grado Industrial)
def c16(valor):
    return min(65535, max(0, int(valor)))

async def motor_matematico(esclavo, estado_global):
    _logger.info("Motor matemático iniciado. Frecuencia: 1 Hz")
    while True:
        estado_global.procesar_ciclo()
        
        while estado_global.eventos_pendientes:
            await cola_alertas.put(estado_global.eventos_pendientes.pop(0))

        # 1. CAPA FÍSICA (Tensiones y Corrientes con AWGN)
        v_base = estado_global.v_fase_nom * (0.8 if estado_global.falla_tension else 1.0)
        ua = int(random.gauss(v_base, 0.01 * v_base))
        ub = int(random.gauss(v_base, 0.01 * v_base))
        uc = int(random.gauss(v_base, 0.01 * v_base))
        
        # Tensiones de línea compuestas derivadas
        uab = int(ua * 1.732)
        ubc = int(ub * 1.732)
        uca = int(uc * 1.732)

        if estado_global.estado_fsm == "CERRADO":
            i_base = estado_global.i_nom * estado_global.carga_actual
            if getattr(estado_global, 'pickup', False): 
                i_base = 8000 # Corriente extrema de falla
            
            ia = int(random.gauss(i_base, 0.015 * i_base))
            ib = int(random.gauss(i_base, 0.015 * i_base))
            ic = int(random.gauss(i_base, 0.015 * i_base))
            
            # --- POTENCIAS TRIFÁSICAS TOTALES REALES ---
            kva_total = int(((ua * ia) + (ub * ib) + (uc * ic)) / 1000)
            
            fp_ruido = random.gauss(estado_global.fp_carga, 0.004)
            fp_ruido = min(1.0, max(0.0, fp_ruido))
            
            kw_total = int(kva_total * fp_ruido)
            kvar_total = int(kva_total * math.sin(math.acos(fp_ruido)))
            
            # Integración de Energía
            estado_global.energia_activa_acumulada += (kw_total / 3600.0)
            estado_global.energia_reactiva_acumulada += (kvar_total / 3600.0)
        else:
            ia = ib = ic = 0
            kva_total = kw_total = kvar_total = 0
            fp_ruido = 0.0

        # Frecuencia normalizada (50 Hz con sutil jitter térmico)
        frecuencia_ruido = int(random.gauss(50.0, 0.02) * 100)

        # 2. ESCRITURA SEGURA A CONTENEDOR MODBUS (Usando clamp c16)
        esclavo.setValues(2, 10001, [1 if estado_global.bloqueo_lockout else 0])
        esclavo.setValues(2, 10010, [1 if getattr(estado_global, 'pickup', False) else 0])
        esclavo.setValues(2, 10035, [1 if estado_global.estado_fsm != "CERRADO" else 0])
        esclavo.setValues(2, 10040, [1 if estado_global.alarma_tension else 0])
        esclavo.setValues(2, 10064, [1 if estado_global.alarma_general else 0])
        esclavo.setValues(2, 10075, [1 if estado_global.estado_fsm == "CERRADO" else 0])
        
        esclavo.setValues(4, 30001, [c16(ia), c16(ib), c16(ic)])
        esclavo.setValues(4, 30005, [c16(ua), c16(ub), c16(uc)])
        esclavo.setValues(4, 30011, [c16(uab), c16(ubc), c16(uca)])
        esclavo.setValues(4, 30026, [c16(kva_total), c16(kvar_total), c16(kw_total)])
        
        # Energía Activa (32 bits mapeados en 30041 y 30042)
        e_act = int(estado_global.energia_activa_acumulada)
        esclavo.setValues(4, 30041, [(e_act >> 16) & 0xFFFF, e_act & 0xFFFF])
        
        # Energía Reactiva (32 bits mapeados en 30043 y 30044)
        e_react = int(estado_global.energia_reactiva_acumulada)
        esclavo.setValues(4, 30043, [(e_react >> 16) & 0xFFFF, e_react & 0xFFFF])
        
        esclavo.setValues(4, 30061, [c16(frecuencia_ruido)])
        esclavo.setValues(4, 30068, [c16(fp_ruido * 1000)])
        esclavo.setValues(4, 30075, [c16(estado_global.operaciones_totales)])

        # --- RELOJ DEL EQUIPO (Holding Registers 40001-40002) ---
        t_unix = int(time.time())
        esclavo.setValues(3, 40001, [(t_unix >> 16) & 0xFFFF, t_unix & 0xFFFF])

        await asyncio.sleep(1)

@app.post("/api/evento/{tipo}")
async def inyectar_evento(tipo: str, request: Request):
    estado = request.app.state.estado
    if tipo == "transitoria": estado.falla_transitoria = True
    elif tipo == "permanente": estado.falla_permanente = True
    elif tipo == "sag": estado.falla_tension = True
    elif tipo == "reset":
        estado.falla_permanente = False
        estado.falla_transitoria = False
        estado.falla_tension = False
    return {"status": "ok", "evento": tipo}

@app.post("/api/control/{accion}")
async def control_manual(accion: str, request: Request):
    estado = request.app.state.estado
    if accion == "abrir":
        estado.falla_permanente = True
        estado.apertura_manual = True
        estado.log_evento("🔧 APERTURA MANUAL desde dashboard.")
    elif accion == "cerrar":
        estado.falla_permanente = False
        estado.falla_transitoria = False
        estado.estado_fsm = "CERRADO"
        estado.open_prot = False
        estado.bloqueo_lockout = False
        estado.alarma_general = False
        estado.apertura_manual = False
        estado.intentos = 0
        estado.pickup = False
        estado.log_evento("🔧 CIERRE MANUAL desde dashboard.")
    return {"status": "ok", "accion": accion}

async def main():
    contexto_servidor, esclavo_modbus = inicializar_memoria_noja()
    estado_global = EstadoSimulador()
    app.state.estado = estado_global
    
    servidor_modbus = StartAsyncTcpServer(context=contexto_servidor, address=("0.0.0.0", 502))
    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="error")
    
    await asyncio.gather(
        servidor_modbus,
        uvicorn.Server(config_uvicorn).serve(),
        motor_matematico(esclavo_modbus, estado_global),
        worker_notificaciones() # Lanzamos el demonio de alertas
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Simulador apagado.")