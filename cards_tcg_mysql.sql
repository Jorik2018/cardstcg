-- Cards TCG | Esquema compatible con server.py (MySQL 8+ / MariaDB compatible)
-- Seleccionar la base existente en phpMyAdmin antes de importar.
-- No incluye contraseñas ni crea cuentas MySQL.
-- No elimina tablas existentes.

CREATE TABLE IF NOT EXISTS `settings` (
  `key` VARCHAR(100) NOT NULL,
  `value` TEXT NOT NULL,
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `products` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `collection` VARCHAR(100) NOT NULL DEFAULT '',
  `rarity` VARCHAR(80) NOT NULL DEFAULT '',
  `price` DECIMAL(12,2) NOT NULL,
  `stock` INT NOT NULL,
  `image` TEXT NOT NULL,
  `description` TEXT NOT NULL,
  `featured` TINYINT NOT NULL DEFAULT 0,
  `created` BIGINT NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sessions` (
  `token_hash` CHAR(64) NOT NULL,
  `csrf` VARCHAR(128) NOT NULL,
  `expires` BIGINT NOT NULL,
  PRIMARY KEY (`token_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `orders` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `items` LONGTEXT NOT NULL,
  `total` DECIMAL(12,2) NOT NULL,
  `customer` VARCHAR(100) NOT NULL,
  `phone` VARCHAR(30) NOT NULL,
  `status` VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
  `created` BIGINT NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Administradores autorizados. El servidor crea la primera cuenta con
-- ADMIN_USERNAME y ADMIN_PASSWORD, guardando solo un hash scrypt.
CREATE TABLE IF NOT EXISTS `admin_users` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(80) NOT NULL,
  `password_hash` VARCHAR(200) NOT NULL,
  `active` TINYINT NOT NULL DEFAULT 1,
  `created` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_admin_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- El usuario administrador se crea por código Python, NO con una contraseña en SQL.
-- Ejecutar después de importar: python crear_administrador.py --usuario admin
-- Requiere variables de entorno MYSQL_* configuradas en el servidor.
