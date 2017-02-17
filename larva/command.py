import subprocess
from subprocess import CalledProcessError


def exec_command(cmd, timeout=None):
    res = subprocess.run(cmd, shell=True, timeout=timeout, stdout=subprocess.PIPE)
    res.stdout = res.stdout.decode('utf-8')
    return res
