import socket
import uuid
from configparser import ConfigParser
from typing import Union, Tuple
import uuid
import re
from db_utils import DataBase
import time
import json
import os

class RequestHandler:
    '''Base class request handler'''
    def __init__(self, conn: socket.socket, addr: Tuple, 
                 config: ConfigParser, data_base: DataBase):
        '''Create instance handler'''
        self._conn = conn
        self._addr = addr
        self._conn.settimeout(int(config['handler']['socket_timeout']))
        self._db = data_base
        #upload settings
        self._upload_size_pack = int(config['handler.upload']['size_pack'])
        self._upload_blocking_sleep = bool(config['handler.upload']['blocking_sleep'])
        self._upload_sleep_time = int(config['handler.upload']['sleep_time'])
        #download settings
        self._download_size_pack = int(config['handler.download']['size_pack'])
        self._download_blocking_sleep = bool(config['handler.download']['blocking_sleep'])
        self._download_sleep_time = int(config['handler.download']['sleep_time'])
        #main file dir
        self._files_dir = config['handler']['files_dir']
        
        self._host = config['service']['host']
        self._port = config['service']['port']

    def processing_request(self) -> None:
        '''Start processing request'''
        result=self._parse_params()
        if not result:
            self._send_response(
                'Bad request: unknown url',
                '400')
            return False
            
        if self._http_params['method'] == 'GET':
            self._get_urls()
        elif self._http_params['method'] == 'POST':
            self._post_urls()
        else:
            msg = 'Bad request: method "%s" not found'
            self._send_response(msg % self._http_params['method'],'400')
    
    def _parse_params(self) -> bool:
        '''Take the http package parameters'''
        base_info = self._conn.recv(1024)
        print ('base_info', base_info)
        self._http_params = dict()
        #one package?
        if not re.findall(b'Expect: 100-continue', base_info):
            content, base_info = self._content_slice(base_info)

            self._http_params['small_content'] = content
            self._http_params['content']='no_continue'
            self._raw_header = base_info
        #convert bytes to string
        buffer = base_info.decode().replace('\r', '').split('\n')
        first = buffer[0].split(' ')
		
        self._http_params['method'] = first[0]
        count = first[1].count('/') 
        if count == 1:
            self._http_params['url'] = first[1]
        elif count == 2:
            url_sub = re.search(r'(/\w+)/(.+)', first[1])
            self._http_params['url'] = url_sub.group(1)
            self._http_params['sub_url'] = url_sub.group(2)
        else:
            return False
        
        self._http_params['agent'] = buffer[2].split(' ')[1]

        if not self._http_params.get('small_content', None):
            self._http_params['content']='continue'
        
        return True
  
    def _content_slice(self, base_info: bytes):
        '''Separate content from headers'''
        #search bytes content
        index_first = base_info.rfind(b'\r\n\r\n')
        first_slice = base_info[index_first + 4:]
        index_second = first_slice.find(b'\r\n')
        content = first_slice[: index_second]
        #get headers
        headers = base_info[: index_first]
        return content, headers

    def _get_urls(self) -> None:
        '''Routing get-request'''
        if self._http_params['url'] == '/check':
            self._check_view()
        elif self._http_params['url'] == '/download':
            self._download_view()
        else:
            msg = 'Not found: path "%s" do not exist'
            self._send_response(msg % self._http_params['url'],'404')

    def _check_view(self) -> None:
        '''Return link and file name'''
        data = self._db.select_file(self._http_params.get('sub_url', None))
        self._send_response(json.dumps(data),'200')

    def _post_urls(self) -> None:
        '''Routing POST-request'''
        if self._http_params['url'] == '/upload':
            self._upload_view()
        else:
            msg = 'Not found: path "%s" do not exist'
            self._send_response(msg % self._http_params['url'],'404')

    def _upload_view(self) -> Union[None, bool]:
        '''Method upload file'''
        if self._http_params['content'] == 'no_continue':
            #upload short content
            original_file_name = self._search_file_name(self._raw_header)
            if not original_file_name:
                self._send_response(
                    'Bad request: no filename header',
                    '400')
                return False
                
            file_name = str(uuid.uuid1(32)) + '_' + original_file_name 
            file_dir = self._files_dir + file_name
            with open(file_dir,'wb') as file:
                file.write(self._http_params['small_content'])
                
            link = self._build_link(file_name)
            self._db.insert_file(file_name, link, file_dir)
            self._send_response(link, '200')
            
        elif self._http_params['content'] == 'continue':
            raw_data = self._conn.recv(1024)
            content, base_info = self._content_slice(raw_data)
            original_file_name = self._search_file_name(base_info)
            if not original_file_name:
                self._send_response(
                    'Bad request: no filename header',
                    '400')
                return False
                
            file_name = str(uuid.uuid1(32)) + '_' + original_file_name
            file_dir = self._files_dir + file_name
            with open(file_dir,'wb') as file:
                file.write(content)
                while True:
                    try:
                        data = self._conn.recv(self._upload_size_pack)
                    except socket.timeout:
                        break
                    if b'\r\n' in data:
                        file.write(data[: data.find(b'\r\n')])
                        break
                    else:
                        file.write(data)

                    if self._upload_blocking_sleep: 
                        time.sleep(self._upload_sleep_time)
            
            link = self._build_link(file_name)
            self._db.insert_file(file_name, link, file_dir)
            self._send_response(link, '200')         
        else:
            msg = 'Intenal Server Error: some error'
            self._send_response(msg,'500')
        
    def _build_link(self, file_name: str) -> str:
        '''Create unique link'''
        url = 'http://%s:%s/download/%s'
        return url % (self._host, self._port, file_name)
        
    def _search_file_name(self, header: str):
        '''Search file name in the headers'''
        header_str = header.decode()
        temp = 'filename="'
        index = header_str.find(temp)

        if index == -1:
            return False
        
        buffer = header_str[index + len(temp): ]
        return buffer[: buffer.find('"')]

    def _download_view(self):
        '''Method download file'''
        if not self._http_params.get('sub_url', None):
            self._send_response('Bad request: where is no filename',
                    '400')

        file_name = self._http_params['sub_url'] 
        file_path = self._db.select_path(file_name)[0][0]

        with open(file_path, 'rb') as file:
            while True:
                buffer = file.read(self._download_size_pack)
                if not buffer:
                    break
                self._conn.sendall(buffer)
                if self._download_blocking_sleep:
                    time.sleep(self._download_sleep_time)
        
    def _send_response(self, message: str, status_code: str) -> None:
        '''Send message to client'''
        self._conn.send(bytes(message, 'utf-8'))
