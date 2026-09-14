CREATE DATABASE IF NOT EXISTS campus_swap;
USE campus_swap;

CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    first_name      VARCHAR(60)  NOT NULL,
    last_name       VARCHAR(60)  DEFAULT '',
    email           VARCHAR(120) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    phone           VARCHAR(20)  DEFAULT NULL,
    bio             TEXT         DEFAULT NULL,
    campus          VARCHAR(100) DEFAULT NULL,
    hostel_block    VARCHAR(50)  DEFAULT NULL,
    department      VARCHAR(50)  DEFAULT NULL,
    reg_number      VARCHAR(50)  DEFAULT NULL,
    semester_year   VARCHAR(50)  DEFAULT NULL,
    room_alt        VARCHAR(50)  DEFAULT NULL,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS items (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    seller_id       INT NOT NULL,
    title           VARCHAR(150) NOT NULL,
    description     TEXT,
    price           DECIMAL(10, 2) NOT NULL DEFAULT 0,
    category        VARCHAR(50) NOT NULL,
    item_condition  VARCHAR(20) NOT NULL,
    image_url       VARCHAR(255) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE INDEX idx_items_category ON items (category);
CREATE INDEX idx_items_seller   ON items (seller_id);
