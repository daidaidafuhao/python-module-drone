-- 机器配置表
CREATE TABLE IF NOT EXISTS `machine_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `machine_name` varchar(50) NOT NULL COMMENT '机器名称',
  `host` varchar(255) NOT NULL COMMENT 'PLC主机地址',
  `port` int NOT NULL COMMENT 'PLC端口号',
  `description` varchar(200) DEFAULT NULL COMMENT '机器描述',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_machine_name` (`machine_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='机器配置表';

-- 插入默认机器配置
INSERT INTO `machine_config` (`machine_name`, `host`, `port`, `description`, `is_active`) VALUES
('default', '127.0.0.1', 502, '默认PLC机器', 1),
('machine_001', '192.168.1.100', 502, '1号无人机柜', 1),
('machine_002', '192.168.1.101', 502, '2号无人机柜', 1);