CREATE DATABASE IF NOT EXISTS control_placas CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE control_placas;

-- Vehículos registrados (autorizados)
CREATE TABLE registradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(15) UNIQUE NOT NULL,
    propietario VARCHAR(100),
    activo TINYINT DEFAULT 1
);

INSERT INTO control_registrada (placa, propietario) VALUES
('ABC-123', 'Juan Pérez'),
('XYZ-987', 'María Torres'),
('MNO-456', 'Carlos Ramírez'),
('TRU-789', 'Ana Flores');


-- Vehículos en entradas y salidas
CREATE TABLE entradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(15) NOT NULL,
    entrada_ts DATETIME NOT NULL,
    salida_ts DATETIME NULL,
    monto DECIMAL(10,2) DEFAULT 0.00,
    procesada TINYINT DEFAULT 0
);

-- Ejemplos de movimientos
INSERT INTO control_entrada (placa, entrada, salida, monto, procesada) VALUES
('ABC-123', NOW() - INTERVAL 30 MINUTE, NOW(), 4.50, 1),
('XYZ-987', NOW() - INTERVAL 10 MINUTE, NULL, 0.00, 0),
('MNO-456', NOW() - INTERVAL 45 MINUTE, NOW(), 6.75, 1);
