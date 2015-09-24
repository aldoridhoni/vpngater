drop table if exists vpnlist;
create table vpnlist (
	id integer primary key autoincrement,
	hostname varchar,
	ip varchar,
	speed varchar,
	country varchar,
	config_data varchar
);