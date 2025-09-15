-- 创建无人机柜表
CREATE TABLE `drone_cabinet` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `name` varchar(50) NOT NULL COMMENT '柜子名称',
    `code` varchar(20) NOT NULL COMMENT '柜子编号',
    `ip` varchar(15) NOT NULL COMMENT 'Modbus IP地址',
    `port` int NOT NULL COMMENT 'Modbus端口',
    `slave_id` int NOT NULL COMMENT 'Modbus从站ID',
    `address` varchar(200) NOT NULL COMMENT '实际地址',
    `longitude` decimal(10,6) DEFAULT NULL COMMENT '经度',
    `latitude` decimal(10,6) DEFAULT NULL COMMENT '纬度',
    `status` tinyint NOT NULL DEFAULT '0' COMMENT '状态（0-离线 1-在线 2-故障）',
    `total_boxes` int NOT NULL COMMENT '总格口数',
    `available_boxes` int NOT NULL COMMENT '可用格口数',
    `last_online_time` datetime DEFAULT NULL COMMENT '最后在线时间',
    `last_offline_time` datetime DEFAULT NULL COMMENT '最后离线时间',
    `last_error_time` datetime DEFAULT NULL COMMENT '最后故障时间',
    `error_message` varchar(500) DEFAULT NULL COMMENT '故障信息',
    `remark` varchar(500) DEFAULT NULL COMMENT '备注',
    `creator` varchar(64) DEFAULT '' COMMENT '创建者',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updater` varchar(64) DEFAULT '' COMMENT '更新者',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` bit(1) NOT NULL DEFAULT b'0' COMMENT '是否删除',
     `tenant_id` bigint NOT NULL DEFAULT 0 COMMENT '租户编号',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_code` (`code`),
    KEY `idx_status` (`status`),
    KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='无人机柜表';

-- 创建无人机柜操作日志表
CREATE TABLE `drone_cabinet_log` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cabinet_id` bigint NOT NULL COMMENT '柜子ID',
    `operation_type` varchar(20) NOT NULL COMMENT '操作类型',
    `operation_result` tinyint NOT NULL COMMENT '操作结果（0-失败 1-成功）',
    `error_message` varchar(500) DEFAULT NULL COMMENT '错误信息',
    `operator` varchar(64) DEFAULT '' COMMENT '操作人',
    `operation_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    `remark` varchar(500) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_cabinet_id` (`cabinet_id`),
    KEY `idx_operation_time` (`operation_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='无人机柜操作日志表';

-- 创建无人机柜格口表
CREATE TABLE `drone_cabinet_box` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cabinet_id` bigint NOT NULL COMMENT '柜子ID',
    `box_no` varchar(20) NOT NULL COMMENT '格口号',
    `status` tinyint NOT NULL DEFAULT '0' COMMENT '状态（0-空闲 1-占用 2-故障）',
    `package_code` varchar(50) DEFAULT NULL COMMENT '包裹编号',
    `pickup_code` varchar(20) DEFAULT NULL COMMENT '取件码',
    `last_operation_time` datetime DEFAULT NULL COMMENT '最后操作时间',
    `last_operation_type` varchar(20) DEFAULT NULL COMMENT '最后操作类型',
    `remark` varchar(500) DEFAULT NULL COMMENT '备注',
    `creator` varchar(64) DEFAULT '' COMMENT '创建者',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updater` varchar(64) DEFAULT '' COMMENT '更新者',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` bit(1) NOT NULL DEFAULT b'0' COMMENT '是否删除',
     `tenant_id` bigint NOT NULL DEFAULT 0 COMMENT '租户编号',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cabinet_box_no` (`cabinet_id`, `box_no`),
    KEY `idx_status` (`status`),
    KEY `idx_package_code` (`package_code`),
    KEY `idx_pickup_code` (`pickup_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='无人机柜格口表';

-- 插入测试数据
INSERT INTO `drone_cabinet` 
(`name`, `code`, `ip`, `port`, `slave_id`, `address`, `longitude`, `latitude`, `status`, `total_boxes`, `available_boxes`, `remark`, `tenant_id`) 
VALUES 
('测试柜1', 'DC001', '192.168.1.100', 502, 1, '浙江省杭州市西湖区文三路123号', 120.123456, 30.123456, 1, 20, 20, '测试柜1号', 1),
('测试柜2', 'DC002', '192.168.1.101', 502, 1, '浙江省杭州市拱墅区莫干山路456号', 120.234567, 30.234567, 1, 20, 20, '测试柜2号', 1); 