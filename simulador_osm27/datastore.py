from pymodbus.datastore import ModbusSparseDataBlock, ModbusDeviceContext, ModbusServerContext

def inicializar_memoria_noja() -> ModbusServerContext:
    """
    Construye el mapa de memoria Modbus con bloques dispersos 
    para Discrete Inputs (1xxxx) e Input Registers (3xxxx).
    """
    diccionario_di = {
        10001: 0,
        10010: 0,
        10035: 0,
        10036: 0,
        10064: 0,
        10075: 1,  # Por defecto cerrado
        10118: 0
    }

    diccionario_ir = {
        30001: 0, 30002: 0, 30003: 0,
        30005: 0, 30006: 0, 30007: 0,
        30011: 0, 30012: 0, 30013: 0,
        30026: 0, 30027: 0, 30028: 0,
        30043: 0, 30044: 0,  
        30061: 0,
        30068: 0,
        30072: 0
    }

    bloque_di = ModbusSparseDataBlock(diccionario_di)
    bloque_ir = ModbusSparseDataBlock(diccionario_ir)
    
    # APLICAMOS EL ESTÁNDAR MODERNO: ModbusDeviceContext (antes SlaveContext)
    device_context = ModbusDeviceContext(
        di=bloque_di, co=None, hr=None, ir=bloque_ir
    )
    
    # Mantenemos el "slaves=" por compatibilidad con la firma de la función interna
    # Pasamos device_context sin la palabra reservada 'slaves='
    return ModbusServerContext(device_context, single=True)