CREATE DATABASE IF NOT EXISTS commercehub_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

GRANT ALL PRIVILEGES ON commercehub_test.* TO 'commercehub'@'%';
FLUSH PRIVILEGES;
