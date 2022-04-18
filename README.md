# myisam_to_innodb
Automatic conversion of MyISAM DB into InnoDB, with usage of foreign keys(based on names).

Tested only with Ergast DB (http://ergast.com/mrd/)

## Usage
```
python -m db_converter /path/to/db/sql_dump.sql
```
Will create new .sql file at: ```/path/to/db/sql_dump_innodb.sql```
