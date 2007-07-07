

class StdoutSquelch(object):
    """
    Redirect stdout to /dev/null

    >>> old_stdout = sys.stdout
    >>> tmp_stdout = StdoutSquelch()
    #Do stuff where you want no stdout
    >>> sys.stdout = old_stdout 


    """

    def __init__(self, filename=None):
        pass

    def write(self, buf):
        """bypass stdlib"""
        pass

    def flush(self):
        """bypass stdlib"""
        pass



