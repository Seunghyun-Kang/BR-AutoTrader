
from pickle import TRUE
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module.trade_creon import CreonTradeModule


a  = CreonTradeModule()

print(a.signal_list)
print("--------------------------------------------------")
print(a.holding_stocks)
print("--------------------------------------------------")
print(a.account_money)
#57506623
