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

class AutoTradeModule:
    def __init__(self, file):
        os.system('taskkill /IM coStarter*  /F  /T')
        os.system('taskkill /IM CpStart*  /F  /T')
        os.system('taskkill /IM DibServer*  /F  /T')

        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

        self.f = file

        self.creon = creon.Creon(self.f)
        properties = parser.ConfigParser()
        properties.read('./config.ini')
        self.creon_id = properties['CREON_INFO']['id']
        creon_pwd = properties['CREON_INFO']['pwd']
        creon_cert_pwd = properties['CREON_INFO']['pwdcert']
        
        self.creon.connect(self.creon_id, creon_pwd, creon_cert_pwd)

        self.PRICE_PER_ORDER = 50000
        self.allStockHolding = [] 
        self.remain_deposit = 0
        self.accout_money = self.remain_deposit
        
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
            sql = """
            CREATE TABLE IF NOT EXISTS trade_history (
                hashcode VARCHAR(20),
                id VARCHAR(20),
                code VARCHAR(20),
                date DATE,
                type VARCHAR(20),
                num INT(20),
                price FLOAT,
                PRIMARY KEY (hashcode)      
            )
            """
            curs.execute(sql) 
        self.conn.commit()

        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date from signal_bollinger_trend where date >= '{signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            self.signals = pd.DataFrame(curs.fetchall())

    def __del__(self):
        self.f.close()
        self.conn.close()

    def checkTodayOrder(self):
        self.allStockHolding = self.creon.get_holdings()['data']
        self.remain_deposit = self.creon.get_balance()
        self.accout_money = self.remain_deposit

        for item in self.allStockHolding:
            self.accout_money = self.accout_money + item['평가금액']

        self.PRICE_PER_ORDER = self.accout_money / 90
        print("전체 계좌 잔고: ")
        print(self.accout_money)
        print("예수금 잔고: ")
        print(self.remain_deposit)
        
        self.f.write(f"********************전체 계좌 잔고: {self.accout_money}********************\n\n")
        self.f.write(f"********************예수금 잔고: {self.remain_deposit}********************\n\n")
        print(f"********************오늘의 매매 단위 가격 {self.PRICE_PER_ORDER}********************\n\n")
        self.f.write(f"********************오늘의 매매 단위 가격 {self.PRICE_PER_ORDER}********************\n\n")
        
    def checkDeposit(self):
        needMoney = 0
        sellList = []
        remain_deposit = self.remain_deposit
        for pos in range(len(self.signals)):
            code = self.signals.values[pos][0]
            signal_type = self.signals.values[pos][1]
            signal_price = int(self.signals.values[pos][2])
            num = 0
            if signal_type == 'buy':
                if signal_price > self.PRICE_PER_ORDER:
                    num = 1
                else:
                    num = int(self.PRICE_PER_ORDER/signal_price)
                
                if signal_price * num > remain_deposit:
                    print("No money in account")
                    self.f.write("No money in account\n")
                    needMoney = needMoney + (signal_price * num)
                else:
                    remain_deposit = remain_deposit - signal_price * num
            else:
                for stock in self.allStockHolding:
                    if stock['종목코드'] == ('A' + code):
                        
                        num = stock['매도가능수량']
                        profit = stock['평가손익']
                        profit_rate = stock['수익률']
                        sellList.append((stock['종목명'], profit))
                        print(f"*****************매도 예정 {stock['종목명']} {profit} 이익***********************\n")
                        self.f.write(f"*****************매도 예정 {stock['종목명']} {profit} 이익***********************\n")
        #얼마 필요한지 카톡 보내기 (remain_deposit)
        #매도 예정 주식, 수량 카톡 보내기 (sellList)

    def start_task(self):
        print(f"현재 계좌 잔고:: {self.creon.get_balance()}")
        self.f.write(f"현재 계좌 잔고:: {self.creon.get_balance()}\n")
        self.creon.subscribe_orderevent(self.callback)

        for pos in range(len(self.signals)):
            print(f"****************************************")
            self.f.write(f"****************************************\n")
            print(f"{pos + 1} 번째 주문 --------------------")
            self.f.write(f"{pos + 1} 번째 주문 --------------------\n")
            code = self.signals.values[pos][0]
            print(f"신호 종목 코드 : {code}")
            self.f.write(f"신호 종목 코드 : {code}\n")
            signal_type = self.signals.values[pos][1]
            print(f"신호 거래 타입 : {signal_type}")
            self.f.write(f"신호 거래 타입 : {signal_type}\n")
            print(f"신호 가격 : {self.signals.values[pos][2]}")
            self.f.write(f"신호 가격 : {self.signals.values[pos][2]}\n")
            print(f"신호 일자 : {self.signals.values[pos][3].strftime('%Y-%m-%d')}")
            self.f.write(f"신호 일자 : {self.signals.values[pos][3].strftime('%Y-%m-%d')}\n")
            signal_price = int(self.signals.values[pos][2])

            print(f"현재 시장 상태 :: {self.creon.get_stock_info(code)}")
            self.f.write(f"현재 시장 상태 :: {self.creon.get_stock_info(code)}\n")
            num = 0
            if signal_type == 'buy':
                if signal_price > self.PRICE_PER_ORDER:
                    num = 1
                else:
                    num = int(self.PRICE_PER_ORDER/signal_price)
                
                if signal_price * num > self.creon.get_balance():
                    print("No money in account")
                    self.f.write("No money in account\n")
                    continue

                print(f"목표 매수 수량: {num}")
                self.f.write(f"목표 매수 수량: {num}\n")
                print(f"---------------------------------------\n")
                self.f.write(f"---------------------------------------\n\n")
                self.creon.buy(code, num)
                time.sleep(1.5)
            elif signal_type == 'sell':
                for stock in self.allStockHolding:
                    if stock['종목코드'] == ('A' + code):
                        print(f"---------------------------------------\n")
                        self.f.write(f"---------------------------------------\n")
                        print("매도")
                        self.f.write(f"매도\n")
                        num = stock['매도가능수량']
                        self.creon.sell(code, num)
                        time.sleep(1.5)

    def callback(self, item):
        print(f"callbakc recieved:: {item}")
        _hash = item['주문번호']
        _date = datetime.today().strftime("%Y-%m-%d")
        _type = "buy"
        if item['매매구분코드'] == "1" or item['매매구분코드'] == 1:
            _type = "sell"

        with self.conn.cursor() as curs:
            sql = f"REPLACE INTO trade_history VALUES ('{_hash}', '{self.creon_id}', '{item['종목코드']}', '{_date}', '{_type}', '{item['체결수량']}', '{item['체결가격']}')"
            curs.execute(sql)
            self.conn.commit()


now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
f = open(f"log_{now}.txt", 'w', encoding="UTF-8")
work = AutoTradeModule(f)
isDone = False
work.checkTodayOrder()
work.checkDeposit()

while True:
    _time = datetime.now()

    if _time.hour == 9 and isDone == False:
        now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
        print(f"-----------------오늘의 자동매매 시작 {_time}------------------")
        f.write(f"-----------------오늘의 자동매매 시작 {_time}------------------")
        work.start_task()
        isDone = True

    
    if _time.hour == 15 and _time.minute > 30:
        now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
        print(f"-----------------오늘의 자동매매 종료 {now}------------------")
        f.write(f"-----------------오늘의 자동매매 종료 {now}------------------")
        break

