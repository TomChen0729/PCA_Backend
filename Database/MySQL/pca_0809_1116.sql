-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主機： 127.0.0.1
-- 產生時間： 2026-08-09 17:16:32
-- 伺服器版本： 10.4.32-MariaDB
-- PHP 版本： 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 資料庫： `pca`
--
CREATE DATABASE IF NOT EXISTS `pca` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `pca`;

-- --------------------------------------------------------

--
-- 資料表結構 `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 資料表新增資料前，先清除舊資料 `alembic_version`
--

TRUNCATE TABLE `alembic_version`;
--
-- 傾印資料表的資料 `alembic_version`
--

INSERT INTO `alembic_version` (`version_num`) VALUES
('59df4eaf514b');

-- --------------------------------------------------------

--
-- 資料表結構 `analysis_results`
--

DROP TABLE IF EXISTS `analysis_results`;
CREATE TABLE `analysis_results` (
  `id` int(11) NOT NULL COMMENT '診斷紀錄唯一識別碼',
  `uid` int(11) NOT NULL COMMENT '受測使用者 ID',
  `faceImg` varchar(255) NOT NULL COMMENT '使用者用於分析的臉部照片路徑',
  `tid` int(11) NOT NULL COMMENT '分析結果隸屬的色彩型別 ID',
  `timestamp` datetime DEFAULT NULL COMMENT '測色時間戳記'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='PCA 診斷紀錄表 (儲存使用者每次的測色結果)';

--
-- 資料表新增資料前，先清除舊資料 `analysis_results`
--

TRUNCATE TABLE `analysis_results`;
-- --------------------------------------------------------

--
-- 資料表結構 `colors_for_type`
--

DROP TABLE IF EXISTS `colors_for_type`;
CREATE TABLE `colors_for_type` (
  `id` int(11) NOT NULL COMMENT '顏色識別碼',
  `tid` int(11) NOT NULL COMMENT '對應的色彩型別 ID',
  `label` varchar(50) DEFAULT NULL COMMENT '適合的顏色值（色碼標籤）',
  `color` varchar(30) NOT NULL COMMENT '適合的顏色值 (HEX 或 RGB)',
  `timestamp` datetime DEFAULT NULL COMMENT '建立時間戳記'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='色彩庫 (定義各型別適合的具體顏色)';

--
-- 資料表新增資料前，先清除舊資料 `colors_for_type`
--

TRUNCATE TABLE `colors_for_type`;
--
-- 傾印資料表的資料 `colors_for_type`
--

INSERT INTO `colors_for_type` (`id`, `tid`, `label`, `color`, `timestamp`) VALUES
(1, 1, '珊瑚紅', '#FF6F61', '2026-08-09 22:09:36'),
(2, 1, '亮橘紅', '#FF5A36', '2026-08-09 22:09:36'),
(3, 1, '鮮橘色', '#FF8C42', '2026-08-09 22:09:36'),
(4, 1, '陽光黃', '#FFD93D', '2026-08-09 22:09:36'),
(5, 1, '蘋果綠', '#7ED957', '2026-08-09 22:09:36'),
(6, 1, '亮青綠', '#00BFA6', '2026-08-09 22:09:36'),
(7, 1, '湖水藍', '#32C5D2', '2026-08-09 22:09:36'),
(8, 1, '亮桃紅', '#FF5C8A', '2026-08-09 22:09:36'),
(9, 2, '蜜桃色', '#FFB07C', '2026-08-09 22:09:36'),
(10, 2, '杏桃色', '#FFA45B', '2026-08-09 22:09:36'),
(11, 2, '珊瑚粉', '#FF7F6A', '2026-08-09 22:09:36'),
(12, 2, '番茄紅', '#E9543F', '2026-08-09 22:09:36'),
(13, 2, '金黃色', '#F6C344', '2026-08-09 22:09:36'),
(14, 2, '駝色', '#C9955D', '2026-08-09 22:09:36'),
(15, 2, '嫩葉綠', '#8DBF67', '2026-08-09 22:09:36'),
(16, 2, '暖青綠', '#3BAF9F', '2026-08-09 22:09:36'),
(17, 3, '淺蜜桃', '#FFD0B5', '2026-08-09 22:09:36'),
(18, 3, '杏仁奶油', '#FFE0A8', '2026-08-09 22:09:36'),
(19, 3, '淺珊瑚粉', '#FFAAA5', '2026-08-09 22:09:36'),
(20, 3, '奶油黃', '#FFF1A8', '2026-08-09 22:09:36'),
(21, 3, '嫩芽綠', '#B9DB9B', '2026-08-09 22:09:36'),
(22, 3, '薄荷綠', '#A8E6CF', '2026-08-09 22:09:36'),
(23, 3, '淺水藍', '#A9DDEB', '2026-08-09 22:09:36'),
(24, 3, '象牙白', '#FFF8E7', '2026-08-09 22:09:36'),
(25, 4, '櫻花粉', '#F4C2C2', '2026-08-09 22:09:36'),
(26, 4, '玫瑰粉', '#E8B4C4', '2026-08-09 22:09:36'),
(27, 4, '薰衣草紫', '#C8B6D9', '2026-08-09 22:09:36'),
(28, 4, '粉霧藍', '#B7C9E2', '2026-08-09 22:09:36'),
(29, 4, '天空藍', '#ADD8E6', '2026-08-09 22:09:36'),
(30, 4, '薄荷藍', '#B8E0D2', '2026-08-09 22:09:36'),
(31, 4, '珍珠灰', '#D8D8DC', '2026-08-09 22:09:36'),
(32, 4, '柔霧紫', '#D5C6E0', '2026-08-09 22:09:36'),
(33, 5, '冷玫瑰', '#C97C91', '2026-08-09 22:09:36'),
(34, 5, '莓果粉', '#B65D7A', '2026-08-09 22:09:36'),
(35, 5, '冷粉紅', '#D989A6', '2026-08-09 22:09:36'),
(36, 5, '薰衣草紫', '#A998C8', '2026-08-09 22:09:36'),
(37, 5, '冷湖藍', '#6FAFC4', '2026-08-09 22:09:36'),
(38, 5, '灰藍色', '#7895B2', '2026-08-09 22:09:36'),
(39, 5, '冷青綠', '#5EAAA8', '2026-08-09 22:09:36'),
(40, 5, '冷灰色', '#9DA7B1', '2026-08-09 22:09:36'),
(41, 6, '乾燥玫瑰', '#B7848C', '2026-08-09 22:09:36'),
(42, 6, '灰粉色', '#BFA0A8', '2026-08-09 22:09:36'),
(43, 6, '藕紫色', '#9C8295', '2026-08-09 22:09:36'),
(44, 6, '霧紫色', '#9587A3', '2026-08-09 22:09:36'),
(45, 6, '灰藍色', '#8294A6', '2026-08-09 22:09:36'),
(46, 6, '煙霧藍', '#78909C', '2026-08-09 22:09:36'),
(47, 6, '鼠尾草綠', '#8FA89B', '2026-08-09 22:09:36'),
(48, 6, '冷灰褐', '#9B9290', '2026-08-09 22:09:36'),
(49, 7, '陶土粉', '#C98276', '2026-08-09 22:09:36'),
(50, 7, '乾燥杏桃', '#D49A7A', '2026-08-09 22:09:36'),
(51, 7, '柔磚紅', '#A65F50', '2026-08-09 22:09:36'),
(52, 7, '鼠尾草綠', '#929B76', '2026-08-09 22:09:36'),
(53, 7, '橄欖綠', '#7F8453', '2026-08-09 22:09:36'),
(54, 7, '灰青綠', '#668B83', '2026-08-09 22:09:36'),
(55, 7, '柔駝色', '#B89572', '2026-08-09 22:09:36'),
(56, 7, '摩卡棕', '#8B6F5E', '2026-08-09 22:09:36'),
(57, 8, '南瓜橘', '#D9782D', '2026-08-09 22:09:36'),
(58, 8, '焦糖橘', '#C96A32', '2026-08-09 22:09:36'),
(59, 8, '磚紅色', '#B55239', '2026-08-09 22:09:36'),
(60, 8, '芥末黃', '#C99A2E', '2026-08-09 22:09:36'),
(61, 8, '橄欖綠', '#747A32', '2026-08-09 22:09:36'),
(62, 8, '森林綠', '#556B3F', '2026-08-09 22:09:36'),
(63, 8, '焦糖棕', '#A66A3F', '2026-08-09 22:09:36'),
(64, 8, '巧克力棕', '#70483C', '2026-08-09 22:09:36'),
(65, 9, '酒紅色', '#7A3038', '2026-08-09 22:09:36'),
(66, 9, '深磚紅', '#7F3F32', '2026-08-09 22:09:36'),
(67, 9, '鐵鏽紅', '#9A4A2F', '2026-08-09 22:09:36'),
(68, 9, '深橄欖綠', '#535B35', '2026-08-09 22:09:36'),
(69, 9, '森林綠', '#354F3D', '2026-08-09 22:09:36'),
(70, 9, '深青綠', '#285C58', '2026-08-09 22:09:36'),
(71, 9, '深咖啡', '#533B32', '2026-08-09 22:09:36'),
(72, 9, '濃駝色', '#8A6847', '2026-08-09 22:09:36'),
(73, 10, '正紅色', '#E60026', '2026-08-09 22:09:36'),
(74, 10, '桃紅色', '#F0007C', '2026-08-09 22:09:36'),
(75, 10, '亮洋紅', '#D600A9', '2026-08-09 22:09:36'),
(76, 10, '寶藍色', '#0057D9', '2026-08-09 22:09:36'),
(77, 10, '電光藍', '#0077FF', '2026-08-09 22:09:36'),
(78, 10, '祖母綠', '#009B77', '2026-08-09 22:09:36'),
(79, 10, '皇家紫', '#7030A0', '2026-08-09 22:09:36'),
(80, 10, '純黑色', '#000000', '2026-08-09 22:09:36'),
(81, 11, '冷正紅', '#C8102E', '2026-08-09 22:09:36'),
(82, 11, '莓果紅', '#A50044', '2026-08-09 22:09:36'),
(83, 11, '洋紅色', '#C2185B', '2026-08-09 22:09:36'),
(84, 11, '寶石藍', '#0047AB', '2026-08-09 22:09:36'),
(85, 11, '鈷藍色', '#0047BB', '2026-08-09 22:09:36'),
(86, 11, '冷紫色', '#663399', '2026-08-09 22:09:36'),
(87, 11, '冰粉色', '#F2D5E5', '2026-08-09 22:09:36'),
(88, 11, '炭灰色', '#3D4147', '2026-08-09 22:09:36'),
(89, 12, '深酒紅', '#681C32', '2026-08-09 22:09:36'),
(90, 12, '黑櫻桃紅', '#5C1A2D', '2026-08-09 22:09:36'),
(91, 12, '深莓紅', '#751A3D', '2026-08-09 22:09:36'),
(92, 12, '深紫色', '#482D59', '2026-08-09 22:09:36'),
(93, 12, '深海軍藍', '#172A46', '2026-08-09 22:09:36'),
(94, 12, '深青綠', '#174E4F', '2026-08-09 22:09:36'),
(95, 12, '深祖母綠', '#0B533D', '2026-08-09 22:09:36'),
(96, 12, '純黑色', '#000000', '2026-08-09 22:09:36');

-- --------------------------------------------------------

--
-- 資料表結構 `seasons`
--

DROP TABLE IF EXISTS `seasons`;
CREATE TABLE `seasons` (
  `id` int(11) NOT NULL COMMENT '季節唯一識別碼',
  `name` varchar(20) NOT NULL COMMENT '季節名稱 (例如：春季型)',
  `timestamp` datetime DEFAULT NULL COMMENT '建立時間戳記'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='大季節分類表 (春、夏、秋、冬)';

--
-- 資料表新增資料前，先清除舊資料 `seasons`
--

TRUNCATE TABLE `seasons`;
--
-- 傾印資料表的資料 `seasons`
--

INSERT INTO `seasons` (`id`, `name`, `timestamp`) VALUES
(1, '春(Spring)', '2026-08-09 22:13:17'),
(2, '夏(Summer)', '2026-08-09 22:13:22'),
(3, '秋(Autumn)', '2026-08-09 22:13:23'),
(4, '冬(Winter)', '2026-08-09 22:13:25');

-- --------------------------------------------------------

--
-- 資料表結構 `types`
--

DROP TABLE IF EXISTS `types`;
CREATE TABLE `types` (
  `id` int(11) NOT NULL COMMENT '型別唯一識別碼',
  `sid` int(11) NOT NULL COMMENT '隸屬的大季節 ID',
  `name` varchar(50) NOT NULL COMMENT '型別名稱 (例如：淺春型)',
  `eng_name` varchar(50) DEFAULT NULL COMMENT '英文型別名稱 (例如：Light Spring)',
  `description` text DEFAULT NULL COMMENT '該型別的特徵描述與穿搭建議',
  `timestamp` datetime DEFAULT NULL COMMENT '建立時間戳記'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='色彩型別表 (季節下的細分)';

--
-- 資料表新增資料前，先清除舊資料 `types`
--

TRUNCATE TABLE `types`;
--
-- 傾印資料表的資料 `types`
--

INSERT INTO `types` (`id`, `sid`, `name`, `eng_name`, `description`, `timestamp`) VALUES
(1, 1, '亮春', 'Spring Bright', NULL, '2026-08-09 22:14:20'),
(2, 1, '暖春', 'Spring Warm', NULL, '2026-08-09 22:14:21'),
(3, 1, '淺春', 'Spring Light', NULL, '2026-08-09 22:14:23'),
(4, 2, '淺夏', 'Summer Light', NULL, '2026-08-09 22:14:24'),
(5, 2, '冷夏', 'Summer Cool', NULL, '2026-08-09 22:14:26'),
(6, 2, '柔夏', 'Summer Mute', NULL, '2026-08-09 22:14:27'),
(7, 3, '柔秋', 'Autumn Mute', NULL, '2026-08-09 22:14:28'),
(8, 3, '暖秋', 'Autumn Warm', NULL, '2026-08-09 22:14:30'),
(9, 3, '深秋', 'Autumn Deep', NULL, '2026-08-09 22:14:31'),
(10, 4, '亮冬', 'Winter Bright', NULL, '2026-08-09 22:14:32'),
(11, 4, '冷冬', 'Winter Cool', NULL, '2026-08-09 22:14:34'),
(12, 4, '深冬', 'Winter Deep', NULL, '2026-08-09 22:14:35');

-- --------------------------------------------------------

--
-- 資料表結構 `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` int(11) NOT NULL COMMENT '使用者唯一識別碼',
  `username` varchar(50) NOT NULL COMMENT '登入帳號名稱',
  `mail` varchar(120) NOT NULL COMMENT '聯絡與註冊信箱',
  `pwd` varchar(255) NOT NULL COMMENT '加密後的密碼 (Hash)',
  `timestamp` datetime DEFAULT NULL COMMENT '紀錄建立時間'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='使用者基本資料表 (管理帳號密碼與個人資訊)';

--
-- 資料表新增資料前，先清除舊資料 `users`
--

TRUNCATE TABLE `users`;
--
-- 傾印資料表的資料 `users`
--

INSERT INTO `users` (`id`, `username`, `mail`, `pwd`, `timestamp`) VALUES
(2, 'test1', 'test1@gmail.com', 'scrypt:32768:8:1$VHX3MEEFpWddrNFb$74e11a19fd421c09cc53c6a543ca5ef572db62bc0ecd1aa365319c8b5bc1f81aef434b6cdf5f3d2ce21881c71d30acbe34a66f0f0ea5e986f49d4bd54de3eb3f', '2026-06-28 10:49:41'),
(3, 's1411031032', 'ttom98075@gmail.com', 'scrypt:32768:8:1$yKVc4JuKjejP0sqa$7c276e46348521b0c84dcbf5180cbda31104234b5190f1c53368c29b33cea43bcc5770599ed5a9efd6820d749bf19b110e2ef7a2808391bbaa011e2a8ca0fd5c', '2026-08-05 14:39:28'),
(4, 'ttt', 'tom98075@gmail.com', 'scrypt:32768:8:1$COlbnZ086xvYRq3O$62de1c82339ee40b827861e81cbb40a11ae24c01caf19cf4d26da852a3cc37fb666172215050cb4cd16754b1e3e9b972b3b2a144ba55fa3953861a0990f7df20', '2026-08-08 10:23:09');

-- --------------------------------------------------------

--
-- 資料表結構 `wardrobe_items`
--

DROP TABLE IF EXISTS `wardrobe_items`;
CREATE TABLE `wardrobe_items` (
  `id` int(11) NOT NULL COMMENT '單品唯一識別碼',
  `uid` int(11) NOT NULL COMMENT '擁有此衣服的使用者 ID',
  `tag` enum('top','bottom') NOT NULL COMMENT '衣服分類標籤',
  `imgPath` varchar(255) NOT NULL COMMENT '圖片儲存路徑 (實體檔案路徑或雲端網址)',
  `color_1` varchar(30) DEFAULT NULL COMMENT 'KMeans 抓出的主要顏色 1 (RGB)',
  `color_2` varchar(30) DEFAULT NULL COMMENT 'KMeans 抓出的主要顏色 2 (RGB)',
  `color_3` varchar(30) DEFAULT NULL COMMENT 'KMeans 抓出的主要顏色 3 (RGB)',
  `timestamp` datetime DEFAULT NULL COMMENT '建立時間戳記'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='衣櫥單品資料表 (儲存使用者上傳並去背的衣服)';

--
-- 資料表新增資料前，先清除舊資料 `wardrobe_items`
--

TRUNCATE TABLE `wardrobe_items`;
--
-- 傾印資料表的資料 `wardrobe_items`
--

INSERT INTO `wardrobe_items` (`id`, `uid`, `tag`, `imgPath`, `color_1`, `color_2`, `color_3`, `timestamp`) VALUES
(5, 2, 'top', 'static/uploads/2/top/9f854165b83744bebdaa35ecebb8f036.png', '42,42,44', '27,26,28', '185,136,116', '2026-06-28 11:25:13'),
(6, 2, 'top', 'static/uploads/2/top/c80dacbe04474a7c902fdc3bd021891d.png', '42,42,44', '27,26,28', '185,136,116', '2026-06-28 11:56:04'),
(7, 2, 'top', 'static/uploads/2/top/a3d057f77c4c4e6597b24c917e161cda.png', '25,24,29', '199,155,133', '229,193,172', '2026-06-28 12:13:53'),
(8, 2, 'top', 'static/uploads/2/top/d703a35ce04349559efe8f42fce914b1.png', '25,24,29', '199,155,133', '229,193,172', '2026-06-28 12:23:50'),
(9, 2, 'top', 'static/uploads/2/top/d378eb7721d646c7a085ab5f8254f7d4.png', '42,42,44', '27,26,28', '185,136,116', '2026-06-28 12:23:58'),
(10, 2, 'top', 'static/uploads/2/top/d1f52d0d6ec6457d91833852023c08cb.png', '97,33,49', '51,22,34', '151,37,60', '2026-06-28 12:24:29'),
(11, 3, 'top', 'static/uploads/3/top/b2306c00d8494d37aa9c82675bc7c244.png', '42,42,44', '27,26,28', '185,136,116', '2026-08-05 14:40:51'),
(12, 3, 'top', 'static/uploads/3/top/3881572e16514f5a88e03c3641c72832.png', '25,24,29', '199,155,133', '229,193,172', '2026-08-05 14:41:21');

--
-- 已傾印資料表的索引
--

--
-- 資料表索引 `alembic_version`
--
ALTER TABLE `alembic_version`
  ADD PRIMARY KEY (`version_num`);

--
-- 資料表索引 `analysis_results`
--
ALTER TABLE `analysis_results`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tid` (`tid`),
  ADD KEY `uid` (`uid`);

