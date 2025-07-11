import gspread
import os
import time
from gpt_rename import classify

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE26 - all woodpecker companies outreached").worksheet("companies")

start_value = 1
end_value = 6000

for i in range(start_value, end_value+1):
    time.sleep(1.5)
    name = sh.acell("a"+str(i)).value
    name = str(name)
    response = classify(name)
    sh.update_acell("b"+str(i),response)
