CREATE DATABASE IF NOT EXISTS control_placas CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE control_placas;

-- Vehículos registrados (autorizados)
CREATE TABLE registradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(15) UNIQUE NOT NULL,
    propietario VARCHAR(100)
);
-- Vehículos en entradas y salidas
CREATE TABLE entradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(15) NOT NULL,
    entrada_ts DATETIME NOT NULL,
    salida_ts DATETIME NULL,
    monto DECIMAL(10,2) DEFAULT 0.00,
    procesada TINYINT DEFAULT 0
);
