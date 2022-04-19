import re
from pathlib import Path
from typing import Union


class Table:
    def __init__(self, body: str) -> None:
        self.body = body

    def __str__(self) -> str:
        return self.get_name()

    def get_name(self) -> str:
        """
        Get name of table

        Returns:
            str: name of table
        """
        try:
            name = re.search(r"CREATE TABLE `.*?`", self.body, re.S).group()
            name = name.replace("CREATE TABLE ", "").replace("`", "")
            return name
        except:
            return None

    def get_primary_key(self) -> Union[str, list]:
        """
        Return name (or list of names) of column(s) that might be a primary key 

        Returns:
            str | list[str]: primary key(s) column(s) name(s)
        """
        try:
            primary_keys = re.search(r"PRIMARY KEY \(`.*?`\)", self.body).group()
            primary_keys = primary_keys.replace("PRIMARY KEY (", "").replace(")", "").replace("`", "")
            if "," in primary_keys:
                return primary_keys.split(",")   # multiple primary keys
            else:
                return primary_keys     # one primary key
        except:
            return None

    def get_fields(self) -> list:
        """
        Get names of all cols in a table

        Returns:
            list[str]: names of columns
        """
        fields = re.findall(r"`.*?`", self.body[self.body.index("("):])
        fields = [k.replace("`", "") for k in fields]
        return list(set(fields))

    def get_foreign_keys(self) -> list:
        """
        Find cols that might be foreign keys (name is usually _____Id)

        Returns:
            list[str]: list containing names of cols that might be foreign keys
        """
        keys = list(filter(lambda x: x.endswith("Id"), self.get_fields()))
        keys = [k for k in keys if k != self.get_primary_key()]
        return keys

    def get_converted_body(self, other_tables: dict) -> str:
        """
        Return query creating table with extra commands creating foreign keys 
        and changing DB engine to InnoDB (previously MyISAM)

        Args:
            other_tables (dict[str, str]): dict created with other tables, format is primary_key: table_name

        Returns:
            str: query creating a table (with foreign keys constraints)
        """
        temp = self.body.replace("ENGINE=MyISAM", "ENGINE=InnoDB")
        footer_template = "\n) ENGINE"     # 'regex' to detect end of creation query
        foreign_keys = self.get_foreign_keys()

        if not foreign_keys:
            return temp
        else:
            foreign_section = ""
            for key in foreign_keys:
                foreign_section += f",\nFOREIGN KEY ({key}) REFERENCES {other_tables[key]}({key})"

            temp = temp.replace(footer_template, foreign_section + footer_template)
            return temp

    def get_alters(self, other_tables: dict) -> list:
        """
        Get list of commands creating creating foreign keys for the table

        Args:
            other_tables (dict[str, str]): dict created with other tables, format is primary_key: table_name

        Returns:
            str: list of commands creating creating foreign keys for the table
        """
        foreign_keys = self.get_foreign_keys()
        if not foreign_keys:
            return []
        else:
            result = []
            name = self.get_name()
            for key in foreign_keys:               
                temp = f"ALTER TABLE {name} ADD FOREIGN KEY ({key}) REFERENCES {other_tables[key]}({key});"
                result.append(temp)
            return result

    def get_data(self) -> dict:
        """
        Return dict with all attributes

        Returns:
            _type_: 
        """
        return {
            "body": self.body,
            "name": self.get_name(),
            "primary_key": self.get_primary_key(),
            "fields": self.get_fields(),
            "foreign_keys": self.get_foreign_keys(),
        }


def convert_dump_to_innodb(file: str, only_single_keys: bool = True) -> str:
    """
    Import sql file and convert it to use InnoDB and foreign keys

    Args:
        file (str): path to Ergast DB dump.
        only_single_keys (bool): some tools (e.g. Django models) don't support primary keys 
                                 made of multiple columns. If set to true, will create new column `id`
                                 that will be primary key instead. (defaults to True)
    Returns:
        (str): path to the new, converted .sql file
    """
    file_path = Path(file)
    db_file = [k for k in open(file_path)]
    sql = "".join(db_file)      # fix 

    table_bodies = re.findall(r"CREATE TABLE.*?;", sql, re.S)
    tables = [Table(k) for k in table_bodies]

    db_tables = {table.get_name(): table for table in tables}
    foreign_keys = {table.get_primary_key(): table.get_name() for table in tables if isinstance(table.get_primary_key(), str)}

    new_sql = sql
    # fixing inconsistency in scheme dump and full dump at ergast website, that causes fail:
    new_sql = new_sql.replace("date NOT NULL DEFAULT '0000-00-00'", "date NOT NULL")    
    # change DB engine to enable foreign keys:
    new_sql = new_sql.replace("ENGINE=MyISAM", "ENGINE=InnoDB")     
    alters = []
    for t in db_tables:
        temp = db_tables[t].get_alters(foreign_keys)
        alters.extend(temp)

    if only_single_keys:
        # regex = r"PRIMARY KEY \(`.*?`(,`.*?`)+\),"  # primary key made of multiple columns
        # new_primary_key = "`pk` int(11) NOT NULL AUTO_INCREMENT,\nPRIMARY KEY (`pk`),"
        # new_sql = re.sub(regex, new_primary_key, new_sql)
        for t in db_tables:
            key =  db_tables[t].get_primary_key()
            if isinstance(key, list):
                name = db_tables[t].get_name()
                alters.append(f"ALTER TABLE `{name}` DROP PRIMARY KEY;")
                alters.append(f"ALTER TABLE `{name}` ADD COLUMN `id` int(11) PRIMARY KEY AUTO_INCREMENT;")
    
    # add alters creating foreign keys at the end of new .sql file
    new_sql += "\n"*3 + "\n".join(alters)
    new_file = file_path.parent / Path(str(file_path.stem) + "_innodb" + str(file_path.suffix))
    with open(new_file, "w") as file:
        file.write(new_sql)
    return str(new_file)



if __name__ == "__main__":
    convert_dump_to_innodb("/home/pawel/Dokumenty/workspace/myisam_to_innodb/f1db.sql")
    pass