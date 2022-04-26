import numpy as np
import pymysql
import pandas as pd

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module import creon
import json
import time
from datetime import timedelta, datetime
from pywinauto import application
import configparser as parser

PRICE_PER_ORDER = 50000

class AutoTradeModule:
    def __init__(self):
        os.system('taskkill /IM coStarter*  /F  /T')
        os.system('taskkill /IM CpStart*  /F  /T')
        os.system('taskkill /IM DibServer*  /F  /T')

        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

        self.creon = creon.Creon()
        properties = parser.ConfigParser()
        properties.read('./config.ini')
        creon_id = properties['CREON_INFO']['id']
        creon_pwd = properties['CREON_INFO']['pwd']
        creon_cert_pwd = properties['CREON_INFO']['pwdcert']
        
        self.creon.connect(creon_id, creon_pwd, creon_cert_pwd)

        self.allStockHolding = self.creon.get_holdingstocks()

        if datetime.today().weekday() == 0:
            signal_day = (datetime.today() - timedelta(2)).strftime("%Y-%m-%d")
        elif datetime.today().weekday() == 5 or datetime.today().weekday() == 6:
            return
        else:
            signal_day = (datetime.today() - timedelta(1)).strftime("%Y-%m-%d")
        print(f"Signal day is : {signal_day}")

        properties = parser.ConfigParser()
        properties.read('./config.ini')
        host = properties['DB_INFO']['host']
        pwd = properties['DB_INFO']['pwd']
        user = properties['DB_INFO']['user']
        database = properties['DB_INFO']['database']
        self.conn = pymysql.connect(host=host, user=user, password=pwd, db=database, charset='utf8')

        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date from signal_bollinger_trend where date >= '{signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            self.signals = pd.DataFrame(curs.fetchall())

    def __del__(self):
        if self.conn != None:
            self.conn.close()

    def start_task(self):
        print(f"현재 계좌 잔고:: {self.creon.get_balance()}")

        for pos in range(len(self.signals)):
            print(f"****************************************")
            print(f"{pos + 1} 번째 주문 --------------------")
            code = self.signals.values[pos][0]
            print(f"신호 종목 코드 : {code}")
            signal_type = self.signals.values[pos][1]
            print(f"신호 거래 타입 : {signal_type}")
            print(f"신호 가격 : {self.signals.values[pos][2]}")
            print(f"신호 일자 : {self.signals.values[pos][3].strftime('%Y-%m-%d')}")
            signal_price = int(self.signals.values[pos][2])

            print(f"현재 시장 상태 :: {self.creon.get_stock_info(code)}")
            if signal_type == 'buy':
                if signal_price > PRICE_PER_ORDER:
                    num = 1
                else:
                    num = int(PRICE_PER_ORDER/signal_price)
                
                if signal_price * num > self.creon.get_balance():
                    print("No money in account")
                    continue

                print(f"목표 매수 수량: {num}")
                print(f"---------------------------------------")
                print("")
                self.creon.buy(code, num)
            else:
                for stock in self.allStockHolding:
                    if(stock['code'] == code):
                        print(f"---------------------------------------")
                        print("")
                        print("매도")
                        self.creon.sell(code, stock['holdnum'])
        
a = AutoTradeModule().start_task()