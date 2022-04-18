import sys
from .db_converter import convert_dump_to_innodb


convert_dump_to_innodb(sys.argv[1])
