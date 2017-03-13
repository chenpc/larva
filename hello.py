import unittest
from larva.core import Larva


class MyError(Exception):
    pass

class Hello(object):
    def test_hello(self, msg, bool_msg=False, num=1, msg2=None, plist=None):
        """ Test Hello msg
        Args:
            msg(str): Message Test
            bool_msg(boolean): Boolean Test
            num(int): Int Test
            msg2(str): Test None
            plist(list): List None
        Returns:
            result(str): Return Test
        Raises:
            NameError(str): name of error

        """
        return (msg, bool_msg, num, msg2, plist)

if __name__ == '__main__':
    core = Larva([Hello()], host="0.0.0.0", port=8080)
    core.run()