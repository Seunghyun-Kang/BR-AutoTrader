import win32com.client
import sys

import os
import argparse
import subprocess
import time
import io
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

from pywinauto import application

class Creon:
    def __init__(self):
        self.obj_CpUtil_CpCybos = win32com.client.Dispatch('CpUtil.CpCybos')
        self.obj_CpUtil_CpCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
        self.obj_CpSysDib_StockChart = win32com.client.Dispatch('CpSysDib.StockChart')
        self.obj_CpTrade_CpTdUtil = win32com.client.Dispatch('CpTrade.CpTdUtil')
        self.obj_CpSysDib_MarketEye = win32com.client.Dispatch('CpSysDib.MarketEye')
        self.obj_CpSysDib_CpSvr7238 = win32com.client.Dispatch('CpSysDib.CpSvr7238')
        self.obj_CpTrade_CpTdNew5331B = win32com.client.Dispatch('CpTrade.CpTdNew5331B')
        self.obj_CpTrade_CpTdNew5331A = win32com.client.Dispatch('CpTrade.CpTdNew5331A')
        self.obj_CpSysDib_CpSvr7254 = win32com.client.Dispatch('CpSysDib.CpSvr7254')
        self.obj_CpSysDib_CpSvr8548 = win32com.client.Dispatch('CpSysDib.CpSvr8548')
        self.obj_CpTrade_CpTd0311 = win32com.client.Dispatch('CpTrade.CpTd0311')
        self.obj_CpTrade_CpTd5341 = win32com.client.Dispatch('CpTrade.CpTd5341')
        self.obj_CpTrade_CpTd6033 = win32com.client.Dispatch('CpTrade.CpTd6033')
        self.obj_Dscbo1_CpConclusion = win32com.client.Dispatch('Dscbo1.CpConclusion')
        self.obj_CpTrade_CpTd0322 = win32com.client.Dispatch('CpTrade.CpTd0322')
        self.obj_Dscbo1_StockBid = win32com.client.Dispatch('Dscbo1.StockBid')
        bConnect = self.obj_CpUtil_CpCybos.IsConnect
        
        if bConnect == 0:
            print("PLUS 연결 안됨!!!!")
            exit()
        
        self.stockcur_handlers = {}  # 주식/업종/ELW시세 subscribe event handlers
        self.stockbid_handlers = {}  # 주식/ETF/ELW 호가, 호가잔량 subscribe event handlers
        self.orderevent_handler = None
    
    def connect(self, id_, pwd, pwdcert, trycnt=300):
        if not self.connected():
            app = application.Application()
            app.start(
                'C:\\CREON\\STARTER\\coStarter.exe /prj:cp /id:{id} /pwd:{pwd} /pwdcert:{pwdcert} /autostart'.format(
                    id=id_, pwd=pwd, pwdcert=pwdcert
                )
            )

        cnt = 0
        while not self.connected():
            if cnt > trycnt:
                return False
            time.sleep(1)
            cnt += 1
        return True

    def connected(self):
        tasklist = subprocess.check_output('TASKLIST')
        if b"DibServer.exe" in tasklist and b"CpStart.exe" in tasklist:
            return self.obj_CpUtil_CpCybos.IsConnect != 0
        return False

    def disconnect(self):
        plist = [
            'coStarter',
            'CpStart',
            'DibServer',
        ]
        for p in plist:
            os.system('wmic process where "name like \'%{}%\'" call terminate'.format(p))
        return True

    def init_trade(self):
        if self.obj_CpTrade_CpTdUtil.TradeInit(0) != 0:
            print("TradeInit failed.", file=sys.stderr)
            return
        account_no = self.obj_CpTrade_CpTdUtil.AccountNumber[0]  # 계좌번호
        account_gflags = self.obj_CpTrade_CpTdUtil.GoodsList(account_no, 1)  # 주식상품 구분
        return account_no, account_gflags

    def order(self, action, code, amount):
        if not code.startswith('A'):
            code = 'A' + code
        account_no, account_gflags = self.init_trade()
        self.obj_CpTrade_CpTd0311.SetInputValue(0, action)  # 1: 매도, 2: 매수
        self.obj_CpTrade_CpTd0311.SetInputValue(1, account_no)  # 계좌번호
        self.obj_CpTrade_CpTd0311.SetInputValue(2, account_gflags[0])  # 상품구분
        self.obj_CpTrade_CpTd0311.SetInputValue(3, code)  # 종목코드
        self.obj_CpTrade_CpTd0311.SetInputValue(4, amount)  # 매수수량
        self.obj_CpTrade_CpTd0311.SetInputValue(8, '03')  # 시장가
        result = self.obj_CpTrade_CpTd0311.BlockRequest()
        if result != 0:
            print('order request failed.', file=sys.stderr)
        status = self.obj_CpTrade_CpTd0311.GetDibStatus()
        msg = self.obj_CpTrade_CpTd0311.GetDibMsg1()
        if status != 0:
            print('order failed. {}'.format(msg), file=sys.stderr)

    def buy(self, code, amount):
        return self.order('2', code, amount)

    def sell(self, code, amount):
        return self.order('1', code, amount)

    # def get_all_codes():
    #     objCpCodeMgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")
    #     codeList = objCpCodeMgr.GetStockListByMarket(1) # 거래소
    #     codeList2 = objCpCodeMgr.GetStockListByMarket(2) # 코스닥
    #     print("거래소 종목 코드: ")

    #     for i, code in enumerate(codeList):
    #         name = objCpCodeMgr.CodeToName(code)
    #         stdPrice = objCpCodeMgr.GetStockStdPrice(code)
    #         print(f"{i}  -  {code} - {name} - {stdPrice}")       