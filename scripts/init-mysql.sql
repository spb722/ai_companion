-- Initialize AI Companion Database
-- This script runs automatically when MySQL container starts

USE ai_companion_db;

-- Set charset and collation
ALTER DATABASE ai_companion_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create a simple test table to verify connection
CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'healthy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert a test record
INSERT INTO health_check (status) VALUES ('database_initialized');