INSERT INTO `event_types` (`id`, `category`, `state`, `description`)
VALUES
	(1,'system-reboot','required','This system requires a reboot.'),
	(2,'system-reboot','completed','This system rebooted.'),
	(3,'system-maintenance','required','This system requires maintenance.'),
	(4,'system-maintenance','completed','System maintenance completed.');

INSERT INTO `fates` (`id`, `creation_type_id`, `completion_type_id`, `description`)
VALUES
	(1,1,2,'A system that needs a reboot can be cleared by rebooting the machine.');
