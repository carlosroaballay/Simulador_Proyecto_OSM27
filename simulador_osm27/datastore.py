from pymodbus.datastore import ModbusSparseDataBlock, ModbusSlaveContext, ModbusServerContext

def inicializar_memoria_noja() -> tuple:
    # Entradas Discretas (Estados, Alarmas y Fallas)
    diccionario_di = {
        10001: 0, # Lockout (Bloqueo)
        10010: 0, # Pickup (Sobrecorriente detectada)
        10035: 0, # Estado Abierto
        10036: 0, # Apertura por Protección (Falla)
        10040: 0, # Tensión fuera de rango
        10064: 0, # Alarma General
        10075: 1  # Estado Cerrado
    }

    # Registros Analógicos (Variables Físicas)
    diccionario_ir = {
        30001: 0, 30002: 0, 30003: 0, # Ia, Ib, Ic
        30005: 0, 30006: 0, 30007: 0, # Ua, Ub, Uc
        30011: 0, 30012: 0, 30013: 0, # Uab, Ubc, Uca
        30026: 0, 30027: 0, 30028: 0, # kVA, kVAr, kW
        30041: 0, 30042: 0, 30043: 0, 30044: 0, # Energías (32 bits Hi/Lo)
        30061: 0, # Frecuencia (Hz)
        30068: 0, # Factor de Potencia
        30075: 0,  # Contador de aperturas
        30082: 8000 # Umbral de disparo por sobrecorriente (A)
    }

    # NUEVO: Holding Registers (Ajustes configurables). Demuestra escalabilidad.
    diccionario_hr = {
        40001: 0, # fecha y hora Hi
        40002: 0, # fecha y hora Lo
        40003: 5, # Tiempo muerto de reconexión (Segundos)
        40005: 3  # Máximo de intentos de reenganche
        
    }

    bloque_di = ModbusSparseDataBlock(diccionario_di)
    bloque_ir = ModbusSparseDataBlock(diccionario_ir)
    bloque_hr = ModbusSparseDataBlock(diccionario_hr)
    
    device_context = ModbusSlaveContext(di=bloque_di, co=None, hr=bloque_hr, ir=bloque_ir)
    server_context = ModbusServerContext(device_context, single=True)
    
    return server_context, device_context