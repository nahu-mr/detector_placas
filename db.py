# db.py
import mysql.connector
from mysql.connector import Error
import datetime
import time

# Configuración de conexión MySQL (ajusta tus credenciales)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "72048052",
    "database": "control_placas"
}

TARIFA_HORA = 5.0   # soles por hora
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
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT activo FROM registradas WHERE placa = %s", (placa,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return bool(row and row[0] == 1)

def registrar_entrada(placa):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM entradas WHERE placa = %s AND procesada = 0", (placa,))
    if cur.fetchone():
        cur.close(); conn.close()
        return None
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO entradas (placa, entrada_ts) VALUES (%s, %s)", (placa, ahora))
    conn.commit()
    cur.close(); conn.close()
    return True

def registrar_salida(placa):
    conn = conectar_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, entrada_ts FROM entradas WHERE placa = %s AND procesada = 0 ORDER BY id DESC LIMIT 1", (placa,))
    entrada = cur.fetchone()
    if not entrada:
        cur.close(); conn.close()
        return None
    entrada_ts = entrada["entrada_ts"]
    salida_ts = datetime.datetime.now()
    segundos = (salida_ts - entrada_ts).total_seconds()
    monto = round((segundos / 3600) * TARIFA_HORA, 2)
    cur.execute("""
        UPDATE entradas SET salida_ts = %s, monto = %s, procesada = 1 WHERE id = %s
    """, (salida_ts.strftime("%Y-%m-%d %H:%M:%S"), monto, entrada["id"]))
    conn.commit()
    cur.close(); conn.close()
    return {"placa": placa, "entrada": entrada_ts, "salida": salida_ts, "monto": monto, "segundos": segundos}

def registrar_autorizada(placa, propietario):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT IGNORE INTO registradas (placa, propietario, activo)
        VALUES (%s, %s, 1)
    """, (placa.upper(), propietario))
    conn.commit()
    cur.close(); conn.close()
    
    
def obtener_registradas():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT id, placa, propietario, activo FROM registradas")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def obtener_movimientos():
    conn = conectar_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, placa, entrada_ts, salida_ts, monto, procesada FROM entradas ORDER BY id ASC")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data
