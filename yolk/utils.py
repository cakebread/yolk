

"""

utils.py
===========

Misc funcitions
---------------

run_command borrowed from Cheesecake - See CREDITS.
"""

__docformat__ = 'restructuredtext'

import os
import signal
import time
from subprocess import Popen, STDOUT



def get_yolk_dir():
    """
    Return location we store config files and data
    """
    return os.path.abspath("%s/.yolk" % os.path.expanduser("~"))


def run_command(cmd, env=None, max_timeout=None):
    """
    Run command and return its return status code and its output

    """
    arglist = cmd.split()

    output = os.tmpfile()
    try:
        pipe = Popen(arglist, stdout=output, stderr=STDOUT, env=env)
    except Exception as errmsg:
        return 1, errmsg

    # Wait only max_timeout seconds.
    if max_timeout:
        start = time.time()
        while pipe.poll() is None:
            time.sleep(0.1)
            if time.time() - start > max_timeout:
                os.kill(pipe.pid, signal.SIGINT)
                pipe.wait()
                return 1, "Time exceeded"

    pipe.wait()
    output.seek(0)
    return pipe.returncode, output.read()

def command_successful(cmd):
    """
    Returns True if command exited normally, False otherwise.

    """
    return_code, _output = run_command(cmd)
    return return_code == 0
