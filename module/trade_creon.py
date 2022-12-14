
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
# from module import creon
from module import kakao
from module import trade_module

import time
from datetime import timedelta, datetime
import configparser as parser
from pytimekr import pytimekr
import holidays
import pymysql
import pandas as pd

class CreonTradeModule(trade_module.AbstractTradeModule):
    # def __init__(self):
        # self.creon_api = creon.Creon()

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
        

    def get_signals_from_core(self):
        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date from signal_bollinger_reverse where date >= '{self.signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            return pd.DataFrame(curs.fetchall())


    def set_companies(self):
        with self.conn.cursor() as curs :
            sql = f"select code, company from company_info"
            curs.execute(sql) 
            companyPD = pd.DataFrame(curs.fetchall())
            
            for pos in range(len(companyPD)):
                code = companyPD.values[pos][0]
                company = companyPD.values[pos][1]
                self.company[code] = company

    def get_holding_stocks(self):
        return self.creon.get_holdings()['data']

    def get_account_money(self):
        money = self.creon.get_balance()
        for item in self.get_holding_stocks():
            money = money + item['평가금액']
        return money

    def get_today_price_per_stock(self):
        return self.get_account_money() / 50
    
    def make_buy_list(self):
        pass

    def make_sell_list(self):
        pass

    def start_trade(self):
        pass