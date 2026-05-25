import asyncio
import os
import sys
import datetime
from pymodbus.client import AsyncModbusTcpClient
import httpx

RESET, ROJO, VERDE, AMARILLO, CIAN = "\033[0m", "\033[91m", "\033[92m", "\033[93m", "\033[96m"

datos_ui = {
    "ua":0, "ub":0, "uc":0, "ia":0, "ib":0, "ic":0, 
    "kw":0, "kvar":0, "kva":0, "fp":0, "frec":0.0,
    "energia_act":0, "energia_react":0, "intentos":0, "max_intentos":3,
    "cerrado":False, "abierto":False, "bloqueo":False, "sag":False, 
    "fecha_equipo": "---", "msg":"Iniciando SCADA..."
}

conexion_activa = True

def dibujar_interfaz():
    sys.stdout.write('\033[H')
    sys.stdout.flush()
    
    print(f"{CIAN}=== TELEMETRÍA SCADA INDUSTRIAL - NOJA OSM27 ==={RESET}".ljust(75))
    print(f" RELOJ DEL CONTROLADOR RC10: {datos_ui['fecha_equipo']}".ljust(75))
    
    led_c = f"{ROJO}⬤{RESET}" if datos_ui['cerrado'] else "◯" 
    led_a = f"{VERDE}⬤{RESET}" if datos_ui['abierto'] else "◯" 
    led_b = f"{AMARILLO}⬤{RESET}" if datos_ui['bloqueo'] else "◯"
    led_s = f"{AMARILLO}⬤{RESET}" if datos_ui['sag'] else "◯"
    
    estado_tcp = f"{VERDE}ONLINE{RESET}" if conexion_activa else f"{ROJO}OFFLINE{RESET}"
    
    print(f" RED MODBUS/TCP: {estado_tcp}".ljust(75))
    print(f" ESTADOS: {led_c} CERRADO (Línea Viva)  {led_a} ABIERTO  {led_b} BLOQUEO  {led_s} SAG".ljust(85))
    print("-----------------------------------------------------------------------------")
    print(f" Ua: {datos_ui['ua']:>6.2f} kV | Ia: {datos_ui['ia']:>5d} A | P: {datos_ui['kw']:>5d} kW | FP: {datos_ui['fp']:.2f}")
    print(f" Ub: {datos_ui['ub']:>6.2f} kV | Ib: {datos_ui['ib']:>5d} A | Q: {datos_ui['kvar']:>5d} kVAr | Hz: {datos_ui['frec']:.2f}")
    print(f" Uc: {datos_ui['uc']:>6.2f} kV | Ic: {datos_ui['ic']:>5d} A | S: {datos_ui['kva']:>5d} kVA | AR: {datos_ui['intentos']}/{datos_ui['max_intentos']}")
    print("-----------------------------------------------------------------------------")
    print(f" ENERGÍA ACTIVA ACUMULADA:  {datos_ui['energia_act']:>8d} kWh".ljust(75))
    print(f" ENERGÍA REACTIVA ACUMULADA: {datos_ui['energia_react']:>8d} kVARh".ljust(75))
    print(f"{AMARILLO} ÚLTIMO EVENTO REGISTRADO: {datos_ui['msg']}{RESET}".ljust(90))
    print(f"{CIAN}============================================================================={RESET}".ljust(75))
    print(" [1] Inyectar Falla Transitoria  [2] Falla Permanente  [3] Inyectar Sag Tensión")
    print(" [4] Simular Corte de Cable TCP [0] SCADA Reset/Clear [Q] Salir del Monitor")
    print(" > Escriba un comando y presione ENTER: ", end="", flush=True)

