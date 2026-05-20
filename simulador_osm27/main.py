import asyncio
import logging
import random
from fastapi import FastAPI, Request
import uvicorn
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
        # --- 1. ESCRITURA DE ENTRADAS DISCRETAS (Función 2) ---
        # Estados lógicos (10035 = Abierto, 10075 = Cerrado) 
        esclavo.setValues(2, 10075, [1 if estado_global.estado_cerrado else 0])
        esclavo.setValues(2, 10035, [1 if estado_global.estado_abierto else 0])
        esclavo.setValues(2, 10001, [1 if estado_global.bloqueo_lockout else 0])
        esclavo.setValues(2, 10010, [1 if estado_global.pickup else 0])
        esclavo.setValues(2, 10036, [1 if estado_global.open_prot else 0])
        esclavo.setValues(2, 10064, [1 if estado_global.alarma_general else 0])
        esclavo.setValues(2, 10118, [1 if estado_global.warning else 0])

        # 2. ESCRITURA DE REGISTROS DE ENTRADA (Función 4) con AWGN ---
        
        # Corrientes (1.5% de ruido)
        esclavo.setValues(4, 30001, [int(random.gauss(estado_global.ia, 0.015 * estado_global.ia))])
        esclavo.setValues(4, 30002, [int(random.gauss(estado_global.ib, 0.015 * estado_global.ib))])
        esclavo.setValues(4, 30003, [int(random.gauss(estado_global.ic, 0.015 * estado_global.ic))])
        
        # Tensiones de Fase (1.5% de ruido)
        esclavo.setValues(4, 30005, [int(random.gauss(estado_global.ua, 0.015 * estado_global.ua))])
        esclavo.setValues(4, 30006, [int(random.gauss(estado_global.ub, 0.015 * estado_global.ub))])
        esclavo.setValues(4, 30007, [int(random.gauss(estado_global.uc, 0.015 * estado_global.uc))])

        # Tensiones de Línea (Podemos hacerlas dependientes o simplemente aplicarles ruido)
        esclavo.setValues(4, 30011, [int(random.gauss(estado_global.uab, 0.015 * estado_global.uab))])
        esclavo.setValues(4, 30012, [int(random.gauss(estado_global.ubc, 0.015 * estado_global.ubc))])
        esclavo.setValues(4, 30013, [int(random.gauss(estado_global.uca, 0.015 * estado_global.uca))])

        # Potencias 
        esclavo.setValues(4, 30026, [int(random.gauss(estado_global.kva_total, 0.01 * estado_global.kva_total))])
        esclavo.setValues(4, 30027, [int(random.gauss(estado_global.kvar_total, 0.01 * estado_global.kvar_total))])
        esclavo.setValues(4, 30028, [int(random.gauss(estado_global.kw_total, 0.01 * estado_global.kw_total))])

        # Factor de potencia (x1000 según manual hipotético / x0.001 en cliente) 
        esclavo.setValues(4, 30068, [int(estado_global.factor_potencia * 1000)])
        
        # Frecuencia (x100 según asunción para enviar decimales)
        esclavo.setValues(4, 30061, [int(estado_global.frecuencia * 100)])
        
        # Contador de operaciones 
        esclavo.setValues(4, 30072, [estado_global.operaciones_totales])
        
        # Cedemos el procesador (Multiplexación TDM)
        await asyncio.sleep(1)

@app.post("/api/fallas/sobrecorriente/{estado_falla}")
async def inyectar_falla(estado_falla: int, request: Request):
    """
    Endpoint para inyectar/limpiar una falla. 1 = Activa, 0 = Normal.
    """
    estado_simulador = request.app.state.estado
    activa = True if estado_falla == 1 else False
    
    estado_simulador.inyectar_falla_sobrecorriente(activa)
    estado_str = "inyectada" if activa else "limpiada"
    
    return {"status": "success", "message": f"Falla de sobrecorriente {estado_str}."}

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