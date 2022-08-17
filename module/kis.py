import sys

import os
import argparse
import subprocess

import time, copy
import yaml
import requests

import pandas as pd
from datetime import datetime
from collections import namedtuple
import json
import io
import abc
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

class APIResp:
    def __init__(self, resp):
        self._rescode = resp.status_code
        self._resp = resp
        self._header = self._setHeader()
        self._body = self._setBody()
        self._err_code = self._body.rt_cd
        self._err_message = self._body.msg1
        
    def getResCode(self):
        return self._rescode   
     
    def _setHeader(self):
        fld = dict()
        for x in self._resp.headers.keys():
            if x.islower():
                fld[x] = self._resp.headers.get(x)
        _th_ =  namedtuple('header', fld.keys())
        
        return _th_(**fld)
    
    def _setBody(self):
        _tb_ = namedtuple('body', self._resp.json().keys())
        
        return  _tb_(**self._resp.json())

    def getHeader(self):
        return self._header
    
    def getBody(self):
        return self._body
    
    def getResponse(self):
        return self._resp
    
    def isOK(self):
        try:
            if(self.getBody().rt_cd == '0'):
                return True
            else:
                return False
        except:
            return False
        
    def getErrorCode(self):
        return self._err_code
    
    def getErrorMessage(self):
        return self._err_message
    
    def printAll(self):
        print("<Header>")
        for x in self.getHeader()._fields:
            print(f'\t-{x}: {getattr(self.getHeader(), x)}')
        print("<Body>")
        for x in self.getBody()._fields:        
            print(f'\t-{x}: {getattr(self.getBody(), x)}')
            
    def printError(self):
        print('-------------------------------\nError in response: ', self.getResCode())
        print(self.getBody().rt_cd, self.getErrorCode(), self.getErrorMessage()) 
        print('-------------------------------')           


          
