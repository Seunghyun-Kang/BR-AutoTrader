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
    def __init__(self):
        print("AutoTrader init()")
        # self.kakao = kakao.Kakao()
        self.holidays = []
        self.weekday = datetime.today().weekday()

        now = str(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))
        self.f = open(f"log_{now}.txt", 'w', encoding="UTF-8")

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def getSignalDate(self):
        pass

    @abstractmethod
    def isWorking(self):
        pass

    # @abstractmethod
    # def getExceptionItemList(self):
    #     pass

    @abstractmethod
    def buy(self):
        pass

    @abstractmethod
    def sell(self):
        pass

    @abstractmethod
    def monitor(self):
        pass 

    def printlog(self, content):
        print(content)
        self.f.write(f"{content}")
        # self.kakao.send_msg_to_me(f"{content}")

    def isHoliday(self, date):
        for holiday in self.holidays:
            if holiday.month == date.month and holiday.day == date.day:
                return True
        if date.weekday() == 5 or date.weekday() == 6:
            return True
        else:
            return False

class Creon(AutoTrader):
    def __init__(self):
        super().__init__()
        self.holidays = self.setHolidays()
        
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

    def setHolidays(self):
        kr_holidays = pytimekr.holidays(year=datetime.now().year)
        red_days_chuseok = pytimekr.red_days(pytimekr.chuseok(year=datetime.now().year))
        print(red_days_chuseok)
        red_days_lunar_newyear = pytimekr.red_days(pytimekr.lunar_newyear(year=datetime.now().year))
        return kr_holidays + red_days_lunar_newyear + red_days_chuseok

    def getSignalDate(self):
        _time = datetime.today() - timedelta(1)
        
        while self.isHoliday(_time) == True:
            _time = _time - timedelta(1)
        
        return _time.strftime("%Y-%m-%d")

    def isWorking(self):
        _time = datetime.now()

        for red_day in self.holidays:
            if _time.month == red_day.month and _time.day == red_day.day:
                self.printlog("--오늘은 한국 휴일--")
                return False

        if self.weekday == 5 or self.weekday == 6:
            self.printlog("--오늘은 한국 주말--")
            return False
        else:
            days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
            self.printlog(f"--오늘은 한국 {days[self.weekday]}--")
            return True

    def buy(self, code, num):
        self.creon.buy(code, num, 0)
        time.sleep(1.5)

    def sell(self, code, num):
        self.creon.sell(code, num, 0)
        time.sleep(1.5)

    def monitor(self):
        self.printlog("Creon monitor()")

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