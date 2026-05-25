import sys
import time
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal
from pymodbus.client import ModbusTcpClient

# =========================================================
# 1. EL TRABAJADOR (Data Plane / Hilo Secundario)
# =========================================================
class WorkerModbus(QThread):
    # Definimos la señal que transportará el diccionario con datos
    datos_actualizados = pyqtSignal(dict)

    def run(self):
        """Este bucle infinito corre en un núcleo separado del procesador"""
        # Usamos el cliente síncrono estándar porque ya estamos en un hilo separado
        cliente = ModbusTcpClient('127.0.0.1', port=502)
        cliente.connect()
        
        while True:
            try:
                # Leemos la tensión Ua, Ub, Uc (3 registros desde el 30005)
                # OJO: Si usaste pymodbus==3.5.2, el argumento es slave=1. 
                # Si estás en la versión nueva, omití slave=1 o usa slave=1 dependiendo de tu versión.
                res_v = cliente.read_input_registers(address=30005, count=3, slave=1)
                
                if not res_v.isError():
                    # Empaquetamos los datos
                    datos = {
                        "ua": res_v.registers[0] / 1000.0,
                        "ub": res_v.registers[1] / 1000.0,
                        "uc": res_v.registers[2] / 1000.0
                    }
                    
                    # EMITIMOS LA SEÑAL (Disparamos los datos hacia la GUI)
                    self.datos_actualizados.emit(datos)
                    
            except Exception as e:
                print(f"Error de red silencioso: {e}")
                
            time.sleep(1) # Hacemos polling cada 1 segundo

# =========================================================
# 2. EL CONTROLADOR (Control Plane / Hilo Principal GUI)
# =========================================================
class VentanaSCADA(QtWidgets.QMainWindow):
    def __init__(self):
        super(VentanaSCADA, self).__init__()
        
        # 1. Cargamos el diseño que hiciste en Qt Designer
        uic.loadUi('panel.ui', self)
        
        # 2. Instanciamos el hilo de fondo
        self.hilo_modbus = WorkerModbus()
        
        # 3. Conectamos la señal del hilo a nuestra función de actualización
        self.hilo_modbus.datos_actualizados.connect(self.refrescar_pantalla)
        
        # 4. Arrancamos el motor de lectura Modbus
        self.hilo_modbus.start()

    # --- CONFIGURACIÓN DE LOS LCD ---
        # Le decimos que muestren 5 dígitos y que no dibujen sombras 3D (Flat)
        for lcd in [self.Ua, self.Ub, self.Uc]:
            lcd.setDigitCount(5)
            lcd.setSegmentStyle(QtWidgets.QLCDNumber.Flat)

        # --- INYECCIÓN DE QSS (Tema Dark Industrial) ---
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QLabel {
                color: #A0A0A0;
                font-family: "Segoe UI", Arial;
                font-size: 14px;
                font-weight: bold;
            }
            QLCDNumber {
                color: #00FFCC; /* Color Cian Neón para los números */
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 5px;
            }
        """)

    def refrescar_pantalla(self, datos):
        """
        Esta función es llamada automáticamente por la señal 'datos_actualizados'.
        Como los nombres de tus widgets en Designer son "Ua", "Ub" y "Uc",
        PyQt5 los convierte automáticamente en self.Ua, self.Ub, etc.
        """
        self.Ua.display("{:.2f}".format(datos['ua']))
        self.Ub.display("{:.2f}".format(datos['ub']))
        self.Uc.display("{:.2f}".format(datos['uc']))

# =========================================================
# 3. EL BUCLE DE LA APLICACIÓN
# =========================================================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Opcional: Acá luego inyectaremos el QSS (CSS) para que se vea como un SCADA real
    
    ventana = VentanaSCADA()
    ventana.show()
    sys.exit(app.exec_())