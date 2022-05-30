import math
import numpy as np
import pymysql
import pandas as pd

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module import creon
from module import kakao
from module import kis
import json
import time
from datetime import timedelta, datetime
from pywinauto import application
import configparser as parser
from pytimekr import pytimekr
import holidays

class AutoTradeModuleCREON:
    def __init__(self, file):
        os.system('taskkill /IM coStarter*  /F  /T')
        os.system('taskkill /IM CpStart*  /F  /T')
        os.system('taskkill /IM DibServer*  /F  /T')

        os.system('wmic process where "name like \'%coStarter%\'" call terminate')
        os.system('wmic process where "name like \'%CpStart%\'" call terminate')
        os.system('wmic process where "name like \'%DibServer%\'" call terminate')

        self.f = file

        self.kakao = kakao.Kakao()
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
            self.signal_day = (datetime.today() - timedelta(3)).strftime("%Y-%m-%d")
        elif datetime.today().weekday() == 6:
            print("일요일!")
            self.signal_day = (datetime.today() - timedelta(2)).strftime("%Y-%m-%d")
        else:
            self.signal_day = (datetime.today() - timedelta(1)).strftime("%Y-%m-%d")
        print(f"Signal day is : {self.signal_day}")

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
            sql = f"select code, type, close, date from signal_bollinger_reverse where date >= '{self.signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            self.signals = pd.DataFrame(curs.fetchall())

        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date from signal_bollinger_trend where date >= '{self.signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            self.signals_origin = pd.DataFrame(curs.fetchall())

        self.company = {}
        with self.conn.cursor() as curs :
            sql = f"select code, company from company_info"
            curs.execute(sql) 
            companyPD = pd.DataFrame(curs.fetchall())
            
            for pos in range(len(companyPD)):
                code = companyPD.values[pos][0]
                company = companyPD.values[pos][1]
                self.company[code] = company
        #22.05.10
        self.ignore_code = [
        ] 

    def __del__(self):
        self.f.close()
        # self.conn.close()

    def checkTodayOrder(self):
        self.allStockHolding = self.creon.get_holdings()['data']
        # print(self.allStockHolding)

        for pos in range(len(self.signals)):
            code = self.signals.values[pos][0]
            signal_type = self.signals.values[pos][1]
            checkStatus = self.creon.get_stockstatus(code)
            print(self.company[code])
            
            ICR = self.creon.getICR(code)
            
            if signal_type == 'buy':
                if checkStatus['control'] != 0 or checkStatus['supervision'] != 0 or checkStatus['status'] != 0:
                    self.kakao.send_msg_to_me(f"거래 위험 종목, 매수 무시 예정--{self.company[code]}")
                    print(f"거래 위험 종목 --{self.company[code]}")
                    print(self.creon.get_stockstatus(code))
                    self.ignore_code.append(code)

                if ICR < 0.0:
                    self.kakao.send_msg_to_me(f"이자보상배율 0 이하, 매수 무시 예정--{self.company[code]}")
                    print(f"이자보상배율 0 이하 --{self.company[code]}")
                    self.ignore_code.append(code)

                for stock in self.allStockHolding:
                    if stock['종목코드'] == 'A'+code and stock['수익률'] > -20:
                        print(f"-20% 이상, 매수 무시 예정--{self.company[code]}")
                        self.kakao.send_msg_to_me(f"-20% 이상, 매수 무시 예정--{self.company[code]}")
                        self.ignore_code.append(code)

        for holding in self.allStockHolding:
            checkStatus = self.creon.get_stockstatus(holding['종목코드'])
            if checkStatus['control'] != 0 or checkStatus['supervision'] != 0 or checkStatus['status'] != 0:
                print(holding)
                self.kakao.send_msg_to_me(f"!!!!!!!!!!!보유 주식 중 거래 위험 경고 발생, 조치 필요--{holding['종목명']}({holding['종목코드']})--수익률{holding['수익률']}--!!!!!!!!")

        self.remain_deposit = self.creon.get_balance()
        self.accout_money = self.remain_deposit

        for item in self.allStockHolding:
            self.accout_money = self.accout_money + item['평가금액']

        self.PRICE_PER_ORDER = self.accout_money / 30  # -> 50 : 100만원
        print("전체 계좌 잔고: ")
        print(self.accout_money)
        print("예수금 잔고: ")
        print(self.remain_deposit)
        
        self.f.write(f"**전체 계좌 잔고: {format(self.accout_money , ',')}**\n\n")
        self.f.write(f"**예수금 잔고: { format(self.remain_deposit, ',')}**\n\n")
        print(f"**오늘의 매매 단위 가격 {format(self.PRICE_PER_ORDER, ',')}**\n\n")
        self.f.write(f"**오늘의 매매 단위 가격 {format(self.PRICE_PER_ORDER, ',')}**\n\n")
        self.kakao.send_msg_to_me(f"--\n전체 계좌 잔고\n{format(self.accout_money, ',')} 원\n--\n--예수금 잔고: { format(self.remain_deposit, ',')} 원--\n--\n오늘의 매매 단위 가격\n{format(math.trunc(self.PRICE_PER_ORDER), ',')} 원\n--")
        
        self.creon.subscribe_orderevent(self.callback)
    
    def checkDeposit(self):
        needMoney = 0
        sellList = []
        buyList = []
        self.kakao.send_msg_to_me(f"--\n오늘의 거래 분석 {self.signal_day} 일자 신호\n총 {len(self.signals)}건\n--")
        remain_deposit = self.remain_deposit
        
        for pos in range(len(self.signals_origin)):
            ignore_flag = False
            code_origin = self.signals_origin.values[pos][0]
            signal_type_origin = self.signals_origin.values[pos][1]
            num = 0
            if signal_type_origin == 'sell':
                for stock in self.allStockHolding:
                    if stock['종목코드'] == ('A' + code_origin):
                        
                        num = stock['매도가능수량']
                        profit = stock['평가손익']
                        profit_rate = stock['수익률']
                        sellList.append((stock['종목명'], profit, profit_rate))
                        print(f"**오리진 매도 예정 {stock['종목명']} {profit} 이익**\n")
                        self.f.write(f"**오리진 매도 예정 {stock['종목명']} {profit} 이익**\n")
                        self.kakao.send_msg_to_me(f"**오리진 매도 예정 {stock['종목명']} {profit} 이익**\n")

        for pos in range(len(self.signals)):
            ignore_flag = False
            code = self.signals.values[pos][0]
            signal_type = self.signals.values[pos][1]
            signal_price = int(self.signals.values[pos][2])
            num = 0
            
            for ignore_code in self.ignore_code:
                if code == ignore_code:
                    ignore_flag = True
                    break
            if signal_type == 'buy':
                if ignore_flag == True:
                    continue
                if signal_price > self.PRICE_PER_ORDER:
                    num = 1
                else:
                    num = int(self.PRICE_PER_ORDER/signal_price)
                
                if signal_price * num > remain_deposit:
                    print("No money in account")
                    self.f.write("No money in account\n")
                    
                    needMoney = needMoney + (signal_price * num)
                    self.kakao.send_msg_to_me(f"--\n크레온 계좌 잔액 부족\n{needMoney}\n--")
                else:
                    buyList.append((code, signal_price))
                    remain_deposit = remain_deposit - signal_price * num
            else:
                if ignore_flag == True:
                    continue
                for stock in self.allStockHolding:
                    if stock['종목코드'] == ('A' + code):
                        
                        num = stock['매도가능수량']
                        profit = stock['평가손익']
                        profit_rate = stock['수익률']
                        sellList.append((stock['종목명'], profit, profit_rate))
                        print(f"**매도 예정 {stock['종목명']} {profit} 이익**\n")
                        self.f.write(f"**매도 예정 {stock['종목명']} {profit} 이익**\n")
        
        # buy_text = ""
        for i, (code, price) in enumerate(buyList):
            # buy_text = buy_text + f"{i+1}. 매수: {code} 종목, {price}원\n"
            if i == 0:
                self.kakao.send_msg_to_me(f"--\n오늘의 매수 예정\n--\n{i+1}. 매수: {self.company[code]} - {format(price, ',')}원\n")
            else:
                self.kakao.send_msg_to_me(f"{i+1}. 매수: {self.company[code]} - {format(price, ',')}원 - {math.trunc(self.PRICE_PER_ORDER/price)}개\n")
        # buy_text = buy_text + "\n\n"
        for i, (stock_name, price, profit) in enumerate(sellList):
            # buy_text = buy_text + f"{i+1}. 매도: {code} 종목, {price}원\n"
            if i == 0:
                self.kakao.send_msg_to_me(f"--\n오늘의 매도 예정\n--\n{i+1}. 매도: {stock_name} - 손익 {format(price, ',')}원 - 수익률 {profit}\n")
            else:
                self.kakao.send_msg_to_me(f"{i+1}. 매도: {stock_name} - 손익 {format(price, ',')}원 - 수익률 {profit}\n")
    
    def start_task(self):
        for pos in range(len(self.signals_origin)):
            code_origin = self.signals_origin.values[pos][0]
            signal_type_origin = self.signals_origin.values[pos][1]
        
            if signal_type_origin == 'sell':
                for stock in self.allStockHolding:
                    if stock['종목코드'] == ('A' + code_origin):
                        print(f"--\n")
                        self.f.write(f"--\n")
                        print("매도")
                        self.f.write(f"오리진 매도\n")
                        num = stock['매도가능수량']
                        self.creon.sell(code_origin, num, 0)
                        time.sleep(1.5)

        for pos in range(len(self.signals)):
            ignore_flag = False
            print(f"*")
            self.f.write(f"*\n")
            print(f"{pos + 1} 번째 주문 --")
            self.f.write(f"{pos + 1} 번째 주문 --\n")
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
                for ignore_code in self.ignore_code:
                    if code == ignore_code:
                        ignore_flag = True
                        self.kakao.send_msg_to_me(f"--\n거래 무시 \n{self.company[code]}\n--")
                        continue
                if ignore_flag:
                    continue
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
                print(f"--\n")
                self.f.write(f"--\n\n")
                self.creon.buy(code, num, 0)
                time.sleep(1.5)
            elif signal_type == 'sell':
                for stock in self.allStockHolding:
                    if stock['종목코드'] == ('A' + code):
                        print(f"--\n")
                        self.f.write(f"--\n")
                        print("매도")
                        self.f.write(f"매도\n")
                        num = stock['매도가능수량']
                        self.creon.sell(code, num, 0)
                        time.sleep(1.5)

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
        try:
            with self.conn.cursor() as curs:
                if _type == "buy":
                    self.kakao.send_msg_to_me(f"매수 체결 완료: {self.company[code]}, 체결수량 {item['체결수량']}, 체결 가격 {format(item['체결가격'], ',')}\n")
                else:
                    self.kakao.send_msg_to_me(f"매도 체결 완료: {self.company[code]}, 체결수량 {item['체결수량']}, 체결 가격 {format(item['체결가격'], ',')}\n")

                sql = f"REPLACE INTO trade_history VALUES ('{_hash}', '{self.creon_id}', '{code}', '{_date}', '{_type}', '{item['체결수량']}', '{format(item['체결가격'], ',')}')"
                curs.execute(sql)
                self.conn.commit()
        except:
            print("DB REPLACE 에러 발생")



