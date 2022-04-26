import numpy as np
import pymysql
import pandas as pd

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module import creon
import json
from datetime import timedelta, datetime
import pywinauto import application

PRICE_PER_ORDER = 100000

class AutoTradeModule:
    def __init__(self):
        os.system('taskkill /IM coStarter*  /F  /T')
        os.system('taskkill /IM CpStart*  /F  /T')
        os.system('taskkill /IM DibServer*  /F  /T')

        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

        time.sleep(5)
        app = application.Application()
        app.start('C:\CREON\STARTER\coStarter.exe /prj:cp/id:****/pwd:***/pwdcert:***/autostart')
        time.sleep(60)
        
        self.creon = creon.Creon()
        self.creon.connect()

        self.allStockHolding = self.creon.get_holdingstocks()

        if datetime.today().weekday() == 0:
            signal_day = (datetime.today() - timedelta(2)).strftime("%Y-%m-%d")
        elif datetime.today().weekday() == 5 or datetime.today().weekday() == 6:
            return
        else:
            signal_day = (datetime.today() - timedelta(1)).strftime("%Y-%m-%d")
        print(f"Signal day is : {signal_day}")

        self.conn = pymysql.connect(host='52.78.240.74', user='root', password='apple10g', db='INVESTAR', charset='utf8')

        with self.conn.cursor() as curs :
            sql = f"select code, type, close from signal_bollinger_trend where date >= '{signal_day}'"
            curs.execute(sql) 
            self.signals = pd.DataFrame(curs.fetchall())
    
    def __del__(self):
        self.conn.close()

    def start_task(self):
        for pos in range(len(self.signals)):
            code = self.signals.values[pos]
            signal_type = self.signals.values[pos]
            signal_price = self.signals.values[pos]
            
            if signal_price > PRICE_PER_ORDER:
                num = 1
            else:
                num = int(PRICE_PER_ORDER/signal_price)
            
            if signal_price * num > self.creon.get_balance():
                print("No money in account")
                return

            if signal_type == 'buy':
                print("BUY SIGNAL TO CREON")
                self.creon.buy(code, num)
            else:
                for stock in self.allStockHolding:
                    if(stock['code'] == code):
                        print("SELL SIGNAL TO CREON")
                        self.creon.sell(code, stock['holdnum'])
            
                # 가지고 있는 물량 전부 처분하는 API 만들어야 함.

a = AutoTradeModule().start_task()