'''Module contains functions for managing project settings'''

import configparser

DEFAULT_CONFIG_NAME = 'config.ini'

def creat_default_config() -> None:
    config = configparser.ConfigParser()
    config['service'] = {'host': '0.0.0.0',
                         'port': '3000'}

    config['handler.upload'] = {'size_pack': '1024', 
                                'blocking_sleep': 'True',
                                'sleep_time': '1'}

    config['handler.download'] = {'size_pack': '100', 
                                  'blocking_sleep': 'True',
                                  'sleep_time': '1'}

    config['handler'] = {'files_dir': 'files_dir/',
                         'socket_timeout': '2'}

    config['data_base'] =  {'db_name': 'files_info.db'}
  
    with open(DEFAULT_CONFIG_NAME, 'w') as configfile:
        config.write(configfile)

def config_loading() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(DEFAULT_CONFIG_NAME)
    return config

if __name__ == "__main__":
    creat_default_config()
    conf = config_loading()
    print (conf.sections())