class AutoTradeModuleKIS:
    def __init__(self, file):
        self.kis = kis.KIS()
        self.f = file
        
        self.kakao = kakao.Kakao()

        if datetime.utcnow().weekday() == 0:
            self.signal_day = (datetime.utcnow() - timedelta(3)).strftime("%Y-%m-%d")
        elif datetime.utcnow().weekday() == 6:
            print("일요일!")
            self.signal_day = (datetime.utcnow() - timedelta(2)).strftime("%Y-%m-%d")
        else:
            self.signal_day = (datetime.utcnow() - timedelta(1)).strftime("%Y-%m-%d")
        print(f"Signal day is : {self.signal_day}")
        
        properties = parser.ConfigParser()
        properties.read('./config.ini')
        host = properties['DB_INFO_NASDAQ']['host']
        pwd = properties['DB_INFO_NASDAQ']['pwd']
        user = properties['DB_INFO_NASDAQ']['user']
        database = properties['DB_INFO_NASDAQ']['database']
        self.conn = pymysql.connect(host=host, user=user, password=pwd, db=database, charset='utf8')
        
        with self.conn.cursor() as curs :
            sql = f"select code, type, close, date from signal_bollinger_reverse_usa where date >= '{self.signal_day}' and valid = 'valid'"
            curs.execute(sql) 
            self.signals = pd.DataFrame(curs.fetchall())
        
        self.company = {}
        self.ticker = {}
        with self.conn.cursor() as curs :
            sql = f"select code, company, ticker from company_info_usa"
            curs.execute(sql) 
            companyPD = pd.DataFrame(curs.fetchall())
            
            for pos in range(len(companyPD)):
                code = companyPD.values[pos][0]
                self.company[code] = companyPD.values[pos][1]
                self.ticker[code] = companyPD.values[pos][2]
        
        self.sellList = []
        self.buyList = []

    def check_deposit(self):
        self.deposit = self.kis.get_acct_remains()
        self.remains = float(self.deposit.사용가능.values[0])
        self.total_money = float(self.deposit.외화잔고.values[0])
        self.using_money = float(self.deposit.매수증거금.values[0])
        self.PRICE_PER_ORDER = float(self.total_money) / 100  #4.5만원

        self.allStockHolding = self.kis.get_acct_balance()
        self.kakao.send_msg_to_me(f"--\n오늘의 한국 투자 종목 당 가격 {self.PRICE_PER_ORDER} 달러\n--")

        
    def check_signals(self):
        remain_deposit = self.remains
        needMoney = 0

        for pos in range(len(self.signals)):
            code = self.signals.values[pos][0]
            signal_type = self.signals.values[pos][1]
            signal_price = round(float(self.signals.values[pos][2]), 2)
            num = 0
            
            if signal_type == 'buy':
                if signal_price > self.PRICE_PER_ORDER and signal_price <= self.PRICE_PER_ORDER * 10:
                    num = 1
                elif signal_price > self.PRICE_PER_ORDER and signal_price > self.PRICE_PER_ORDER * 10:
                    self.f.write(f"--\n한국투자 해당 종목 기준가격 10배 이상, 매수 무시\n--")
                    self.kakao.send_msg_to_me(f"--\n한국투자 해당 종목 기준가격 10배 이상, 매수 무시\n--")
                    continue
                else:
                    num = int(self.PRICE_PER_ORDER/signal_price)
                
                if float(signal_price * num) > remain_deposit:
                    print("No money in account")
                    self.f.write("No money in account\n")
                    
                    needMoney = needMoney + (signal_price * num)
                    self.kakao.send_msg_to_me(f"--\n한국투자 계좌 잔액 부족\n{needMoney}\n--")
                self.buyList.append((code, self.company[code] ,signal_price, num))
                remain_deposit = remain_deposit - signal_price * num
            else:
                for idx in range(len(self.allStockHolding)):
                    holding_code = self.allStockHolding.코드.values[idx]
                    name = self.allStockHolding.종목명.values[idx]

                    if code == holding_code:
                        num = self.allStockHolding.수량.values[idx]
                        profit = self.allStockHolding.실현손익.values[idx]
                        profit_rate = self.allStockHolding.수익률.values[idx]
                        self.sellList.append((code, name , signal_price, profit, profit_rate, num))
                        print(f"**한국투자 매도 예정 {name}, {profit} 이익**\n")
                        self.f.write(f"**한국투자 매도 예정 {name}, {profit} 이익**\n")
        
        
        # buy_text = ""
        for i, (code, name, price, num) in enumerate(self.buyList):
            # buy_text = buy_text + f"{i+1}. 매수: {code} 종목, {price}원\n"
            if i == 0:
                self.kakao.send_msg_to_me(f"--\n한국투자 오늘의 매수 예정\n--\n{i+1}. 매수: {name} - {format(price, ',')}달러\n")
            else:
                self.kakao.send_msg_to_me(f"{i+1}. 매수: {name} - {format(price, ',')}달러 - {num}개\n")
        # buy_text = buy_text + "\n\n"
        for i, (code, name, price, profit, profit_rate, num) in enumerate(self.sellList):
            # buy_text = buy_text + f"{i+1}. 매도: {code} 종목, {price}원\n"
            if i == 0:
                self.kakao.send_msg_to_me(f"--\n한국투자 오늘의 매도 예정\n--\n{i+1}. 매도: {name}, {profit} 달러 이익\n")
            else:
                self.kakao.send_msg_to_me(f"{i+1}. 매도: {name}, {profit} 달러 이익\n")


    def start_task(self):
        for i, (code, name, price, profit, profit_rate, num) in enumerate(self.sellList):
            if self.ticker[code] == 'NASDAQ':
                self.kis.do_sell('NASD', code, num, '0', self.kakao, name,prd_code="01", order_type="31")
            elif self.ticker[code] == 'NYSE':
                self.kis.do_sell('NYSE', code, num, '0', self.kakao, name,prd_code="01", order_type="31")
            elif self.ticker[code] == 'AMEX':
                self.kis.do_sell('AMEX', code, num, '0', self.kakao, name,prd_code="01", order_type="31")
        for i, (code, name, price, num) in enumerate(self.buyList):
            if self.ticker[code] == 'NASDAQ':
                self.kis.do_buy('NASD',code, num, price, self.kakao,name, prd_code="01", order_type="32")
            elif self.ticker[code] == 'NYSE':
                self.kis.do_buy('NYSE', code, num, price, self.kakao,name, prd_code="01", order_type="32")
            elif self.ticker[code] == 'AMEX':
                self.kis.do_buy('AMEX', code, num, price, self.kakao,name, prd_code="01", order_type="32")
    
    def trade(self, type):
        self.allStockHolding = self.kis.get_acct_balance()
        profit_flag = 0.0

        if type == 'normal': 
            profit_flag = 20.0
        elif type == 'last':
            profit_flag = 5.0

        for idx in range(len(self.allStockHolding)):
            holding_code = self.allStockHolding.코드.values[idx]
            name = self.allStockHolding.종목명.values[idx]

            num = self.allStockHolding.수량.values[idx]
            profit = float(self.allStockHolding.실현손익.values[idx])
            profit_rate = float(self.allStockHolding.수익률.values[idx])
            price = round(float(self.allStockHolding.가격.values[idx]) * 0.98, 2)
            possible_sell = float(self.allStockHolding.매도가능수량.values[idx])
            
            if profit_rate >= profit_flag and possible_sell > 0:
                print(f"**한국투자 매도 예정 {name}, {profit} 이익**\n")
                self.f.write(f"**한국투자 매도 예정 {name}, {profit} 이익**\n")
                if self.ticker[holding_code] == 'NASDAQ':
                    self.kis.do_sell('NASD', holding_code, num, price, self.kakao, name,prd_code="01", order_type="00")
                elif self.ticker[holding_code] == 'NYSE':
                    self.kis.do_sell('NYSE', holding_code, num, price, self.kakao, name,prd_code="01", order_type="00")
                elif self.ticker[holding_code] == 'AMEX':
                    self.kis.do_sell('AMEX', holding_code, num, price, self.kakao, name,prd_code="01", order_type="00")

