from service import Service
from config import config_loading
from handler import RequestHandler
from db_utils import DataBase


if __name__ == "__main__":
    config = config_loading()
    data_base = DataBase(config['data_base']['db_name'])
    service = Service(config, RequestHandler, data_base)
    service.base_configuration()
    try:
        print ('\nstart service...')
        service.start()
    except KeyboardInterrupt as ex:
        print (ex)
        print ('\nstop service...')