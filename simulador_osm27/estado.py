import time
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
        # TODO: Escribí una lógica simple que modifique un "multiplicador_carga" 
        # Si la hora es el pico (ej. 13 o 21), el multiplicador es 1.0 (100%)
        # Si es de madrugada (ej. 3 AM), el multiplicador baja a 0.4 (40%)
        # Luego, aplicá ese multiplicador a las corrientes nominales (Ia, Ib, Ic).
        
        
        # ==============================================================
        # BLOQUE 2: MÁQUINA DE ESTADOS (ANSI 79)
        # ==============================================================
        # TODO: Implementá la lógica que pensaste usando t_actual y self.tiempo_apertura.
        # Si estado es CERRADO y hay falla -> Cambiar a ESPERA, guardar t_actual en tiempo_apertura.
        # Si estado es ESPERA -> Evaluar el delta. Si pasó el dead_time:
        #      -> Sumar 1 a intentos.
        #      -> Si intentos >= max_intentos -> Cambiar a BLOQUEO.
        #      -> Si no, y la falla sigue activa -> Renovar tiempo_apertura (nuevo Trip).
        #      -> Si la falla desapareció -> Volver a CERRADO, resetear intentos.
        
        
        # ==============================================================
        # BLOQUE 3: FÍSICA Y ENERGÍA (Procesamiento de Señales)
        # ==============================================================
        if self.estado_fsm == "CERRADO":
            # TODO: Calcular Potencia Aparente (S = raiz(3) * V_linea * I_linea)
            # Calcular Potencia Activa (P = S * cos_phi) y Reactiva (Q = S * sin_phi)
            # Integrar la Energía Activa Acumulada (E = E_anterior + P / 3600)
            pass
        else:
            # En ESPERA o BLOQUEO, las potencias y corrientes caen a 0.
            pass

    def inyectar_falla_sobrecorriente(self, activa: bool):
        """Lógica simple para simular un disparo por sobrecorriente."""
        if activa:
            self.ia = 8000  # 8 kA de falla
            self.estado_cerrado = False
            self.estado_abierto = True
            self.pickup = True
            self.open_prot = True
            self.alarma_general = True
        else:
            self.ia = 150
            self.estado_cerrado = True
            self.estado_abierto = False
            self.pickup = False
            self.open_prot = False
            self.alarma_general = False
    