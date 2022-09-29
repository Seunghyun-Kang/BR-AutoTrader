# from asyncio.windows_events import NULL
import math
import numpy as np
import pymysql
import pandas as pd
import re

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
# from module import creon
# from module import kakao
# from module import kis
# import FinanceDataReader as fdr
import json
import time
from datetime import timedelta, datetime
# from pywinauto import application
import configparser as parser
from pytimekr import pytimekr
import holidays
from abc import ABC, abstractmethod
    
class AutoTrader(ABC):
    def __init__(self, country):
        print("AutoTrader init()")
        self.kakao = kakao.Kakao()
        self.conn = None
        self.country = country
        self.holidays = []
        self.ticker = {}
        self.signals = []
        self.company = {}
        self.weekday = datetime.today().weekday()

        now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
        self.f = open(f"log_{now}.txt", 'w', encoding="UTF-8")

    def __del__(self):
        self.f.close()

    def connectDB(self, db_name):
        properties = parser.ConfigParser()
        properties.read('./config.ini')
        host = properties[db_name]['host']
        pwd = properties[db_name]['pwd']
        user = properties[db_name]['user']
        database = properties[db_name]['database']
        self.conn = pymysql.connect(host=host, user=user, password=pwd, db=database, charset='utf8')
        
    def getSignalList(self, table_name, signal_day):
        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date from {table_name} where date >= '{signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            return pd.DataFrame(curs.fetchall())

    @abstractmethod
    def getCompanyList(self):
        pass

    @abstractmethod
    def login(self):
        pass

    def isWorking(self):
        if self.weekday == 5 or self.weekday == 6:
            self.printlog("--오늘은 주말--")
            return False

        if self.country == 'KR':
            _time = datetime.now()
            for red_day in self.holidays:
                if _time.month == red_day.month and _time.day == red_day.day:
                    self.printlog("--오늘은 한국 휴일--")
                    return False

        elif self.country == 'US':
            for (date, name) in holidays.UnitedStates(years=_time.year).items():
                if date.strftime("%Y-%m-%d") == datetime.today().strftime("%Y-%m-%d"):
                    self.printlog("--오늘은 미국 휴일--")
                    return False
        
        days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        self.printlog(f"--오늘은 {days[self.weekday]}--")
        return True

    @abstractmethod
    def getExceptionItemList(self):
        pass

    @abstractmethod
    def buy(self):
        pass

    @abstractmethod
    def sell(self):
        pass

    @abstractmethod
    def getHoldings(self):
        pass 

    def setHolidays(self):
        if self.country == 'KR':
            kr_holidays = pytimekr.holidays(year=datetime.now().year)
            red_days_chuseok = pytimekr.red_days(pytimekr.chuseok(year=datetime.now().year))
            red_days_lunar_newyear = pytimekr.red_days(pytimekr.lunar_newyear(year=datetime.now().year))
            return kr_holidays + red_days_lunar_newyear + red_days_chuseok

        elif self.country == 'US':
            return list(holidays.UnitedStates(years=datetime.now().year).keys())

    def getSignalDate(self):
        if self.country == 'KR':
            _time = datetime.today() - timedelta(1)
        elif self.country == 'US':
            _time = datetime.utcnow() - timedelta(1)

        while self.isHoliday(_time) == True:
            _time = _time - timedelta(1)
        
        return _time.strftime("%Y-%m-%d")

    def printlog(self, content):
        print(content)
        self.f.write(f"{content}")
        self.kakao.send_msg_to_me(f"{content}")

    def isHoliday(self, date):
        for holiday in self.holidays:
            if holiday.month == date.month and holiday.day == date.day:
                return True
        if date.weekday() == 5 or date.weekday() == 6:
            return True
        else:
            return False

