
from pickle import TRUE
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module import trade_creon


a  = trade_creon.CreonTradeModule()

print(a.signal_list)
print("--------------------------------------------------")
print(a.holding_stocks)
print("--------------------------------------------------")
print(a.account_money)
#57506623
