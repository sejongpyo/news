import pymysql
import rds_config

# rds_config.py에 저장된 aws rds정보
rds_host = rds_config.rds_host
rds_user = rds_config.rds_user
rds_password = rds_config.rds_password
db_name = rds_config.db_name
rds_table = rds_config.rds_table
rds_index = rds_config.rds_index


class MysqlController:

    """
    rds_config.py에 저장된 rds 엔드포인트, 
    Mysql 계정 정보(id, password, db_name)를 사용하여 DB접속
    
    """

    def __init__(self, host, id, pw, db_name):
        self.conn = pymysql.connect(
            host=host, user=id, password=pw, db=db_name, charset="utf8"
        )
        self.curs = self.conn.cursor()

    """
    입력된 키워드 db에 저장, 중복된 키워드 입력 시 IGNORE INTO로 무시
    
    [SQL Query = INSERT IGNORE INTO table_name VALUES keyword]
    
    input : 사용자 키워드

    """

    def insert_value_with(self, table_name, col, keyword):
        sql = "INSERT IGNORE INTO {0} ({1}) VALUES ({2})".format(
            table_name, ",".join(col), "'" + keyword + "'"
        )
        self.curs.execute(sql)
        self.conn.commit()

    """
    db에 저장된 키워드 불러오기

    [SQL Query = SELECT keyword FROM table_name]
    
    output : ('keyword1',),('keyword2',),... 튜플형식

    """

    def get_db_data(self, index_name, table_name):
        sql = "SELECT DISTINCT {0} FROM ({1})".format(index_name, table_name)
        self.curs.execute(sql)
        row = self.curs.fetchall()
        return row
            

if __name__ == "__main__":
    mysql_controller = MysqlController(rds_host, rds_user, rds_password, db_name)
    table_name = rds_table
    index_name = rds_index
    mysql_controller.insert_value_with(table_name, ["keyword"], keyword)
    temp = mysql_controller.get_db_data(index_name, table_name)
    print(temp)