class Creon(AutoTrader):
    def __init__(self,country):
        super().__init__(country)
        self.holidays = self.setHolidays(country)
        
    def login(self):
        os.system('taskkill /IM coStarter*  /F  /T')
        os.system('taskkill /IM CpStart*  /F  /T')
        os.system('taskkill /IM DibServer*  /F  /T')

        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

        self.creon = creon.Creon()

        properties = parser.ConfigParser()
        properties.read('./config.ini')
        self.creon_id = properties['CREON_INFO']['id']
        creon_pwd = properties['CREON_INFO']['pwd']
        creon_cert_pwd = properties['CREON_INFO']['pwdcert']
        
        self.creon.connect(self.creon_id, creon_pwd, creon_cert_pwd)
        self.creon.subscribe_orderevent(self.callback)

    def getCompanyList(self, table_name):
        with self.conn.cursor() as curs :
            sql = f"select code, company from {table_name}"
            curs.execute(sql) 
            companyPD = pd.DataFrame(curs.fetchall())
            
            for pos in range(len(companyPD)):
                code = companyPD.values[pos][0]
                company = companyPD.values[pos][1]
                self.company[code] = company


    def getExceptionItemList(self):
        breakstocks = []
        holdings_f = open(f"holding2.txt", 'r', encoding="UTF-8")
        
        while True :
            codes = holdings_f.readline()
            if codes == '' :
                break
            breakstocks.append(codes[1:7])

        return breakstocks
        
    def buy(self, code, num):
        self.creon.buy(code, num, 0)
        time.sleep(1.5)

    def sell(self, code, num):
        self.creon.sell(code, num, 0)
        time.sleep(1.5)

    def getHoldings(self):
        holdings = []
        items = self.creon.get_holdings()['data']

        for item in items:
             data = {}
             data['code'] = item['종목코드']
             data['profit'] = item['평가손익']
             data['profit_rate'] = item['수익률']
             data['name'] = item['종목명']
             holdings.append(data)

        return holdings
 
    def callback(self, item):
        print(f"callbakc recieved:: {item}")
        _hash = item['주문번호']
        _date = datetime.today().strftime("%Y-%m-%d")
        _type = "buy"
        code = item['종목코드'].replace("A","")

        if item['매매구분코드'] == "1" or item['매매구분코드'] == 1:
            _type = "sell"
        if item['체결가격'] == 0:
            return

        if _type == "buy":
            self.printlog(f"매수 체결 완료: {self.company[code]}, 체결수량 {item['체결수량']}, 체결 가격 {format(item['체결가격'], ',')}\n")
        else:
            self.printlog(f"매도 체결 완료: {self.company[code]}, 체결수량 {item['체결수량']}, 체결 가격 {format(item['체결가격'], ',')}\n")

class Kis(AutoTrader):
    def __init__(self, country):
        super().__init__(country)
        self.holidays = self.setHolidays(country)
        
    def login(self):
        self.kis = kis.KIS()

    def getCompanyList(self, table_name):
        with self.conn.cursor() as curs :
            sql = f"select code, company, ticker from {table_name}"
            curs.execute(sql) 
            companyPD = pd.DataFrame(curs.fetchall())
            
            for pos in range(len(companyPD)):
                code = companyPD.values[pos][0]
                self.company[code] = companyPD.values[pos][1]
                self.ticker[code] = companyPD.values[pos][2]

    def getExceptionItemList(self):
        pass
        
    def buy(self, code, num, price):
        ticker = ''
        if self.ticker[code] == 'NASDAQ':
            ticker = 'NASD'
        else:
            ticker = self.ticker[code]
        self.kis.do_buy(ticker, code, num, price, prd_code="01", order_type="00")

    def sell(self, code, num, price):
        ticker = ''
        if self.ticker[code] == 'NASDAQ':
            ticker = 'NASD'
        else:
            ticker = self.ticker[code]
        self.kis.do_sell(ticker, code, num, price, prd_code="01", order_type="00")
            
    def getHoldings(self):
        holdings = []
        items = self.kis.get_acct_balance()

        for idx in range(len(items)):
            data = {}
            data['code'] = items.코드.values[idx]
            data['name'] = items.종목명.values[idx]
            data['profit'] = float(items.실현손익.values[idx])
            data['profit_rate'] = float(items.수익률.values[idx])
            data['price'] = round(float(items.가격.values[idx]) * 0.98, 2)
            data['possible_sell'] = float(items.매도가능수량.values[idx])
            holdings.append(data)

        return holdings
 
    def callback(self, item):
        print(f"callbakc recieved:: {item}")
        _hash = item['주문번호']
        _date = datetime.today().strftime("%Y-%m-%d")
        _type = "buy"
        code = item['종목코드'].replace("A","")

        if item['매매구분코드'] == "1" or item['매매구분코드'] == 1:
            _type = "sell"
        if item['체결가격'] == 0:
            return

        if _type == "buy":
            self.printlog(f"매수 체결 완료: {self.company[code]}, 체결수량 {item['체결수량']}, 체결 가격 {format(item['체결가격'], ',')}\n")
        else:
            self.printlog(f"매도 체결 완료: {self.company[code]}, 체결수량 {item['체결수량']}, 체결 가격 {format(item['체결가격'], ',')}\n")

creon = Creon()