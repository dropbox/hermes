INSERT INTO event_types
VALUES
	(1,'system-reboot','required','This system requires a reboot.');

INSERT INTO event_types
VALUES
	(2,'system-reboot','completed','This system rebooted.');

INSERT INTO event_types
VALUES
	(3,'system-maintenance','required','This system requires maintenance.');

INSERT INTO event_types
VALUES
	(4,'system-maintenance','ready','This system is ready for maintenance.');

INSERT INTO event_types
VALUES
	(5,'system-maintenance','completed','System maintenance completed.');

INSERT INTO event_types
VALUES
	(6,'system-shutdown','required','System shutdown required.');

INSERT INTO event_types
VALUES
	(7,'system-shutdown','completed','System shutdown completed.');

INSERT INTO fates
VALUES
	(1,1,NULL, 0, 1, 'Reboot or release the system');

INSERT INTO fates
VALUES
	(2,2,1, 0, 1, 'System rebooted');

INSERT INTO fates
VALUES
	(3,4,1, 0, 1, 'System released');

INSERT INTO fates
VALUES
	(4,3,NULL, 0, 1, 'Release or acknowledge downtime');

INSERT INTO fates
VALUES
	(5,4,4, 1, 0, 'Perform maintenance');

INSERT INTO fates
VALUES
	(6,5,5, 1, 0, 'Maintenance completed');


INSERT INTO hosts
    VALUES (1, 'example.dropbox.com');

INSERT INTO hosts
    VALUES (2, 'sample.dropbox.com');

INSERT INTO hosts
    VALUES (3, 'test.dropbox.com');

INSERT INTO events ('id', 'host_id', 'timestamp', 'user', 'event_type_id', 'note')
    VALUES (1, 1, "2015-04-31 10:00:00", "system", 1, "example.dropbox.com needs a reboot");

INSERT INTO events ('id', 'host_id', 'timestamp', 'user', 'event_type_id', 'note')
    VALUES (2, 1, "2015-05-01 22:34:03", "system", 2, "example.dropbox.com rebooted.");