async def tarea_modbus():
    cliente = AsyncModbusTcpClient('127.0.0.1', port=502)
    await cliente.connect()
    os.system('cls' if os.name == 'nt' else 'clear')
    
    while True:
        if conexion_activa:
            if not cliente.connected: await cliente.connect()
            try:
                # Lecturas precisas atomizadas por bloques Sparse
                r_blk = await cliente.read_discrete_inputs(10001, 1, slave=1)
                r_ab = await cliente.read_discrete_inputs(10035, 1, slave=1)
                r_sag = await cliente.read_discrete_inputs(10040, 1, slave=1)
                r_cer = await cliente.read_discrete_inputs(10075, 1, slave=1)
                
                r_i = await cliente.read_input_registers(30001, 3, slave=1)
                r_v = await cliente.read_input_registers(30005, 3, slave=1)
                r_p = await cliente.read_input_registers(30026, 3, slave=1)
                r_e1 = await cliente.read_input_registers(30041, 2, slave=1)
                r_e2 = await cliente.read_input_registers(30043, 2, slave=1)
                r_frec = await cliente.read_input_registers(30061, 1, slave=1)
                r_fp = await cliente.read_input_registers(30068, 1, slave=1)
                r_int = await cliente.read_input_registers(30075, 1, slave=1)
                
                r_time = await cliente.read_holding_registers(40001, 2, slave=1)

                if not any(r.isError() for r in [r_blk, r_i, r_v, r_p, r_e1, r_e2, r_time]):
                    datos_ui["bloqueo"] = r_blk.bits[0]
                    datos_ui["abierto"] = r_ab.bits[0]
                    datos_ui["sag"] = r_sag.bits[0]
                    datos_ui["cerrado"] = r_cer.bits[0]
                    
                    datos_ui["ia"], datos_ui["ib"], datos_ui["ic"] = r_i.registers
                    datos_ui["ua"] = r_v.registers[0] / 1000.0
                    datos_ui["ub"] = r_v.registers[1] / 1000.0
                    datos_ui["uc"] = r_v.registers[2] / 1000.0
                    
                    datos_ui["kva"], datos_ui["kvar"], datos_ui["kw"] = r_p.registers
                    datos_ui["frec"] = r_frec.registers[0] / 100.0
                    datos_ui["fp"] = r_fp.registers[0] / 1000.0
                    datos_ui["intentos"] = r_int.registers[0]
                    
                    datos_ui["energia_act"] = (r_e1.registers[0] << 16) | r_e1.registers[1]
                    datos_ui["energia_react"] = (r_e2.registers[0] << 16) | r_e2.registers[1]
                    
                    unix_ts = (r_time.registers[0] << 16) | r_time.registers[1]
                    datos_ui["fecha_equipo"] = datetime.datetime.fromtimestamp(unix_ts).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                datos_ui["msg"] = f"Error en lectura SCADA: {e}"
        else:
            cliente.close()
            datos_ui["ua"] = datos_ui["ub"] = datos_ui["uc"] = 0.0
            datos_ui["ia"] = datos_ui["ib"] = datos_ui["ic"] = 0
            datos_ui["kw"] = datos_ui["kvar"] = datos_ui["kva"] = 0
            datos_ui["frec"] = 0.0
            datos_ui["fecha_equipo"] = "DESCONECTADO (Link Down)"
            
        dibujar_interfaz()
        await asyncio.sleep(1)

async def enviar_api(comando: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"http://127.0.0.1:8000/api/evento/{comando}")
            datos_ui["msg"] = f"Comando '{comando.upper()}' enviado. Analizando FSM."
    except Exception as e:
        datos_ui["msg"] = f"Error conectando a API: {e}"
    dibujar_interfaz()

async def tarea_teclado():
    global conexion_activa
    loop = asyncio.get_running_loop()
    while True:
        cmd = await loop.run_in_executor(None, sys.stdin.readline)
        cmd = cmd.strip().upper()
        
        sys.stdout.write("\033[F\033[K")
        sys.stdout.flush()

        if cmd == '1': await enviar_api("transitoria")
        elif cmd == '2': await enviar_api("permanente")
        elif cmd == '3': await enviar_api("sag")
        elif cmd == '4': 
            conexion_activa = not conexion_activa
            datos_ui["msg"] = "Enlace TCP Modbus re-conectado." if conexion_activa else "Enlace TCP Modbus cortado voluntariamente."
        elif cmd == '0': await enviar_api("reset")
        elif cmd == 'Q': os._exit(0)

async def main():
    await asyncio.gather(tarea_modbus(), tarea_teclado())

if __name__ == "__main__":
    asyncio.run(main())