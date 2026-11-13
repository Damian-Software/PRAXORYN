"""Synthetic practice code only; do not copy into production."""
import subprocess

def calculate(expression):
    return eval(expression)

def run_untrusted(argument):
    return subprocess.run('printf ' + argument, shell=True, check=False)

def swallow():
    try:
        print(1/0)
    except:
        pass

breakpoint()
