
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module.creon import Creon
from module.trade_module import AbstractTradeModule
from module.stock_detail import StockDetail
from module.signal_detail import SignalDetail
import time
from datetime import timedelta, datetime
import configparser as parser
from pytimekr import pytimekr
import FinanceDataReader as fdr
import holidays
import pymysql
import pandas as pd

class CreonTradeModule(AbstractTradeModule):
    def __init__(self):
        super().__init__()
       
        self.creon_api = None
        self.connect_api()
        self.connect_database()
        self.set_properties()


    def set_properties(self):
        # self.company_dic = self.set_companies()
        self.signal_day = self.get_signal_day()
        self.set_signals_from_core(self.signal_day)
        self.holding_stocks = self.get_holding_stocks()
        self.account_money = self.get_account_money()

        df_konex = fdr.StockListing('KONEX')
        df_konex['ticker'] = 'KONEX'
        self.konex = df_konex.rename(columns={'Symbol':'code', 'Name':'company','ticker':'ticker'})


    def connect_api(self):
        os.system('taskkill /IM coStarter*  /F  /T')
        os.system('taskkill /IM CpStart*  /F  /T')
        os.system('taskkill /IM DibServer*  /F  /T')

        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

        creon_id = self.config['CREON_INFO']['id']
        creon_pwd = self.config['CREON_INFO']['pwd']
        creon_cert_pwd = self.config['CREON_INFO']['pwdcert']
        
        try:
            self.creon_api = Creon()
            self.creon_api.connect(creon_id, creon_pwd, creon_cert_pwd)
        except:
            print("크레온 서버 접속 실패")


    def get_signal_day(self):
        day_before = 1
        while self.is_holiday((datetime.today() - timedelta(day_before))):
            day_before = day_before + 1
        return (datetime.today() - timedelta(day_before)).strftime("%Y-%m-%d")


    def is_holiday(self, day):
        kr_holidays = pytimekr.holidays(year=datetime.now().year)
        red_days_chuseok = pytimekr.red_days(pytimekr.chuseok(year=datetime.now().year))
        red_days_lunar_newyear = pytimekr.red_days(pytimekr.lunar_newyear(year=datetime.now().year))

        for red_days in red_days_chuseok:
            kr_holidays.append(red_days)
        for red_days in red_days_lunar_newyear:
            kr_holidays.append(red_days)

        if day.weekday() == 6:
            print("일요일")
            return True
        elif day.weekday() == 5:
            print("토요일")
            return True
        for red_day in kr_holidays:
            if day.month == red_day.month and day.day == red_day.day:
                print("공휴일")
                return True
        
        return False


    def connect_database(self):
        host = self.config['DB_INFO']['host']
        pwd = self.config['DB_INFO']['pwd']
        user = self.config['DB_INFO']['user']
        database = self.config['DB_INFO']['database']
        self.conn = pymysql.connect(host=host, user=user, password=pwd, db=database, charset='utf8')
        

    def set_signals_from_core(self, signal_day):
        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date, buy_count from signal_bollinger_reverse where date >= '{signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            signals = pd.DataFrame(curs.fetchall())
            for pos in range(len(signals)):
                code = signals.values[pos][0]
                signal_date = signals.values[pos][3]
                signal_type = signals.values[pos][1]
                signal_price = signals.values[pos][2]
                signal_count = signals.values[pos][4]

                self.signal_list.append(SignalDetail(code, signal_date, signal_type, signal_price, signal_count))


    def set_companies(self):
        companies = {}
        with self.conn.cursor() as curs :
            sql = f"select code, company from company_info"
            curs.execute(sql) 
            companyPD = pd.DataFrame(curs.fetchall())
            
            for pos in range(len(companyPD)):
                code = companyPD.values[pos][0]
                company = companyPD.values[pos][1]
                companies[code] = company
        return companies


    def get_holding_stocks(self):
        holding_stock_dic = {}

        try:
            for item in self.creon_api.get_holdings()['data']:
                name = item['종목명']
                code = item['종목코드']
                quantity = item['매도가능수량']
                price = item['평가금액']
                profit = item['평가손익']
                profit_rate = item['수익률']
                even_price = item['손익단가']
                holding_stock_dic[code] = StockDetail(name, code, quantity, price, profit, profit_rate, even_price)
        except:
            print("잔고 조회 실패")

        return holding_stock_dic


    def get_account_money(self):
        try:
            money = self.creon_api.get_balance()
            holdings = self.holding_stocks
            for item in holdings.values():
                money = money + item.price
        except:
            print("예수금 조회 실패")
            return None

        return money

    def get_today_price_per_stock(self):
        return self.get_account_money() / 50
    

    def get_break_stocks(self):
        break_stocks = []
        f = open(f"./holding2.txt", 'r', encoding="UTF-8")

        while True :
            codes = f.readline()
            if codes == '' :
                break
            break_stocks.append(codes[1:7])

        return break_stocks


    def is_safe_warning(self, code):
        try:
            stock_status = self.creon_api.get_stockstatus(code)
            if stock_status['control'] != 0 or stock_status['supervision'] != 0 or stock_status['status'] != 0:
                return False
            else:
                return True
        except:
            print("종목 위험성 여부 확인 실패")


    def is_safe_ICR(self, code):
        try:
            ICR = self.creon_api.getICR(code)
            if ICR < 0.0:
                return False
            else:
                return True
        except:
            print("종목 ICR 확인 실패")


    def is_KONEX(self, code):
        try:
            for pos in range(len(self.konex)):
                konex_code = self.konex.values[pos][0]
                if code == konex_code:
                    return True

            return False
        except:
            print("KONEX 확인 실패")


    def buy(self, code, num):
        self.creon_api.buy(code, num, 0)


    def sell(self, code, num):
        self.creon_api.sell(code, num, 0)



