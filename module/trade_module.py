from abc import *
from module.kakao import Kakao
import configparser as parser

class AbstractTradeModule(metaclass=ABCMeta):

    def __init__(self):
        self.kakao = Kakao()
        self.config = parser.ConfigParser()
        self.config.read('./config.ini')

        self.holding_stocks = {}
        self.company_dic = {}
        self.signal_day = None
        self.signal_list = []
        self.account_money = None

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
    def get_signals_from_core(self, signal_day):
        pass

    @abstractmethod
    def set_companies(self):
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