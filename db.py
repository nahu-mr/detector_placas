# db.py
import mysql.connector
from mysql.connector import Error
import datetime
import time
import math  # ← AGREGADO: necesario para math.ceil()

# Configuración de conexión MySQL (ajusta tus credenciales)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "72048052",
    "database": "control_placas"
}

TARIFA_MINUTO = 0.15   # soles por minuto
COOLDOWN_SEG = 5
_last_seen = {}

def conectar_db():
    return mysql.connector.connect(**DB_CONFIG)

def inicializar_tablas():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS registradas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        placa VARCHAR(15) UNIQUE NOT NULL,
        propietario VARCHAR(100),
        activo TINYINT DEFAULT 1
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entradas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        placa VARCHAR(15) NOT NULL,
        entrada_ts DATETIME NOT NULL,
        salida_ts DATETIME NULL,
        monto DECIMAL(10,2) DEFAULT 0.00,
        procesada TINYINT DEFAULT 0
    ) ENGINE=InnoDB;
    """)
    # Solo crea el índice si no existe
    cur.execute("""
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema = DATABASE() AND table_name='entradas' AND index_name='idx_placa';
    """)
    exists = cur.fetchone()[0]
    if not exists:
        cur.execute("CREATE INDEX idx_placa ON entradas(placa);")
    conn.commit()
    cur.close()
    conn.close()

def puede_procesar_placa(placa):
    ahora = time.time()
    if placa in _last_seen and (ahora - _last_seen[placa]) < COOLDOWN_SEG:
        return False
    _last_seen[placa] = ahora
    return True

def esta_registrada(placa):
    """Verifica si una placa está registrada en la base de datos"""
    try:
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM registradas WHERE UPPER(TRIM(placa)) = UPPER(TRIM(%s))", (placa,))
        resultado = cur.fetchone()[0]
        cur.close()
        conn.close()
        return resultado > 0
    except Exception as e:
        print(f"Error en esta_registrada: {e}")
        return False

def registrar_entrada(placa):
    """Registra una nueva entrada si no hay una activa"""
    try:
        conn = conectar_db()
        cur = conn.cursor()
        
        # Verificar si ya hay una entrada sin procesar
        cur.execute("SELECT id FROM entradas WHERE placa = %s AND procesada = 0", (placa,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return None
        
        # Registrar nueva entrada
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO entradas (placa, entrada_ts, procesada) VALUES (%s, %s, 0)", (placa, ahora))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error en registrar_entrada: {e}")
        return None

def registrar_salida(placa):
    """Registra la salida y calcula el monto a cobrar"""
    try:
        conn = conectar_db()
        cur = conn.cursor(dictionary=True)
        
        # Buscar la última entrada sin procesar
        cur.execute(
            "SELECT id, entrada_ts FROM entradas WHERE placa = %s AND procesada = 0 ORDER BY id DESC LIMIT 1",
            (placa,)
        )
        
        entrada = cur.fetchone()
        if not entrada:
            cur.close()
            conn.close()
            return None
        
        # Calcular tiempo y monto
        entrada_ts = entrada["entrada_ts"]
        salida_ts = datetime.datetime.now()
        segundos = (salida_ts - entrada_ts).total_seconds()
        minutos_reales = segundos / 60
        minutos_cobrados = math.ceil(minutos_reales)
        monto = round(minutos_cobrados * TARIFA_MINUTO, 2)

        # Actualizar el registro
        cur.execute("""
            UPDATE entradas 
            SET salida_ts = %s, monto = %s, procesada = 1 
            WHERE id = %s
        """, (
            salida_ts.strftime("%Y-%m-%d %H:%M:%S"),
            monto,
            entrada["id"]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "placa": placa,
            "entrada": entrada_ts,
            "salida": salida_ts,
            "segundos": segundos,  # ← AGREGADO: necesario para el GUI
            "minutos_reales": round(minutos_reales, 2),
            "minutos_cobrados": minutos_cobrados,
            "monto": monto
        }
    except Exception as e:
        print(f"Error en registrar_salida: {e}")
        import traceback
        traceback.print_exc()
        return None

def registrar_autorizada(placa, propietario):
    """Registra una nueva placa autorizada"""
    try:
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT IGNORE INTO registradas (placa, propietario, activo)
            VALUES (%s, %s, 1)
        """, (placa.upper(), propietario))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error en registrar_autorizada: {e}")
        return False
    
def obtener_registradas():
    """Obtiene todas las placas registradas"""
    try:
        conn = conectar_db()
        cur = conn.cursor()
        cur.execute("SELECT id, placa, propietario, activo FROM registradas")
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        print(f"Error en obtener_registradas: {e}")
        return []

def obtener_movimientos():
    """Obtiene todos los movimientos (entradas y salidas)"""
    try:
        conn = conectar_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, placa, entrada_ts, salida_ts, monto, procesada FROM entradas ORDER BY id DESC")
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        print(f"Error en obtener_movimientos: {e}")
        return []