import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def probar_servidor():
    print("[*] Iniciando cliente de prueba Modbus TCP...")
    
    # 1. Instanciamos el cliente apuntando a la IP local y puerto de nuestro servidor
    cliente = AsyncModbusTcpClient('127.0.0.1', port=502)
    
    # 2. Intentamos establecer el handshake TCP (SYN, SYN-ACK, ACK)
    conectado = await cliente.connect()
    
    if not conectado:
        print("[!] Error fatal: No hay conexión. ¿Está corriendo el simulador con sudo?")
        return
        
    print("[+] Conexión TCP exitosa. Consultando Tensión Ua (Registro 30005)...")
    
    # 3. Disparamos la petición Modbus (Function Code 4: Read Input Registers)
    # address=30005: Porque configuramos la memoria con zero_mode=False
    # count=1: Queremos traer un solo registro de 16 bits
    # slave=1: El Unit ID por defecto de nuestro simulador
    respuesta = await cliente.read_input_registers(address=30005, count=1, device_id=1)
    
    # 4. Evaluamos la respuesta de la capa de aplicación
    if respuesta.isError():
        print(f"[!] El servidor retornó un Error Modbus: {respuesta}")
    else:
        valor_leido = respuesta.registers[0]
        print(f"[+] ¡Éxito! Valor crudo en RAM: {valor_leido}")
        print(f"[+] Valor físico interpretado: {valor_leido / 1000.0} kV")
        
    # 5. Cerramos el socket civilizadamente
    cliente.close()

if __name__ == "__main__":
    asyncio.run(probar_servidor())
