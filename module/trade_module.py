from abc import *
from module import kakao
import configparser as parser

class AbstractTradeModule(metaclass=ABCMeta):

    def __init__(self):
        self.kakao = kakao.Kakao()
        self.config = parser.ConfigParser()
        self.config.read('./config.ini')

        self.holding_stocks = [] 

    @abstractmethod
    def connect_api(self):
        pass

    @abstractmethod
    def get_signal_day(self):
        pass

    @abstractmethod
    def connect_database(self):
        pass

    @abstractmethod
    def get_signals_from_core(self):
        pass

    @abstractmethod
    def get_companies(self):
        pass

    @abstractmethod
    def get_holding_stocks(self):
        pass

    @abstractmethod
    def get_account_money(self):
        pass

    @abstractmethod
    def get_today_price_per_stock(self):
        pass
    
    @abstractmethod
    def make_buy_list(self):
        pass

    @abstractmethod
    def make_sell_list(self):
        pass

    @abstractmethod
    def start_trade(self):
        pass