now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))

kakao_module = kakao.Kakao()

f = open(f"log_{now}.txt", 'w', encoding="UTF-8")

work = AutoTradeModuleCREON(f)
work_nasdaq = AutoTradeModuleKIS(f)

KRX_Done = False
NASDAQ_Done = False
KRX_Break = False
KRX_Check = False
NASDAQ_Break = False

kr_holidays = pytimekr.holidays(year=datetime.now().year)
red_days_chuseok = pytimekr.red_days(pytimekr.chuseok(year=datetime.now().year))
red_days_lunar_newyear = pytimekr.red_days(pytimekr.lunar_newyear(year=datetime.now().year))

_weekday = datetime.today().weekday()
_time = datetime.now()

for red_days in red_days_chuseok:
    kr_holidays.append(red_days)
for red_days in red_days_lunar_newyear:
    kr_holidays.append(red_days)

kakao_module.send_msg_to_me(f'{now}\nBR auto-trader 가동되었습니다.')

for (date, name) in holidays.UnitedStates(years=_time.year).items():
    if date.strftime("%Y-%m-%d") == datetime.today().strftime("%Y-%m-%d"):
        print(f"--오늘은 미국 노는날 {_time}--")
        f.write(f"--오늘은 미국 노는날 {_time}--")
        kakao_module.send_msg_to_me(f"--오늘은 미국 노는날 {name}--")
        NASDAQ_Break = True

