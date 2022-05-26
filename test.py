
from pickle import TRUE
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from module import kis


a  = kis.KIS().get_acct_balance(TRUE)
print(a)
