import subprocess
import time
import argparse


def run_process(market_type, mode=None):
    if mode is None or market_type is None:
        return 0

    do_dict = 'no'
    collect = 'no'

    if mode == 'both':
        do_dict = 'yes'
        collect = 'yes'
    elif mode == 'dict':
        do_dict = 'yes'
    elif mode == 'collect':
        collect = 'yes'

    ret = subprocess.check_call(['python', 'nyse.py', '-type', market_type, '-dict', do_dict, '-collect', collect])
    return ret


def do_market(market_type, mode=None):
    do_run = True
    while do_run is True:
        try:
            ret = run_process(market_type, mode)
            if ret == 0:
                print 'done bail'
                do_run = False
        except:
            print 'detected error'
            time.sleep(3)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-nyse_mode', default=None)
    parser.add_argument('-nasdaq_mode', default=None)
    args = parser.parse_args()

    do_market('nyse', mode=args.nyse_mode)
    do_market('nasdaq', mode=args.nasdaq_mode)

