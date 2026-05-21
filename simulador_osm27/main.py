import asyncio
import logging
import random
import uvicorn
from fastapi import FastAPI, Request
from pymodbus.server import StartAsyncTcpServer
from datastore import inicializar_memoria_noja
from estado import EstadoSimulador

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

app = FastAPI(title="Panel de Control - Simulador OSM27")

async def motor_matematico(contexto, estado_global):
    _logger.info("Motor matemático iniciado. Frecuencia: 1 Hz")
    esclavo = contexto[0] 
    
    while True:
        # 1. EL CEREBRO PIENSA (Actualiza FSM, Curva de Carga y Energía)
        estado_global.procesar_ciclo()
        
        # 2. CAPA FÍSICA: AGREGAMOS RUIDO AWGN SOLO SI HAY FLUJO DE CORRIENTE
        if estado_global.estado_fsm == "CERRADO":
            # 1.5% de ruido a la corriente y tensión
            ia_ruido = int(random.gauss(estado_global.ia, 0.015 * estado_global.ia))
            ib_ruido = int(random.gauss(estado_global.ib, 0.015 * estado_global.ib))
            ic_ruido = int(random.gauss(estado_global.ic, 0.015 * estado_global.ic))
            
            ua_ruido = int(random.gauss(estado_global.ua, 0.015 * estado_global.ua))
            ub_ruido = int(random.gauss(estado_global.ub, 0.015 * estado_global.ub))
            uc_ruido = int(random.gauss(estado_global.uc, 0.015 * estado_global.uc))
        else:
            # En falla/espera la corriente es cero. 
            # La tensión se mantiene estable aguas arriba del reconectador.
            ia_ruido = ib_ruido = ic_ruido = 0
            ua_ruido = int(estado_global.ua)
            ub_ruido = int(estado_global.ub)
            uc_ruido = int(estado_global.uc)

        # 3. ESCRITURA MODBUS: MAPA DE MEMORIA ESTRICTO
        
        # Entradas Discretas (Estados Lógicos - Función 2)
        esclavo.setValues(2, 10075, [1 if estado_global.estado_cerrado else 0])
        esclavo.setValues(2, 10035, [1 if estado_global.estado_abierto else 0])
        esclavo.setValues(2, 10001, [1 if getattr(estado_global, 'bloqueo_lockout', False) else 0])

        # Registros de Entrada Analógicos (Función 4) - ¡Sin exceder 65535!
        # Corrientes (A)
        esclavo.setValues(4, 30001, [ia_ruido])
        esclavo.setValues(4, 30002, [ib_ruido])
        esclavo.setValues(4, 30003, [ic_ruido])
        
        # Tensiones de Fase (V)
        esclavo.setValues(4, 30005, [ua_ruido])
        esclavo.setValues(4, 30006, [ub_ruido])
        esclavo.setValues(4, 30007, [uc_ruido])
        
        # Potencias (kW, kVAr, kVA)
        esclavo.setValues(4, 30026, [int(estado_global.kw_total)])
        esclavo.setValues(4, 30027, [int(estado_global.kvar_total)])
        esclavo.setValues(4, 30028, [int(estado_global.kva_total)])
        
        # Factor de Potencia (Escalado x1000 para enviar decimales, ej 980)
        esclavo.setValues(4, 30068, [int(estado_global.factor_potencia * 1000)])
        
        # Energía y Contadores (Casteados a int)
        esclavo.setValues(4, 30043, [int(estado_global.energia_activa_acumulada)])
        esclavo.setValues(4, 30044, [int(estado_global.energia_reactiva_acumulada)])
        esclavo.setValues(4, 30072, [estado_global.intentos]) # O el contador total
        
        # 4. Cedemos el procesador al Event Loop
        await asyncio.sleep(1)

@app.post("/api/fallas/sobrecorriente/{estado_falla}")
async def inyectar_falla(estado_falla: int, request: Request):
    """
    Endpoint para inyectar/limpiar una falla permanente. 1 = Activa, 0 = Normal.
    """
    estado_simulador = request.app.state.estado
    activa = True if estado_falla == 1 else False
    
    # LA MAGIA DE LA ARQUITECTURA: 
    # Solo cambiamos el "flag" lógico. La FSM hará el resto del trabajo.
    estado_simulador.falla_permanente = activa
    
    estado_str = "inyectada" if activa else "limpiada"
    return {
        "status": "success", 
        "message": f"Falla permanente {estado_str}. El reconectador evaluará la red."
    }

async def main():
    contexto_servidor = inicializar_memoria_noja()
    estado_global = EstadoSimulador()

    app.state.estado = estado_global
    
    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    servidor_web = uvicorn.Server(config_uvicorn)
    
    # Puerto 502 ESTRICTO (Requiere Administrador/Root) 
    servidor_modbus = StartAsyncTcpServer(
        context=contexto_servidor,
        address=("0.0.0.0", 502),
    )
    
    _logger.info("Iniciando todos los subsistemas (FastAPI + Modbus TCP:502)...")
    
    await asyncio.gather(
        servidor_modbus,
        servidor_web.serve(),
        motor_matematico(contexto_servidor, estado_global)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Simulador apagado.")