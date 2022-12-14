
from pickle import TRUE
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module import trade_creon


a  = trade_creon.CreonTradeModule()

a.connect_api()
a.connect_database()
a.set_companies()

signal_day = a.get_signal_day()
signal_list = a.get_signals_from_core(signal_day)

holding_stocks = a.get_holding_stocks()
account_money = a.get_account_money()

print(signal_list)
print("--------------------------------------------------")
print(holding_stocks)
print("--------------------------------------------------")
print(account_money)
#57506623
