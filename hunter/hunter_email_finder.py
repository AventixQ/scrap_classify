from pyhunter import PyHunter
import time

hunter = PyHunter('c98232d4704c8830cffa582ab001957d2a526c0d')
#print(hunter.account_information())

def email_find_verify(company="",first_name="", last_name=""):
    try:
        email, confidence_score = hunter.email_finder(company=company, first_name=first_name, last_name=last_name)
        status = hunter.email_verifier(email)
        #time.sleep(0.2)
        return email, confidence_score, status['status']
    except:
        return "","",""
    
def email_verify(email: str) -> str:
    return hunter.email_verifier(email)['status']

email, confidence_score, status = email_find_verify("Instagram","Kevin","Systrom")
#print(email)
#print(confidence_score)
#print(status['status'])