# ⚡ Gemelo Digital - Reconectador NOJA OSM27

Este proyecto implementa un simulador físico y lógico del reconectador automático OSM27 mediante Modbus TCP, junto con un SCADA interactivo de consola y una interfaz gráfica en Qt5.

## 🛠️ Instalación y Configuración

**1. Clonar el repositorio:**
Bash:
git clone https://github.com/pablogonzalezcontreras0-commits/Proyecto_OSM27.git
//Moverse a la carpeta
cd Proyecto_OSM27


**2. Crear el entorno virtual:**
* En **Windows**: `python -m venv venv`
* En **Linux**: `python3 -m venv venv`

**3. Activar el entorno virtual:**
* En **Windows**: `.\venv\Scripts\activate`
* En **Linux**: `source venv/bin/activate`

**4. Instalar todas las dependencias:**
Bash:
pip install -r requirements.txt

---

## 🚀 Ejecución del Sistema

El sistema consta de dos partes: el Servidor (Simulador) y el Cliente (SCADA). **Se deben ejecutar en terminales separadas, ambas con el entorno virtual activado.**

### A. Levantar el Simulador (Backend Modbus TCP)
* **Windows:** `python simulador_osm27/main.py`
* **Linux:** `sudo ./venv/bin/python simulador_osm27/main.py` *(Requiere sudo para abrir el puerto 502)*

### B. Levantar el SCADA (Frontend)
Una vez que el servidor esté corriendo, abrí otra terminal, activá el entorno y ejecutá el cliente que prefieras:

**SCADA Táctico de Consola (Interactividad total):**
Bash:
python cliente_interactivo.py