for red_day in kr_holidays:
    if _time.month == red_day.month and _time.day == red_day.day:
        print(f"--오늘은 한국 노는날 {_time}--")
        f.write(f"--오늘은 한국 노는날 {_time}--")
        kakao_module.send_msg_to_me(f"--오늘은 한국 노는날 {_time}--")
        KRX_Break = True

if _weekday == 5 or _weekday == 6:
    print(f"--오늘은 노는날 {_time}--")
    f.write(f"--오늘은 노는날 {_time}--")
    kakao_module.send_msg_to_me(f"--오늘은 노는날 {_time}--")
    KRX_Break = True
    NASDAQ_Break == True 
    print(f"--프로그램 정상 종료 {now}--")
    sys.exit()

while True:
    _time = datetime.now()

    if _time.hour == 8 and _time.minute >= 30 and  KRX_Done == False and KRX_Break == False and KRX_Check == False:
        work.checkTodayOrder()
        work.checkDeposit() 
        KRX_Check = True
    
    if _time.hour == 9 and KRX_Done == False and KRX_Break == False:
        now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
        print(f"--오늘의 한국 자동매매 시작 {_time}--")
        f.write(f"--오늘의 한국 자동매매 시작 {_time}--")
        kakao_module.send_msg_to_me(f"--\n오늘의 한국 자동매매 시작\n{_time}\n--")

        work.start_task()
        KRX_Done = True

    if _time.hour == 15 and _time.minute > 30 and KRX_Break == False:
        now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
        print(f"--오늘의 한국 자동매매 종료 {now}--")
        f.write(f"--오늘의 한국 자동매매 종료 {now}--")
        kakao_module.send_msg_to_me(f"--\n오늘의 한국 자동매매 종료\n{now}\n--")
        KRX_Done = False 

    if _time.hour == 23 and _time.minute == 0 and _time.second == 0 and NASDAQ_Done == False and NASDAQ_Break == False:
        print(f"--오늘의 미국 자동매매 시작 30분 전{_time}--")
        f.write(f"--오늘의 미국 자동매매 시작 30분 전{_time}--")
        kakao_module.send_msg_to_me(f"--\n오늘의 미국 자동매매 30분 전\n{_time}\n--")
        work_nasdaq.check_signals()
        work_nasdaq.check_deposit()
        work_nasdaq.start_task()
    
    if ((_time.hour == 23 and _time.minute >= 30) or (_time.hour >= 0 and _time.hour < 6)) and NASDAQ_Done == False and NASDAQ_Break == False:
        NASDAQ_Done = True

    # if _time.hour == 23 and _time.minute == 29 and _time.second == 0 and NASDAQ_Done == False and NASDAQ_Break == False:
    #     print(f"--오늘의 미국 자동매매 시작 1 분전{_time}--")
    #     f.write(f"--오늘의 미국 자동매매 시작 1 분전{_time}--")
    #     kakao_module.send_msg_to_me(f"--\n오늘의 미국 자동매매 1 분전\n{_time}\n--")
    #     work_nasdaq.check_deposit()
    #     work_nasdaq.start_task()

    if NASDAQ_Done == True and  _time.second == 0 and NASDAQ_Break == False:
        print(f"--미국 자동매매 가격 점검 {_time}--")
        work_nasdaq.trade('normal')

    if NASDAQ_Done == True and _time.hour == 5 and _time.second == 30 and NASDAQ_Break == False:
        print(f"--미국 자동매매 최종 가격 점검 {_time}--")
        work_nasdaq.trade('last')

    if _time.hour == 6 and _time.minute == 0 and NASDAQ_Done == True and NASDAQ_Break == False:
        print(f"--오늘의 미국 자동매매 종료 {_time}--")
        f.write(f"--오늘의 미국 자동매매 종료 {_time}--")
        kakao_module.send_msg_to_me(f"--\n오늘의 미국 자동매매 종료\n{_time}\n--")
        NASDAQ_Done = False
        sys.exit()