--
-- 資料表索引 `colors_for_type`
--
ALTER TABLE `colors_for_type`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tid` (`tid`);

--
-- 資料表索引 `seasons`
--
ALTER TABLE `seasons`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- 資料表索引 `types`
--
ALTER TABLE `types`
  ADD PRIMARY KEY (`id`),
  ADD KEY `sid` (`sid`);

--
-- 資料表索引 `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `mail` (`mail`);

--
-- 資料表索引 `wardrobe_items`
--
ALTER TABLE `wardrobe_items`
  ADD PRIMARY KEY (`id`),
  ADD KEY `uid` (`uid`);

--
-- 在傾印的資料表使用自動遞增(AUTO_INCREMENT)
--

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `analysis_results`
--
ALTER TABLE `analysis_results`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '診斷紀錄唯一識別碼';

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `colors_for_type`
--
ALTER TABLE `colors_for_type`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '顏色識別碼', AUTO_INCREMENT=97;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `seasons`
--
ALTER TABLE `seasons`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '季節唯一識別碼', AUTO_INCREMENT=5;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `types`
--
ALTER TABLE `types`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '型別唯一識別碼', AUTO_INCREMENT=13;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '使用者唯一識別碼', AUTO_INCREMENT=5;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `wardrobe_items`
--
ALTER TABLE `wardrobe_items`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '單品唯一識別碼', AUTO_INCREMENT=14;

--
-- 已傾印資料表的限制式
--

--
-- 資料表的限制式 `analysis_results`
--
ALTER TABLE `analysis_results`
  ADD CONSTRAINT `analysis_results_ibfk_1` FOREIGN KEY (`tid`) REFERENCES `types` (`id`),
  ADD CONSTRAINT `analysis_results_ibfk_2` FOREIGN KEY (`uid`) REFERENCES `users` (`id`);

--
-- 資料表的限制式 `colors_for_type`
--
ALTER TABLE `colors_for_type`
  ADD CONSTRAINT `colors_for_type_ibfk_1` FOREIGN KEY (`tid`) REFERENCES `types` (`id`);

--
-- 資料表的限制式 `types`
--
ALTER TABLE `types`
  ADD CONSTRAINT `types_ibfk_1` FOREIGN KEY (`sid`) REFERENCES `seasons` (`id`);

--
-- 資料表的限制式 `wardrobe_items`
--
ALTER TABLE `wardrobe_items`
  ADD CONSTRAINT `wardrobe_items_ibfk_1` FOREIGN KEY (`uid`) REFERENCES `users` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
