import os

ENABLE_PRINT = True

def cprint(msg=''):
    if ENABLE_PRINT:
        local_msg = msg
        if os.name == 'nt': #Check Windows(nt)
            pass
            # with open('D:/proxy_logs.log', 'a') as f:
            #     print(local_msg, file=f)
        else:
            with open('/var/app_middleware_logs.log', 'a') as f:
                print(local_msg, file=f)