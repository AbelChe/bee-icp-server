-- MySQL初始化脚本
-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS icp_database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE icp_database;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'icp_user'@'%' IDENTIFIED BY 'icp_password';

-- 授权
GRANT ALL PRIVILEGES ON icp_database.* TO 'icp_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 设置时区
SET time_zone = '+08:00';