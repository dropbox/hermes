SET foreign_key_checks=0;
DROP TABLE IF EXISTS event_types;

CREATE TABLE event_types (
  id int(11) NOT NULL AUTO_INCREMENT,
  category varchar(64) COLLATE utf8_unicode_ci NOT NULL,
  state varchar(32) COLLATE utf8_unicode_ci NOT NULL,
  description varchar(1024) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY _category_state_uc (category,state),
  KEY event_type_idx (id,category,state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

LOCK TABLES event_types WRITE;
/*!40000 ALTER TABLE event_types DISABLE KEYS */;

INSERT INTO event_types (id, category, state, description)
VALUES
	(1,'system-reboot','required','System requires a reboot'),
	(2,'system-reboot','completed','System rebooted'),
	(3,'system-maintenance','required','System requires maintenance'),
	(4,'system-maintenance','ready','System ready for maintenance'),
	(5,'system-maintenance','completed','System maintenance completed'),
	(6,'system-maintenance','acknowledge','Acknowledge system maintenance'),
	(7,'system-maintenance','cancel','Cancel system maintenance');

/*!40000 ALTER TABLE event_types ENABLE KEYS */;
UNLOCK TABLES;


# Dump of table fates
# ------------------------------------------------------------

DROP TABLE IF EXISTS fates;

CREATE TABLE fates (
  id int(11) NOT NULL AUTO_INCREMENT,
  creation_type_id int(11) NOT NULL,
  follows_id int(11) DEFAULT NULL,
  for_creator int(1) NOT NULL DEFAULT '0',
  for_owner int(1) NOT NULL DEFAULT '1',
  description varchar(2048) COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY _creation_completion_uc (creation_type_id,follows_id),
  KEY ix_fates_creation_type_id (creation_type_id),
  KEY fate_idx (id,creation_type_id,follows_id),
  KEY ix_fates_follows_id (follows_id),
  CONSTRAINT fates_ibfk_1 FOREIGN KEY (creation_type_id) REFERENCES event_types (id),
  CONSTRAINT fates_ibfk_3 FOREIGN KEY (follows_id) REFERENCES fates (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

LOCK TABLES fates WRITE;
/*!40000 ALTER TABLE fates DISABLE KEYS */;

INSERT INTO fates (id, creation_type_id, follows_id, for_creator, for_owner, description)
VALUES
	(1,1,NULL,0,1,'Reboot or release the system'),
	(2,2,1,0,1,'System rebooted'),
	(3,3,NULL,0,1,'Release or acknowledge downtime'),
	(4,4,3,1,0,'Perform maintenance'),
	(5,5,4,1,0,'Maintenance completed'),
	(6,6,3,1,0,'Perform online maintenance'),
	(7,5,6,1,0,'Maintenance completed'),
	(8,7,3,1,0,'Maintenance cancelled'),
	(9,7,4,1,0,'Maintenance cancelled'),
	(10,7,6,1,0,'Maintenance cancelled');

/*!40000 ALTER TABLE fates ENABLE KEYS */;
UNLOCK TABLES;
SET foreign_key_checks=1;