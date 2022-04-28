import win32com.client
import sys

import os
import argparse
import subprocess
import time
import io
import abc
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

from pywinauto import application

class Creon:
    def __init__(self, file):
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
        self.obj_Dscbo1_StockMst = win32com.client.Dispatch('Dscbo1.StockMst')
        bConnect = self.obj_CpUtil_CpCybos.IsConnect
        self.file = file 

        self.stockcur_handlers = {}  # 주식/업종/ELW시세 subscribe event handlers
        self.stockbid_handlers = {}  # 주식/ETF/ELW 호가, 호가잔량 subscribe event handlers
        self.orderevent_handler = None
    
    def wait(self):
        remain_time = self.obj_CpUtil_CpCybos.LimitRequestRemainTime
        remain_count = self.obj_CpUtil_CpCybos.GetLimitRemainCount(1)
        if remain_count <= 3:
            time.sleep(remain_time / 1000)

    def request(self, obj, data_fields, header_fields=None, cntidx=0, n=None):
        def process():
            obj.BlockRequest()

            status = obj.GetDibStatus()
            msg = obj.GetDibMsg1()
            if status != 0:
                return None

            cnt = obj.GetHeaderValue(cntidx)
            data = []
            for i in range(cnt):
                dict_item = {k: obj.GetDataValue(j, cnt-1-i) for j, k in data_fields.items()}
                data.append(dict_item)
            return data

        # 연속조회 처리
        data = process()
        while obj.Continue:
            self.wait()
            _data = process()
            if len(_data) > 0:
                data = _data + data
                if n is not None and n <= len(data):
                    break
            else:
                break

        result = {'data': data}
        if header_fields is not None:
            result['header'] = {k: obj.GetHeaderValue(i) for i, k in header_fields.items()}

        return result

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
        self.file.write(f'주문->>>>> {code} - {action} - {result}\n')
        if result != 0:
            print('order request failed.', file=sys.stderr)
            self.file.write(f'RESULT {code} 주문 요청 실패!!!\n')
        status = self.obj_CpTrade_CpTd0311.GetDibStatus()
        msg = self.obj_CpTrade_CpTd0311.GetDibMsg1()
        if status != 0:
            print('order failed. {}'.format(msg), file=sys.stderr)
            self.file.write(f'STATUS {code} 주문 요청 실패!!!\n\n')

    def buy(self, code, amount):
        return self.order('2', code, amount)

    def sell(self, code, amount):
        return self.order('1', code, amount)

    def get_stock_info(self, code):
        if not code.startswith('A'):
            code = 'A' + code
        self.obj_Dscbo1_StockMst.SetInputValue(0, code)
        self.obj_Dscbo1_StockMst.BlockRequest()

        item ={}
        item['cur_price'] = self.obj_Dscbo1_StockMst.GetHeaderValue(11)
        item['ask'] = self.obj_Dscbo1_StockMst.GetHeaderValue(16)
        item['bid'] = self.obj_Dscbo1_StockMst.GetHeaderValue(17)

        return item['cur_price'], item['ask'], item['bid']

    def get_balance(self):
        """
        매수가능금액
        """
        account_no, account_gflags = self.init_trade()
        self.obj_CpTrade_CpTdNew5331A.SetInputValue(0, account_no)
        self.obj_CpTrade_CpTdNew5331A.SetInputValue(1, account_gflags[0])
        self.obj_CpTrade_CpTdNew5331A.BlockRequest()
        v = self.obj_CpTrade_CpTdNew5331A.GetHeaderValue(9)
        return v
    
    def get_holdingstocks(self):
        """
        보유종목
        """
        account_no, account_gflags = self.init_trade()
        self.obj_CpTrade_CpTdNew5331B.SetInputValue(0, account_no)
        self.obj_CpTrade_CpTdNew5331B.SetInputValue(3, ord('1')) # 1: 주식, 2: 채권
        self.obj_CpTrade_CpTdNew5331B.BlockRequest()
        cnt = self.obj_CpTrade_CpTdNew5331B.GetHeaderValue(0)
        res = []
        for i in range(cnt):
            item = {
                'code': self.obj_CpTrade_CpTdNew5331B.GetDataValue(0, i),
                'name': self.obj_CpTrade_CpTdNew5331B.GetDataValue(1, i),
                'holdnum': self.obj_CpTrade_CpTdNew5331B.GetDataValue(6, i),
                'buy_yesterday': self.obj_CpTrade_CpTdNew5331B.GetDataValue(7, i),
                'sell_yesterday': self.obj_CpTrade_CpTdNew5331B.GetDataValue(8, i),
                'buy_today': self.obj_CpTrade_CpTdNew5331B.GetDataValue(10, i),
                'sell_today': self.obj_CpTrade_CpTdNew5331B.GetDataValue(11, i),
            }
            res.append(item)
        return res

    def get_trade_history(self):
        account_no, account_gflags = self.init_trade()
        self.obj_CpTrade_CpTd5341.SetInputValue(0, account_no)
        self.obj_CpTrade_CpTd5341.SetInputValue(1, account_gflags[0])  # 상품구분

        _fields = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 22, 24]
        _keys = [
            '상품관리구분코드', '주문번호', '원주문번호', '종목코드', '종목이름', 
            '주문내용', '주문호가구분코드내용', '주문수량', '주문단가', '총체결수량', 
            '체결수량', '체결단가', '확인수량', '정정취소구분내용 ', '거부사유내용', 
            '채권매수일', '거래세과세구분내용', '현금신용대용구분내용', '주문입력매체코드내용', 
            '정정취소가능수량', '매매구분',
        ]

        result = self.request(self.obj_CpTrade_CpTd5341, dict(zip(_fields, _keys)), cntidx=6)
        return result

    def subscribe_orderevent(self, cb):
        obj = win32com.client.Dispatch('Dscbo1.CpConclusion')
        handler = win32com.client.WithEvents(obj, OrderEventHandler)
        handler.set_attrs(obj, cb)
        self.orderevent_handler = obj
        obj.Subscribe()

    def unsubscribe_orderevent(self):
        if self.orderevent_handler is not None:
            self.orderevent_handler.Unsubscribe()
            self.orderevent_handler = None
