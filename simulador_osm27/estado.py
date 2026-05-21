import time
import math
from datetime import datetime

class EstadoSimulador:
    """
    Memoria compartida (Single Source of Truth) del equipo OSM27.
    Contiene los valores físicos y lógicos en tiempo real.
    """
    def __init__(self):
        # --- Tensiones de Fase y Línea (V) ---
        self.ua = 13200
        self.ub = 13200
        self.uc = 13200
        self.uab = 22860
        self.ubc = 22860
        self.uca = 22860
        
        # --- Corrientes (A) ---
        self.ia = 150
        self.ib = 150
        self.ic = 150
        
        # --- Potencias y Factor de Potencia ---
        self.kw_total = 3000
        self.kvar_total = 500
        self.kva_total = 3041
        self.factor_potencia = 0.98  # Se escalará x1000 para Modbus
        
        # --- Frecuencia y Energía ---
        self.frecuencia = 50.0  # Se escalará x100 para Modbus
        self.energia_activa_acumulada = 0  # kWh (Cálculo por software)
        self.energia_reactiva_acumulada = 0 # kVArh
        
        # --- Estados Lógicos (Discrete Inputs) ---
        self.estado_cerrado = True
        self.estado_abierto = False
        self.bloqueo_lockout = False
        self.alarma_general = False
        self.warning = False
        self.pickup = False
        self.open_prot = False
        
        # --- Contadores ---
        self.operaciones_totales = 150

        self.estado_fsm = "CERRADO"
        self.tiempo_apertura = 0.0
        self.intentos = 0
        self.max_intentos = 3
        self.dead_time = 5.0
        
        # Flags inyectables desde FastAPI
        self.falla_permanente = False 
        
    def procesar_ciclo(self):
        """
        Esta función se ejecuta a 1 Hz. Representa 1 paso de simulación.
        """
        t_actual = time.time()
        hora_actual = datetime.now().hour # Devuelve un entero de 0 a 23
        
        # ==============================================================
        # BLOQUE 1: DEPENDENCIA TEMPORAL (Perfil de Carga AM)
        # ==============================================================
        # Por defecto, supongamos una carga media del 70%
        multiplicador_carga = 0.7 
        
        if hora_actual in [13, 14, 20, 21, 22]: # Rango de horas pico
            multiplicador_carga = 1.0
        elif 2 <= hora_actual <= 5:             # Rango de madrugada
            multiplicador_carga = 0.4
            
        self.ia = self.ib = self.ic = int(150 * multiplicador_carga)

        # ==============================================================
        # BLOQUE 2: MÁQUINA DE ESTADOS (ANSI 79)
        # ==============================================================
        if self.estado_fsm == "CERRADO":
            if self.falla_permanente:
                self.estado_fsm = "ESPERA"
                self.tiempo_apertura = t_actual
        elif self.estado_fsm == "ESPERA":
            delta = t_actual - self.tiempo_apertura
            if delta >= self.dead_time:
                self.intentos += 1
                if self.intentos >= self.max_intentos:
                    self.estado_fsm = "BLOQUEO"
                else:
                    if self.falla_permanente:
                        self.tiempo_apertura = t_actual
                    else:
                        self.estado_fsm = "CERRADO"
                        self.intentos = 0
        
        # ==============================================================
        # BLOQUE 3: FÍSICA Y ENERGÍA (Procesamiento de Señales)
        # ==============================================================
        if self.estado_fsm == "CERRADO":
            # 1. Asumimos un factor de potencia que varía ligeramente con la carga
            # A más carga, FP más bajo (motores industriales)
            self.factor_potencia = 0.98 if multiplicador_carga < 0.8 else 0.85
            
            # 2. Potencia Aparente S (VA) = sqrt(3) * V_linea * I_linea
            s_va = 1.732 * self.uab * self.ia
            self.kva_total = int(s_va / 1000) # Convertimos a kVA
            
            # 3. Potencias Activa P (kW) y Reactiva Q (kVAr)
            sin_phi = math.sin(math.acos(self.factor_potencia))
            self.kw_total = int(self.kva_total * self.factor_potencia)
            self.kvar_total = int(self.kva_total * sin_phi)
            
            # 4. Integración de Energía (Euler-Forward simple)
            # P [kW] / 3600 segundos te da la porción de kWh de este segundo
            self.energia_activa_acumulada += (self.kw_total / 3600.0)
            self.energia_reactiva_acumulada += (self.kvar_total / 3600.0)
            
            # 5. Actualizamos los flags de Modbus
            self.estado_cerrado = True
            self.estado_abierto = False
            self.bloqueo_lockout = False
        else:
            # En ESPERA o BLOQUEO, es un circuito abierto (I = 0)
            self.ia = self.ib = self.ic = 0
            self.kw_total = self.kvar_total = self.kva_total = 0
            
            self.estado_cerrado = False
            self.estado_abierto = True
            if self.estado_fsm == "BLOQUEO":
                self.bloqueo_lockout = True