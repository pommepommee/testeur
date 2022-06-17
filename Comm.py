import socket
import ipaddress
import sys
import Row
import time

g_history = []
notifs = {'30': 'No more sugar', '31': 'No more bucket', '32': 'No more drink'}



class Comm:
    """
    Communication class
    Send all the primitives through the defined socket
    """

    def __init__(self, host='127.0.0.1', port=4200, timeout=5.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock = None

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        try:
            test = ipaddress.ip_address(host)
            if 'v6' in str(type(test)):
                self._sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                self._host = host
                self._sock.settimeout(self._timeout)
            elif 'v4' in str(type(test)):
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._host = host
                self._sock.settimeout(self._timeout)
            else:
                sys.exit("Only IPv4/6 supported")
        except ValueError as e:
            sys.exit(e)

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        try:
            port = int(port)
            if 1024 <= port <= 65535:
                self._port = port
            else:
                raise ValueError
        except ValueError:
            error = str(port) + " is not a valid port. (hint: 1024 <= port <= 65535)"
            sys.exit(error)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        try:
            if 0.0 <= timeout <= 30.0:
                self._timeout = timeout
            else:
                raise ValueError
        except ValueError:
            error = str(timeout) + " is not valid. (hint: 0.0 <= timeout <= 30.0)"
            sys.exit(error)

        try:
            self._sock.settimeout(self._timeout)
        except ValueError as e:
            sys.exit(e)

    def send(self, msg):
        """
        Send msg through socket to coffee machine
        """
        assert self._host is not None, "Host must be defined and valid to send"
        assert self._port is not None, "Port must be defined and valid to send"
        conn = (self._host, self._port)
        self._sock.sendto(msg, conn)

    def recv(self):
        """
        Return the message sent by the coffee machine
        """
        try:
            ret = self._sock.recv(1024)
        except (Exception,):
            ret = "Inconc".encode()
        return ret

    def send_and_recv(self, hexstring='00'):
        """
        Send hexstring through the socket and receive on the same socket
        b'Inconc' value if the coffee machine is not reachable
        """
        if not hexstring:
            hexstring = '00'
        self.send(bytes.fromhex(hexstring))
        res = self.recv()
        msg_type = res.hex()[:2]
        if msg_type in notifs.keys():
            print(str(res.hex()))
            notif = Row.Row(n="current", tpid="current", prim="Indication", obs=notifs[msg_type], ver="Indic",
                            rcvd=str(res.hex()))
            g_history.append(notif)
            res = self.recv()
        return res

    def connect(self):
        """
        Test socket connection
        """
        return self._sock.connect_ex((self._host, self._port))

    def close(self):
        """
        Close the socket connection
        """
        self._sock.close()

    # Primitives
    def UtInitialize(self):
        """
        return UtResult
            MessageType 0x01
            Success     0x00 | 0x01
        """
        return self.send_and_recv('00')

    def UtSetNbSugar(self, n_sugar=200):
        """
        return UtResult
            MessageType 0x01
            Success     0x00 | 0x01
        """
        n_sugar = format(n_sugar, '02x')
        hexa = '02' + n_sugar
        return self.send_and_recv(hexa)

    def UtSetNbBuckets(self, n_buckets=100):
        """
        return UtResult
            MessageType 0x01
            Success     0x00 | 0x01
        """
        n_buckets = format(n_buckets, '02x')
        hexa = '03' + n_buckets
        return self.send_and_recv(hexa)

    def UtSetNbDrinks(self, index=0, amount=0):
        """
        return UtResult
            MessageType 0x01
            Success     0x00 | 0x01
        """
        index = format(index, '02x')
        amount = format(amount, '02x')
        hexa = '04' + index + amount
        return self.send_and_recv(hexa)

    def UtGetInfos(self):
        """
        return UtGetInfosResult
            MessageType 0x13
            Sugar       0x00 - 0xff
            Buckets     0x00 - 0xff
            NDrinks     0x00 - 0xff
            Drinks
                LabelSize   0x00 - 0xff
                Label       string
                PriceSize   0x00 - 0xff
                Price       string
                Sugar       0x00 | 0x01
        """
        return self.send_and_recv('10')

    def UtGetPrint(self):
        """
        return UtGetPrintResult
            MessageType 0x11
            Length      0x00 - 0xff
            Value       string
        """
        return self.send_and_recv("12")

    def UtSelectDrink(self, index=0):
        """
        return UtSelectResult
            MessageType 0x20
            Success     0x00 | 0x01
        """
        index = format(index, '02x')
        hexa = '21' + index
        return self.send_and_recv(hexa)

    def UtSetSugar(self, n_sugar=0):
        """
        return UtSelectResult
            MessageType 0x20
            Success     0x00 | 0x01
        """
        n_sugar = format(n_sugar, '02x')
        hexa = '22' + n_sugar
        return self.send_and_recv(hexa)

    def UtValidate(self):
        """
        return UtSelectResult
            MessageType 0x20
            Success     0x00 | 0x01
        """
        return self.send_and_recv("23")

    def UtInsertCoin(self, coin=0):
        """
        return UtSelectResult
            MessageType 0x20
            Success     0x00 | 0x01
        """
        coin = format(coin, '02x')
        hexa = '24' + coin
        return self.send_and_recv(hexa)

    def UtGetDrink(self):
        """
        return UtSelectResult
            MessageType 0x20
            Success     0x00 | 0x01
        """
        return self.send_and_recv('25')

    def UtGetChange(self):
        """
        return UtSelectResult
            MessageType 0x20
            Success     0x00 | 0x01
        """
        return self.send_and_recv('26')