class KIS:
    def __init__(self):
        with open(r'kisdev_vi.yaml', encoding='UTF-8') as f:
            self._cfg = yaml.load(f, Loader=yaml.FullLoader)

        self._TRENV = tuple()
        self._last_auth_time = datetime.now()
        self._autoReAuth = False
        self._DEBUG = True
        self._isPaper = True
        self._base_headers = {
                    "Content-Type": "application/json",
                    "Accept": "text/plain",
                    "charset": "UTF-8",
                    'User-Agent': self._cfg['my_agent']
                }
        print(self._cfg)
        self.auth()
        
    # 계좌 잔고 액수 반환
    def get_acct_remains(self, kakao):
        url = '/uapi/overseas-stock/v1/trading/inquire-present-balance'
        tr_id = "CTRP6504R"

        params = {
            'CANO': self.getTREnv().my_acct, 
            'ACNT_PRDT_CD': '01', 
            'WCRC_FRCR_DVSN_CD': '02', 
            'NATN_CD': '840', 
            'TR_MKET_CD': '00', 
            'INQR_DVSN_CD': '00'
            }

        t1 = self._url_fetch(url, tr_id, params)
        try:
            output2 = t1.getBody().output2
            output1 = t1.getBody().output1
            output3 = t1.getBody().output3
            tr_count = t1.getHeader().tr_cont
            if tr_count == 'D' or tr_count == 'E':
                kakao.send_msg_to_me(f"-----------------\n@@@@@@@@@@@페이지 증가 확인 필요@@@@@@@@@@\n------------------\n")
            print(output3)
            if t1.getBody().rt_cd == '0':  #body 의 rt_cd 가 0 인 경우만 성공
                df1 = pd.DataFrame(output1)
                using_column = ['pdno', 'prdt_name', 'evlu_pfls_rt1', 'ccld_qty_smtl1','frcr_evlu_amt2', 'frcr_pchs_amt', 'evlu_pfls_amt2']
                df1 = df1[using_column]
                df1 = df1.rename(columns={'pdno':'코드', 'prdt_name':'종목명', 'evlu_pfls_rt1':'수익률', 'ccld_qty_smtl1':'수량','frcr_evlu_amt2':'평가금액', 'frcr_pchs_amt':'매입금액', 'evlu_pfls_amt2':'평가손익'})

                df = pd.DataFrame(output2)
                using_column = ['frcr_dncl_amt_2', 'frcr_drwg_psbl_amt_1', 'frcr_buy_mgn_amt','frst_bltn_exrt']
                df = df[using_column]
                df = df.rename(columns={'frcr_dncl_amt_2':'외화잔고', 'frcr_drwg_psbl_amt_1':'사용가능', 'frcr_buy_mgn_amt':'매수증거금', 'frst_bltn_exrt':'환율'})
                
                # df3 = pd.DataFrame(output3)
                # # using_column = ['tot_asst_amt']
                # # df3 = df3[using_column]
                # # df3 = df3.rename(columns={'tot_asst_amt':'총자산금액'})
                # print(df3)
                
                return df1, df
            else:
                t1.printError()
                return pd.DataFrame()
        except:
            print("ERROR IN REQUEST")  
        
    def get_total_assets(self):
        url = '/uapi/overseas-stock/v1/trading/inquire-present-balance'
        tr_id = "CTRP6504R"

        params = {
            'CANO': self.getTREnv().my_acct, 
            'ACNT_PRDT_CD': '01', 
            'WCRC_FRCR_DVSN_CD': '02', 
            'NATN_CD': '840', 
            'TR_MKET_CD': '00', 
            'INQR_DVSN_CD': '00'
            }

        t1 = self._url_fetch(url, tr_id, params)
        try:
            output3 = t1.getBody().output3
            print("@@@@@@@@@@@@@@")
            print(output3)
            if t1.getBody().rt_cd == '0':  #body 의 rt_cd 가 0 인 경우만 성공
                return float(output3['tot_asst_amt'])
            else:
                t1.printError()
                return None
        except:
            print("ERROR IN REQUEST")  
    # 계좌 잔고를 DataFrame 으로 반환
    # Input: None (Option) rtCashFlag=True 면 예수금 총액을 반환하게 된다
    # Output: DataFrame (Option) rtCashFlag=True 면 예수금 총액을 반환하게 된다
    def get_acct_balance(self, rtCashFlag=False):
        url = '/uapi/overseas-stock/v1/trading/inquire-balance'
        tr_id = "JTTT3012R"

        params = {
            'CANO': self.getTREnv().my_acct, 
            'ACNT_PRDT_CD': '01', 
            'OVRS_EXCG_CD': 'NASD', 
            'TR_CRCY_CD': 'USD', 
            'CTX_AREA_FK200': '', 
            'CTX_AREA_NK200': ''
            }

        t1 = self._url_fetch(url, tr_id, params)
        if rtCashFlag and t1.isOK():
            r2 = t1.getBody().output2
            return t1.getBody().msg1
        try:
            output1 = t1.getBody().output1
            output2 = t1.getBody().output2
            if t1.isOK() and output1 and output2:  #body 의 rt_cd 가 0 인 경우만 성공
                df = pd.DataFrame(output1)
                using_column = ['ovrs_pdno', 'ovrs_item_name', 'frcr_evlu_pfls_amt', 'evlu_pfls_rt', 'ovrs_cblc_qty','now_pric2','ord_psbl_qty']
                df = df[using_column]
                df = df.rename(columns={'ovrs_pdno':'코드', 'ovrs_item_name':'종목명', 'frcr_evlu_pfls_amt':'실현손익', 'evlu_pfls_rt':'수익률', 'ovrs_cblc_qty':'수량','now_pric2':'가격','ord_psbl_qty':'매도가능수량'})
                return df                
            else:
                t1.printError()
                return pd.DataFrame()
        except:
            print("ERROR IN REQUEST")  
     
    # 종목별 현재가를 dict 로 반환
    # Input: 종목코드
    # Output: 현재가 Info dictionary. 반환된 dict 가 len(dict) < 1 경우는 에러로 보면 됨

    def get_current_price(self, stock_no):
        url = "/uapi/overseas-stock/v1/quotations/inquire-price"
        tr_id = "FHKST01010100"

        params = {
            'FID_COND_MRKT_DIV_CODE': 'J', 
            'FID_INPUT_ISCD': stock_no
            }
        
        t1 = self._url_fetch(url, tr_id, params)
        
        if t1.isOK():
            return t1.getBody().output
        else:
            t1.printError()
            return dict()

    # 주문 base function
    # Input: 종목코드, 주문수량, 주문가격, Buy Flag(If True, it's Buy order), order_type="00"(지정가)
    # Output: HTTP Response

    def do_order(self, excg_code ,stock_code, order_qty, order_price, kakao,name, prd_code="01", buy_flag=True, order_type="00"):

        url = "/uapi/overseas-stock/v1/trading/order"
        type = ""
        msg_type = ""
        if buy_flag:
            tr_id = "JTTT1002U"  #buy
            msg_type = "매수"
        else:
            tr_id = "JTTT1006U"  #sell
            type= "00"
            msg_type = "매도"

        params = {
            'CANO': self.getTREnv().my_acct, 
            'ACNT_PRDT_CD': prd_code, 
            'OVRS_EXCG_CD': excg_code,
            'OVRS_ORD_UNPR':str(order_price),
            'PDNO': stock_code, 
            'ORD_DVSN': order_type, 
            'ORD_QTY': str(order_qty), 
            'CTAC_TLNO': '', 
            'ORD_SVR_DVSN_CD': '0',
            'SLL_TYPE': type, 
            }
        
        t1 = self._url_fetch(url, tr_id, params, postFlag=True, hashFlag=True)
        try:
            if t1.isOK():
                kakao.send_msg_to_me(f"-----------------\n한국투자 미국 주식 접수완료\n------------------\n {msg_type}: {name}\n")
                
            else:
                kakao.send_msg_to_me(f"-----------------\n한국투자 미국 주식 접수실패\n------------------\n {msg_type}: {name}\n")
                
        except:
            kakao.send_msg_to_me(f"-----------------\n한국투자 미국 주식 접수실패\n------------------\n {msg_type}: {name}\n")
            

    # 사자 주문. 내부적으로는 do_order 를 호출한다.
    # Input: 종목코드, 주문수량, 주문가격
    # Output: True, False

    def do_sell(self, excg_code ,stock_code, order_qty, order_price, kakao, name, prd_code="01", order_type="00"):
        t1 = self.do_order(excg_code, stock_code, order_qty, order_price, kakao,name, prd_code, buy_flag=False, order_type=order_type)
        

    # 팔자 주문. 내부적으로는 do_order 를 호출한다.
    # Input: 종목코드, 주문수량, 주문가격
    # Output: True, False

    def do_buy(self, excg_code , stock_code, order_qty, order_price, kakao,name, prd_code="01", order_type="00"):
        t1 = self.do_order(excg_code, stock_code, order_qty, order_price, kakao,name, prd_code, buy_flag=True, order_type=order_type)
        



    # 내 계좌의 일별 주문 체결 조회
    # Input: 시작일, 종료일 (Option)지정하지 않으면 현재일
    # output: DataFrame

    def get_my_complete(self, sdt, edt=None, prd_code='01', zipFlag=True):
        url = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        tr_id = "TTTC8001R"

        if (edt is None):
            ltdt = datetime.now().strftime('%Y%m%d')
        else:
            ltdt = edt
            
        params = {
            "CANO": self.getTREnv().my_acct,
            "ACNT_PRDT_CD": prd_code,
            "INQR_STRT_DT": sdt,
            "INQR_END_DT": ltdt,
            "SLL_BUY_DVSN_CD": '00',
            "INQR_DVSN": '00',
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO":"",
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "INQR_DVSN_2": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        t1 = self._url_fetch(url, tr_id, params)

        #output1 과 output2 로 나뉘어서 결과가 옴. 지금은 output1만 DF 로 변환
        if t1.isOK():
            tdf = pd.DataFrame(t1.getBody().output1)
            tdf.set_index('odno', inplace=True)  
            if (zipFlag):
                return tdf[['ord_dt','orgn_odno', 'sll_buy_dvsn_cd_name', 'pdno', 'ord_qty', 'ord_unpr', 'avg_prvs', 'cncl_yn','tot_ccld_amt','rmn_qty']]
            else:
                return tdf
        else:
            t1.printError()
            return pd.DataFrame()


    # 매수 가능(현금) 조회
    # Input: None
    # Output: 매수 가능 현금 액수
    def get_buyable_cash(self, stock_code='', qry_price=0, prd_code='01'):
        url = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        tr_id = "TTTC8908R"

        params = {
            "CANO": self.getTREnv().my_acct,
            "ACNT_PRDT_CD": prd_code,
            "OVRS_EXCG_CD": "NASD",
            "PDNO": stock_code,
            "ORD_UNPR": str(qry_price),
            "ORD_DVSN": "02", 
            "CMA_EVLU_AMT_ICLD_YN": "Y", #API 설명부분 수정 필요 (YN)
            "OVRS_ICLD_YN": "N"
        }

        t1 = self._url_fetch(url, tr_id, params)

        if t1.isOK():
            return int(t1.getBody().output['ord_psbl_cash'])
        else:
            t1.printError()
            return 0

    def _getBaseHeader(self):
        if self._autoReAuth: self.reAuth()
        return copy.deepcopy(self._base_headers)

    def _setTRENV(self, cfg):
        nt1 = namedtuple('KISEnv', ['my_app','my_sec','my_acct', 'my_prod', 'my_token', 'my_url'])
        d = {
            'my_app': cfg['my_app'],
            'my_sec': cfg['my_sec'],
            'my_acct': cfg['my_acct'],
            'my_prod': cfg['my_prod'],
            'my_token': cfg['my_token'],
            'my_url' : cfg['my_url']
        }
        
        self._TRENV = nt1(**d)

    def isPaperTrading(self):
        return self._isPaper

    def changeTREnv(self, token_key, svr='prod', product='01'):
        cfg = dict()

        if svr == 'prod':
            ak1 = 'my_app'
            ak2 = 'my_sec'
            self._isPaper = False
        elif svr == 'vps':
            ak1 = 'paper_app'
            ak2 = 'paper_sec'
            self._isPaper = True
            
        cfg['my_app'] = self._cfg[ak1]
        cfg['my_sec'] = self._cfg[ak2]   
        
        if svr == 'prod' and product == '01':
            cfg['my_acct'] = self._cfg['my_acct_stock']
        elif svr == 'prod' and product == '03':
            cfg['my_acct'] = self._cfg['my_acct_future']
        elif svr == 'vps' and product == '01':        
            cfg['my_acct'] = self._cfg['my_paper_stock']
        elif svr == 'vps' and product == '03':        
            cfg['my_acct'] = self._cfg['my_paper_future']

        cfg['my_prod'] = product
        cfg['my_token'] = token_key
        cfg['my_url'] = self._cfg[svr] 
        
        self._setTRENV(cfg)

    def _getResultObject(self, json_data):
        _tc_ = namedtuple('res', json_data.keys())
                
        return _tc_(**json_data)
        
    def auth(self, svr='prod', product='01'):

        p = {
            "grant_type": "client_credentials",
        }
        print(svr)
        if svr == 'prod':
            ak1 = 'my_app'
            ak2 = 'my_sec'
        elif svr == 'vps':
            ak1 = 'paper_app'
            ak2 = 'paper_sec'
            
        p["appkey"] = self._cfg[ak1]
        p["appsecret"] = self._cfg[ak2]
        

        url = f'{self._cfg[svr]}/oauth2/tokenP'

        res = requests.post(url, data=json.dumps(p), headers=self._getBaseHeader())
        rescode = res.status_code
        if rescode == 200:
            my_token = self._getResultObject(res.json()).access_token
        else:
            print('Get Authentification token fail!\nYou have to restart your app!!!')  
            return
    
        self.changeTREnv(f"Bearer {my_token}", svr, product)
        
        self._base_headers["authorization"] = self._TRENV.my_token
        self._base_headers["appkey"] = self._TRENV.my_app
        self._base_headers["appsecret"] = self._TRENV.my_sec
        
        self._last_auth_time = datetime.now()
        
        if (self._DEBUG):
            print(f'[{self._last_auth_time}] => get AUTH Key completed!')

    def reAuth(self, svr='prod', product='01'):
        n2 = datetime.now()
        if (n2-self._last_auth_time).seconds >= 86400:
            self.auth(svr, product) 

    def getEnv(self):
        return self._cfg
    def getTREnv(self):
        return self._TRENV

    def set_order_hash_key(self, h, p):
    
        url = f"{self.getTREnv().my_url}/uapi/hashkey"
        print(json.dumps(p))
        res = requests.post(url, data=json.dumps(p), headers=h)
        rescode = res.status_code
        if rescode == 200:
            h['hashkey'] = self._getResultObject(res.json()).HASH
        else:
            print("Error:", rescode)
    
    def _url_fetch(self, api_url, ptr_id, params, appendHeaders=None, postFlag=False, hashFlag=True):
        url = f"{self.getTREnv().my_url}{api_url}"
        
        headers = self._getBaseHeader()

        #추가 Header 설정
        tr_id = ptr_id
        if ptr_id[0] in ('T', 'J', 'C'):
            if self.isPaperTrading():
                tr_id = 'V' + ptr_id[1:]

        headers["tr_id"] = tr_id
        headers["custtype"] = "P"
        
        if appendHeaders is not None:
            if len(appendHeaders) > 0:
                for x in appendHeaders.keys():
                    headers[x] = appendHeaders.get(x)

        if(self._DEBUG):
            print("< Sending Info >")
            print(f"URL: {url}, TR: {tr_id}")
            print(f"<header>\n{headers}")
            print(f"<body>\n{params}")
            
        if (postFlag):
            if(hashFlag): self.set_order_hash_key(headers, params)
            res = requests.post(url, headers=headers, data=json.dumps(params))
        else:
            res = requests.get(url, headers=headers, params=params)

        if res.status_code == 200:
            ar = APIResp(res)
            if (self._DEBUG): ar.printAll()
            return ar
        else:
            print("Error Code : " + str(res.status_code) + " | " + res.text)
            return None