class EventHandler:
    # 실시간 조회(subscribe)는 최대 400건

    def set_attrs(self, obj, cb):
        self.obj = obj
        self.cb = cb

    @abc.abstractmethod
    def OnReceived(self):
        pass

class OrderEventHandler(EventHandler):
    def OnReceived(self):
        item = {
            '계좌명': self.obj.GetHeaderValue(1),
            'name': self.obj.GetHeaderValue(2),
            '체결수량': self.obj.GetHeaderValue(3),
            '체결가격': self.obj.GetHeaderValue(4),
            '주문번호': self.obj.GetHeaderValue(5),
            '원주문번호': self.obj.GetHeaderValue(6),
            '계좌번호': self.obj.GetHeaderValue(7),
            '상품관리구분코드': self.obj.GetHeaderValue(8),
            '종목코드': self.obj.GetHeaderValue(9),
            '매매구분코드': self.obj.GetHeaderValue(12),
            '체결구분코드': self.obj.GetHeaderValue(14),
            '현금신용대용구분코드': self.obj.GetHeaderValue(17),
        }
        self.cb(item)

    # def get_all_codes():
    #     objCpCodeMgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")
    #     codeList = objCpCodeMgr.GetStockListByMarket(1) # 거래소
    #     codeList2 = objCpCodeMgr.GetStockListByMarket(2) # 코스닥
    #     print("거래소 종목 코드: ")

    #     for i, code in enumerate(codeList):
    #         name = objCpCodeMgr.CodeToName(code)
    #         stdPrice = objCpCodeMgr.GetStockStdPrice(code)
    #         print(f"{i}  -  {code} - {name} - {stdPrice}")       