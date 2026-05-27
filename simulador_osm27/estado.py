import time
import random
from datetime import datetime

class EstadoSimulador:
    def __init__(self):
        # Nominales y Físicos
        self.v_fase_nom = 13200
        self.i_nom = 105
        self.fp_carga = 0.95
        self.carga_actual = 1.0
        
        # Máquina de Estados (ANSI 79)
        self.estado_fsm = "CERRADO"
        self.tiempo_apertura = 0.0
        self.intentos = 0
        self.max_intentos = 3
        self.dead_time = 5.0
        
        # Flags de Inyección
        self.falla_permanente = False
        self.falla_transitoria = False
        self.falla_tension = False # Hueco de tensión (Sag)
        self.tiempo_inicio_sag = 0.0
        self.duracion_sag = 0.0
        
        # Telemetría Modbus
        self.pickup = False
        self.open_prot = False
        self.bloqueo_lockout = False
        self.alarma_general = False
        self.alarma_tension = False
        self.operaciones_totales = 150
        self.energia_activa_acumulada = 100000.0
        self.energia_reactiva_acumulada = 25000.0
        
        # Cola interna de eventos
        self.eventos_pendientes = []

    def log_evento(self, mensaje):
        self.eventos_pendientes.append(mensaje)

    def procesar_ciclo(self):
        t_actual = time.time()
        
        # 1. PERFIL DE CARGA (Curva AM)
        hora = datetime.now().hour
        self.carga_actual = 1.0 if hora in [13, 14, 20, 21, 22] else (0.4 if 2 <= hora <= 5 else 0.7)
        
        # 2. MÁQUINA DE ESTADOS (ANSI 79)
        if self.estado_fsm == "CERRADO":
            if self.falla_permanente or self.falla_transitoria:
                self.estado_fsm = "ESPERA"
                self.pickup = True
                self.open_prot = True
                self.tiempo_apertura = t_actual
                self.operaciones_totales += 1
                self.log_evento(f"⚠️ DISPARO: Sobrecorriente. Abriendo contactos. (Op: {self.operaciones_totales})")
            else:
                self.intentos = 0
                self.pickup = False
                
        elif self.estado_fsm == "ESPERA":
            if t_actual - self.tiempo_apertura >= self.dead_time:
                self.intentos += 1
                if self.intentos >= self.max_intentos:
                    self.estado_fsm = "BLOQUEO"
                    self.bloqueo_lockout = True
                    self.alarma_general = True
                    self.log_evento("❌ BLOQUEO (Lockout): Intentos agotados. Falla permanente en la línea.")
                else:
                    self.estado_fsm = "CERRADO"
                    self.open_prot = False
                    self.log_evento(f"🔄 REENGANCHE: Intento {self.intentos}/{self.max_intentos}. Cerrando contactos.")
                    if self.falla_transitoria:
                        self.falla_transitoria = False
                        self.log_evento("✅ Falla transitoria despejada. Línea estabilizada.")
                        
        elif self.estado_fsm == "BLOQUEO":
            if not self.falla_permanente and not self.falla_transitoria:
                self.estado_fsm = "CERRADO"
                self.bloqueo_lockout = False
                self.alarma_general = False
                self.intentos = 0
                self.log_evento("🔧 RESET: Operario restableció el equipo. Línea Viva.")

        # 3. INYECCIÓN DE SAG DE TENSIÓN (HUECO DE TENSIÓN)
        if self.falla_tension:
            # Si recién arranca el sag
            if self.tiempo_inicio_sag == 0.0:
                self.tiempo_inicio_sag = t_actual
                # Simulamos la duración típica del arranque de un motor pesado (1 a 5 segundos)
                self.duracion_sag = random.uniform(1.0, 5.0) 
                self.alarma_tension = True
                self.log_evento(f"⚡ ALARMA: Hueco de tensión (SAG) detectado. Motor arrancando...")
            
            # Chequeamos si ya pasó el tiempo de inrush
            elif t_actual - self.tiempo_inicio_sag >= self.duracion_sag:
                self.falla_tension = False
                self.alarma_tension = False
                self.tiempo_inicio_sag = 0.0
                self.log_evento("✅ SAG superado. Tensión de red normalizada.")
        else:
            self.tiempo_inicio_sag = 0.0
            self.alarma_tension = False