import subprocess

def risky(value):
    return eval(value)

def shell(command):
    return subprocess.run(command, shell=True)
