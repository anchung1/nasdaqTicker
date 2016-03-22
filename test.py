import subprocess
import time


def run_process():
    ret = subprocess.check_call(['python', 'nyse.py'])
    return ret

do_run = True
while do_run is True:
    try:
        ret = run_process()
        if ret == 0:
            print 'done bail'
            do_run = False
    except:
        print 'detected error'
        time.sleep(3)



