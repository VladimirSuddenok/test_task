'''Module contains class for managing data base'''
import sqlite3
from threading import Lock
from typing import Union
from config import config_loading

class DataBase:
    '''Class access to data base'''
    def __init__(self, db_name: str) -> None:
        '''Create instance'''
        self._connect = sqlite3.connect(db_name, check_same_thread=False)
        self._lock = Lock()

    def base_configuration(self) -> None:
        '''Used to create the base'''
        cursor = self._connect.cursor()
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS file (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL ,
                    name TEXT NOT NULL,
                    link TEXT NOT NULL,
                    dir varchar(255) NOT NULL
                );
            ''')
        
    def _execute_query(self, sql: str, 
                       commit: bool = True) -> Union[None, list]:
        '''Excute query template'''
        self._lock.acquire()
        cursor = self._connect.cursor()  
        result = [record for record in cursor.execute(sql)]
        if commit:
            self._connect.commit()
            cursor.close()
            self._lock.release()
        else:
            cursor.close()
            self._lock.release()
            return result        
    
    def insert_file(self, file_name, link, file_dir) -> None:
        '''Insert data about file'''
        sql = f'''INSERT INTO file
                  VALUES ( null, '{file_name}', '{link}', '{file_dir}')'''
        self._execute_query(sql)

    def select_file(self, file_name = None) -> None:
        '''Return one or more file information'''
        sql = f'SELECT name, link FROM file '
        if file_name:
            sql += "WHERE name = '%s'" % file_name
        data = self._execute_query(sql, commit=False)
        return data

    def select_path(self, file_name = None) -> None:
        '''Find file folder'''
        sql = f"""SELECT dir FROM file
                  WHERE name = '{file_name}' """

        data = self._execute_query(sql, commit=False)
        return data

if __name__ == "__main__":
    config = config_loading()
    data_base = DataBase(config['data_base']['db_name'])
    data_base.base_configuration()