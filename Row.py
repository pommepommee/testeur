from datetime import datetime


class Row:
    """
    Classe Row permettant de générer les lignes du rapport
    """

    def __init__(self, n=0, tpid="NaN", prim="NaN", exp="NaN", obs="NaN", ver="NaN", req="NaN", sent="NaN", rcvd="NaN"):
        self.tpid = tpid
        self.id = n
        self.date = datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")
        self.primitive = prim
        self.expected = exp
        self.observed = obs
        self.verdict = ver
        self.requisites = req
        self.datahex_sent = sent
        self.datahex_received = rcvd
