import asyncio
import os
import sys
from pymodbus.client import AsyncModbusTcpClient
import httpx

# Códigos ANSI para colores en la terminal
RESET = "\033[0m"
ROJO = "\033[91m"
VERDE = "\033[92m"
AMARILLO = "\033[93m"
CIAN = "\033[96m"

# Diccionario global (Nuestra memoria de video)
datos_ui = {
    "ua": 0, "ub": 0, "uc": 0,
    "ia": 0, "ib": 0, "ic": 0,
    "kw": 0, "kvar": 0, "kva": 0,
    "energia_act": 0, "energia_react": 0,
    "cerrado": False, "abierto": False, "bloqueo": False,
    "msg_sistema": "Iniciando enlace TCP..."
}

def limpiar_pantalla():
    """Limpia la consola independientemente del SO (Windows/Linux)"""
    os.system('cls' if os.name == 'nt' else 'clear')

def dibujar_interfaz():
    """Renderiza el SCADA en modo texto"""
    limpiar_pantalla()
    print(f"{CIAN}================================================={RESET}")
    print(f"{CIAN}      PANEL DE OPERADOR SCADA - NOJA OSM27       {RESET}")
    print(f"{CIAN}================================================={RESET}")
    
    # Lógica de LEDs circulares
    led_cerrado = f"{VERDE}⬤{RESET}" if datos_ui['cerrado'] else "◯"
    led_abierto = f"{AMARILLO}⬤{RESET}" if datos_ui['abierto'] else "◯"
    led_bloqueo = f"{ROJO}⬤{RESET}" if datos_ui['bloqueo'] else "◯"
    
    print(f"\n ESTADOS:   {led_cerrado} CERRADO(Línea Viva)   {led_abierto} ABIERTO   {led_bloqueo} BLOQUEO(Lockout)\n")
    print(f" TENSIONES (kV)       CORRIENTES (A)       POTENCIAS")
    print(f" -----------------------------------------------------------")
    print(f" Ua: {datos_ui['ua']:>6.2f} kV        Ia: {datos_ui['ia']:>6d} A        P: {datos_ui['kw']:>6d} kW")
    print(f" Ub: {datos_ui['ub']:>6.2f} kV        Ib: {datos_ui['ib']:>6d} A        Q: {datos_ui['kvar']:>6d} kVAr")
    print(f" Uc: {datos_ui['uc']:>6.2f} kV        Ic: {datos_ui['ic']:>6d} A        S: {datos_ui['kva']:>6d} kVA")
    print(f" -----------------------------------------------------------")
    print(f" ENERGÍA ACTIVA:   {datos_ui['energia_act']} kWh")
    print(f" ENERGÍA REACTIVA: {datos_ui['energia_react']} kVArh\n")
    
    print(f"{AMARILLO}ÚLTIMO MENSAJE: {datos_ui['msg_sistema']}{RESET}")
    print(f"{CIAN}================================================={RESET}")
    print(" COMANDOS: [1] Inyectar Falla | [0] Limpiar Falla | [Q] Salir")
    print(" > Escriba un comando y presione ENTER: ", end="", flush=True)

async def tarea_modbus():
    """Hilo de fondo que consulta al simulador (Polling)"""
    cliente = AsyncModbusTcpClient('127.0.0.1', port=502)
    conectado = await cliente.connect()
    
    if not conectado:
        datos_ui["msg_sistema"] = "ERROR: No se pudo conectar a Modbus:502."
        dibujar_interfaz()
        return

    datos_ui["msg_sistema"] = "Enlace TCP Modbus establecido."
    
    while True:
        try:
            # 1. Leemos Estados Lógicos (Se leen de a 1)
            res_di_cerrado = await cliente.read_discrete_inputs(address=10075, count=1, device_id=1)
            res_di_abierto = await cliente.read_discrete_inputs(address=10035, count=1, device_id=1)
            res_di_bloqueo = await cliente.read_discrete_inputs(address=10001, count=1, device_id=1)
            
            # 2. Leemos Registros Analógicos en sub-bloques exactos (Sin huecos)
            res_i = await cliente.read_input_registers(address=30001, count=3, device_id=1) # Ia, Ib, Ic
            res_v = await cliente.read_input_registers(address=30005, count=3, device_id=1) # Ua, Ub, Uc
            res_p = await cliente.read_input_registers(address=30026, count=3, device_id=1) # S, Q, P
            res_e = await cliente.read_input_registers(address=30043, count=2, device_id=1) # Energías
            
            # 3. Verificamos que ninguna trama haya rebotado
            if not (res_di_cerrado.isError() or res_i.isError() or res_v.isError() or res_p.isError()):
                
                datos_ui["cerrado"] = res_di_cerrado.bits[0]
                datos_ui["abierto"] = res_di_abierto.bits[0]
                datos_ui["bloqueo"] = res_di_bloqueo.bits[0]
                
                datos_ui["ia"] = res_i.registers[0]
                datos_ui["ib"] = res_i.registers[1]
                datos_ui["ic"] = res_i.registers[2]
                
                datos_ui["ua"] = res_v.registers[0] / 1000.0  
                datos_ui["ub"] = res_v.registers[1] / 1000.0  
                datos_ui["uc"] = res_v.registers[2] / 1000.0  
                
                datos_ui["kw"] = res_p.registers[0]
                datos_ui["kvar"] = res_p.registers[1]
                datos_ui["kva"] = res_p.registers[2]
                
                datos_ui["energia_act"] = res_e.registers[0]
                datos_ui["energia_react"] = res_e.registers[1]
            else:
                datos_ui["msg_sistema"] = "ADVERTENCIA: Fallo de lectura (Illegal Data Address)"
            
            dibujar_interfaz()
            
        except Exception as e:
            datos_ui["msg_sistema"] = f"Error de red: {e}"
            dibujar_interfaz()
            
        await asyncio.sleep(1)

async def inyectar_falla_api(estado: int):
    """Envía un POST a FastAPI"""
    url = f"http://127.0.0.1:8000/api/fallas/sobrecorriente/{estado}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url)
            datos = response.json()
            datos_ui["msg_sistema"] = f"API Web: {datos['message']}"
    except Exception as e:
        datos_ui["msg_sistema"] = f"Error conectando a FastAPI (Puerto 8000): {e}"
    dibujar_interfaz()

async def tarea_teclado():
    """Lee el teclado de forma asíncrona sin bloquear el bucle de UI"""
    loop = asyncio.get_running_loop()
    while True:
        # Ejecuta la función bloqueante input() en un hilo secundario
        comando = await loop.run_in_executor(None, sys.stdin.readline)
        comando = comando.strip().upper()
        
        if comando == '1':
            datos_ui["msg_sistema"] = "Inyectando Falla Permanente..."
            dibujar_interfaz()
            await inyectar_falla_api(1)
        elif comando == '0':
            datos_ui["msg_sistema"] = "Limpiando Falla Permanente..."
            dibujar_interfaz()
            await inyectar_falla_api(0)
        elif comando == 'Q':
            print("\nSaliendo del SCADA...")
            os._exit(0)

async def main():
    # Lanzamos el polling Modbus y el lector de teclado al mismo tiempo
    await asyncio.gather(
        tarea_modbus(),
        tarea_teclado()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSaliendo...")