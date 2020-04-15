import socket
from threading import Thread
from configparser import ConfigParser
from handler import RequestHandler
from db_utils import DataBase

from typing import Tuple

class Service:
    '''Base class service'''
    def __init__(self, config: ConfigParser, 
                 classRequestHandler: RequestHandler,
                 data_base: DataBase):
        '''Initializaion main obeject servce'''
        self._config = config
        self._data_base = data_base
        self._requestHandler = classRequestHandler
        self._socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
    
    def base_configuration(self):
        '''Socket configuration'''
        self._socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._config['service']['host'],
                           int(self._config['service']['port'])))

    def start(self):
        '''Start listening to the input connections'''
        self._socket.listen()
        while True:
            conn, addr = self._socket.accept()
            thread = Thread(
                target = self._new_request,
                args = (conn, addr)
            )
            thread.start()

    def _new_request(self, conn: socket.socket, addr: Tuple):
        '''Input connection processing'''
        rh = self._requestHandler(conn, addr, 
                                  self._config, self._data_base)
        rh.processing_request()
        conn.close()

    def stop(self):
        '''Close main socket connection'''
        self._socket.close()