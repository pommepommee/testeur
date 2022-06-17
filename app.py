from Comm import *
import Row
from flask import Flask, render_template, request
import argparse as ap
import csv
import json

# Globals
g_coins = {0: 0.1, 1: 0.2, 2: 0.5, 3: 1.0, 4: 2.0}
g_result = ''
g_headers = ["tpid", "id", "date", "primitive", "expected", "observed", "verdict", "requisites", "datahex_sent",
             "datahex_received"]
g_fails = ['Inconc', 'Fail', 'Error']

with open('CoffeeMachine_windows/config.json', 'r') as conf:
    j = json.load(conf)
    g_pixit = j["strings"]

app = Flask(__name__, template_folder='./templates')
comm = Comm()


def h(st):
    """
    Return -- if possible -- the hexstring of @st, otherwise, return 00
    """
    try:
        ret = str(bytes.fromhex(st).hex())
    except (Exception,):
        ret = "00"
    return ret


def get_infos(bts): 
    """
    If possible, parse the infos returned by the primitive UtGetInfos, else return b'Inconc'
    """
    try:
        sugar, buckets, nb_drinks, drinks = bts[1], bts[2], bts[3], []
        data_drinks = bts[4:]
        cur = 0
        for idx in range(nb_drinks):
            drk = {"index": idx}
            label_size = data_drinks[cur]
            cur += 1
            drk["label"] = data_drinks[cur:cur+label_size].decode('utf-8')
            cur += label_size
            price_size = data_drinks[cur]
            cur += 1
            drk["price"] = data_drinks[cur:cur+price_size].decode('utf-8')
            cur += price_size
            drk["sweet"] = data_drinks[cur]
            drinks.append(drk)
            cur += 1
        infos = {'sugar': sugar, 'buckets': buckets, 'nbdrinks': nb_drinks, 'drinks': drinks}
    except (Exception,):
        infos = "Inconc".encode()
    return infos


def test_ut_result(res, row):
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.datahex_received = res.hex()
        if res[1] == 1:
            row.observed = "UtResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtResult.Success == ERROR"
            row.verdict = 'Fail'


def pay_exact(price=0.0):
    """
    Returns a list of coins of g_coins to insert to pay the exact price parameter
    Example:
        price = 6.3
        g_coins = {0: 0.1, 1: 0.2, 2: 0.5, 3: 1.0, 4: 2.0}
        Returns : [4, 4, 4, 1, 0]
    """
    to_pay = []
    i = 4

    while price > 0:
        if price >= g_coins[i]:
            to_pay.append(i)
            price -= g_coins[i]
            price = round(price, 2)
        else:
            i -= 1
    return to_pay


def tp1():
    """
    Tant qu’aucune boisson n’est sélectionnée, aucun prix n’est affiché
    """
    tpid = "TP/CF/DR/BV-01"
    n: int = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp="Print "+g_pixit["chooseDrinkText"], sent=h('12'))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.datahex_received = str(res.hex())
        row.observed = res
        res = res[2:]
        if res.decode() == g_pixit["chooseDrinkText"]:
            row.observed = g_pixit["chooseDrinkText"]
            row.verdict = 'Pass'
        else:
            row.verdict = 'Fail'
    g_history.append(row)


def tp2():
    """
    Tant qu’aucune boisson n’est sélectionnée, la boisson ne peut pas être validée
    """
    tpid = "TP/CF/DR/BV-02"
    res = comm.UtInitialize()
    n = 0
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="Cannot validate (UtValidateResult == ERROR)", sent=h('23'))
    row.datahex_received = str(res.hex())
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 0:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Fail'
    g_history.append(row)


def tp3(idx=0):
    """
    Lorsqu’une boisson est sélectionnée, son prix est affiché
    """
    tpid = "TP/CF/DR/BV-03"
    h_idx = format(idx, '02x')
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="Select drink {}".format(idx), sent=h('21')+h_idx)
    row.datahex_received = str(res.hex())
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Print machine's information", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    drink_price = ""
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            for key in infos["drinks"]:
                if idx == key["index"]:
                    drink_price = key["price"]
                    row.verdict = "Pass"
                    # row.observed = json.dumps(infos)
                    # pprint(infos)
                    row.observed = "infos"
        except (Exception,):
            row.verdict = "Fail"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp="Print price of drink {} ({})".format(idx, drink_price), sent=h('12'),
                  rcvd=str(res.hex()))
    res = res[2:]
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.observed = res.decode('utf-8')
        if res == drink_price.encode():
            row.verdict = "Pass"
        else:
            row.verdict = "Fail"
    g_history.append(row)


def tp4(first_drink_idx=0, second_drink_idx=1):
    """
    Lorsqu’on sélectionne une boisson, puis une autre, le prix affiché est mis à jour
    """
    tpid = "TP/CF/DR/BV-04"
    h_first, h_second = format(first_drink_idx, '02x'), format(second_drink_idx, '02x')
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Machine's information", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    first_drink_price = ""
    second_drink_price = ""
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            for key in infos["drinks"]:
                if first_drink_idx == key["index"]:
                    first_drink_price = key["price"]
                if second_drink_idx == key["index"]:
                    second_drink_price = key["price"]
            row.verdict = "Pass"
            # row.observed = json.dumps(infos)
            row.observed = "infos"
            # pprint(infos)
        except (Exception,):
            row.verdict = "Fail"
    g_history.append(row)

    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(first_drink_idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {first_drink_idx}", exp="UtSelectResult == SUCCESS", sent=h('21')+h_first)
    row.datahex_received = str(res.hex())
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp=first_drink_price, sent=h('12'), rcvd=str(res.hex()))
    res = res[2:]
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.observed = res.decode('utf-8')
        if res == first_drink_price.encode():
            row.verdict = "Pass"
        else:
            row.verdict = "Fail"
    g_history.append(row)

    res = comm.UtSelectDrink(second_drink_idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {second_drink_idx}", exp="UtSelectResult == SUCCESS", sent=h('21')+h_second)
    row.datahex_received = str(res.hex())
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp=second_drink_price, sent=h('12'), rcvd=str(res.hex()))
    res = res[2:]
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.observed = res.decode('utf-8')
        if res == second_drink_price.encode():
            row.verdict = "Pass"
        else:
            row.verdict = "Fail"
    g_history.append(row)


def tp5(idx=0, sugar=5):
    """
    Lorsqu’une boisson est sélectionnée, il est possible de sélectionner le taux de sucre
    """
    tpid = "TP/CF/DR/BV-05"
    h_idx, h_sugar = format(idx, '02x'), format(sugar, '02x')
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        row.verdict = "Pass"
        row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21')+h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetSugar(sugar)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetSugar with sugar={sugar}", exp="UtSelectResult.Success == SUCCESS", sent=h('22')+h_sugar, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)


def tp6(idx=8, sugar=5):
    """
    Si une boisson n’a pas de sucre, le taux de sucre ne peut pas être modifié
    """
    tpid = "TP/CF/DR/BV-06"
    h_idx, h_sugar = format(idx, '02x'), format(sugar, '02x')
    n, max_idx = 0, 255
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="The chosen drink cannot be sweetened", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        max_idx = infos["nbdrinks"]
        row.requisites = f"0 <= idx <= {max_idx - 1}"

        if idx >= max_idx:
            row.verdict = "Error"
            row.observed = f"Index {idx} out of drink range"
        else:
            can_be_sugared = 0
            if infos == "Inconc".encode():
                row.verdict = "Inconc"
            else:
                try:
                    for key in infos["drinks"]:
                        if idx == key["index"]:
                            can_be_sugared = key["sweet"]

                    if can_be_sugared:
                        row.verdict = "Fail"
                        row.observed = f"The drink at index {idx} can be sweetened"
                    else:
                        row.verdict = "Pass"
                        row.observed = f"The drink at index {idx} cannot be sweetened"

                except (Exception,):
                    row.verdict = "Fail"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21')+h_idx, rcvd=str(res.hex()))
    row.requisites = f"0 <= idx <= {max_idx - 1}"
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetSugar(sugar)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetSugar amount = {sugar}", exp="UtSelectResult.Success == ERROR", sent=h('22') + h_sugar, rcvd=str(res.hex()))
    row.requisites = f"0 <= sugar <= 10"
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp7(sugar=11):
    """
    Le nombre d’unités de sucre ne peut pas être plus grand que 10
    """
    tpid = "TP/CF/DR/BV-07"
    drinks = None
    h_sugar = format(sugar, '02x')
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get first drink that can be sweetened", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = [drink for drink in infos["drinks"] if drink["sweet"] == 1]
            row.verdict = "Pass"
            row.observed = drinks[0]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "No drinks that can be sweetened"
    g_history.append(row)
    if row.verdict in g_fails:
        return
    idx = drinks[0]['index']
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetSugar(sugar)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetSugar with amount = {sugar}", exp="UtSelectResult.Success == ERROR", sent=h('22') + h_sugar, rcvd=str(res.hex()))
    row.requisites = f"11 <= sugar <= 255"
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp8(sugar=-1):
    """
    Le nombre d’unités de sucre ne peut pas être plus petit que 0
    """
    tpid = "TP/CF/DR/BV-08"
    n = 0
    row = Row.Row(n=n, prim="Impossible to negatives hexa", tpid=tpid)
    if sugar < 0:
        row.verdict = "Error"
        row.observed = f"Cannot negatives amount to the coffee machine"
    else:
        row.verdict = "Inconc"
    g_history.append(row)


def tp9():
    """
    Tant qu’aucune boisson n’est validée, il n’est pas possible d’insérer de pièces
    """
    tpid = "TP/CF/DR/BV-09"
    n = 0
    drinks = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get first drink of list", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks[0]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]
    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for i in range(5):
        res = comm.UtInsertCoin(i)
        n += 1
        row = Row.Row(n=n, prim=f"UtInsertCoin({i}) (coin value = {g_coins[i]} €)", tpid=tpid,
                      exp="UtSelectResult.Success == ERROR", sent=h('24') + format(i, '02x'), rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult.Success == SUCCESS"
                row.verdict = 'Fail'
            else:
                row.observed = "UtSelectResult.Success == ERROR"
                row.verdict = 'Pass'
        g_history.append(row)


def tp10():
    """
    Tant qu’aucune boisson n’est validée, il n’est pas possible de récupérer le rendu monnaie
    """
    tpid = "TP/CF/DR/BV-10"
    n = 0
    drinks = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get first drink of list", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks[0]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]
    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetChange()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetChange", exp="UtSelectResult.Success == ERROR", sent=h("26"), rcvd=(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp11():
    """
    Tant qu’aucune boisson n’est validée, il n’est pas possible de récupérer de boisson
    """
    tpid = "TP/CF/DR/BV-11"
    n = 0
    drinks = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get first drink of list", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks[0]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]
    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetChange()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetChange", exp="UtSelectResult.Success == ERROR", sent=h("26"), rcvd=(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp12():
    """
    Lorsqu’une boisson est validée, il n’est pas possible de sélectionner une boisson
    """
    tpid = "TP/CF/DR/BV-12"
    n = 0
    drinks = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get list of drinks indexes", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            idxs = [drink["index"] for drink in drinks]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = idxs
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]
    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)

    for drink in drinks:
        cur_idx = drink["index"]
        h_idx = format(cur_idx, '02x')
        res = comm.UtSelectDrink(cur_idx)
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {cur_idx}", exp="UtSelectResult.Success == ERROR", sent=h('21') + h_idx, rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtValidateResult == SUCCESS"
                row.verdict = 'Fail'
            else:
                row.observed = "UtValidateResult == ERROR"
                row.verdict = 'Pass'
        g_history.append(row)


def tp13():
    """
    Lorsqu’une boisson est validée, il est possible d’insérer de la monnaie
    """
    tpid = "TP/CF/DR/BV-13"
    n = 0
    drinks = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get list of drinks indexes", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            idxs = [drink["index"] for drink in drinks]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = idxs
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]
    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    coin = 4
    res = comm.UtInsertCoin(coin)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]} €)", exp="UtSelectResult.Success == SUCCESS", sent=h('24') + format(coin, '02x'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)


def tp14():
    """
    Tant que la boisson n’est pas entièrement payée, il n’est pas possible de récupérer le rendu monnaie
    """
    tpid = "TP/CF/DR/BV-14"
    n = 0
    drinks, price = None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="", exp="Get list of drinks", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]

    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtInsertCoin(0)
    h_coin = format(0, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({0} (coin value = {g_coins[0]})", exp="UtSelectResult == SUCCESS", sent=h('24') + h_coin, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetChange()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetChange", exp="UtSelectResult.Success == ERROR", sent=h('26'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp15():
    """
    Tant que la boisson n’est pas entièrement payée, il n’est pas possible de récupérer de boisson
    """
    tpid = "TP/CF/DR/BV-15"
    n = 0
    drinks, price = None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get list of drinks", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]

    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtInsertCoin(0)
    h_coin = format(0, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({0}) (coin value = {g_coins[0]}", exp="UtSelectResult == SUCCESS", sent=h('24') + h_coin, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetDrink()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == ERROR", sent=h('25'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp16():
    """
    Tant que la boisson n’est pas entièrement payée, il n’est pas possible de sélectionner de boisson
    """
    tpid = "TP/CF/DR/BV-16"
    n = 0
    drinks, price = None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get list of drinks", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]

    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtInsertCoin(0)
    h_coin = format(0, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({0}) (coin value = {g_coins[0]}", exp="UtSelectResult == SUCCESS", sent=h('24') + h_coin, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for drink in drinks:
        cur_idx = drink["index"]
        h_idx = format(cur_idx, '02x')
        res = comm.UtSelectDrink(cur_idx)
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {cur_idx}", exp="UtSelectResult.Success == ERROR", sent=h('21') + h_idx,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtValidateResult == SUCCESS"
                row.verdict = 'Fail'
            else:
                row.observed = "UtValidateResult == ERROR"
                row.verdict = 'Pass'
        g_history.append(row)


def tp17():
    """
    Lorsqu’une pièce est insérée, le prix restant à payer affiché est mis à jour
    """
    tpid = "TP/CF/DR/BV-17"
    n = 0
    drinks, price = None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get list of drinks", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            # pprint(drinks)
            row.verdict = "Pass"
            row.observed = drinks
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    drink = drinks[0]

    idx = drink["index"]
    h_idx = format(idx, '02x')

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = drink["price"]
    printed = None

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp="Print price of drink {} ({})".format(idx, price), sent=h('12'),
                  rcvd=str(res.hex()))
    res = res[2:]
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            printed = res.decode('utf-8')
            row.observed = printed
            row.verdict = "Pass"
            printed = float(printed.strip().replace('€', ''))

        except (Exception,):
            row.verdict = "Error"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    coin = 0
    res = comm.UtInsertCoin(coin)
    h_coin = format(coin, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({0}) (coin value = {g_coins[0]}", exp="UtSelectResult == SUCCESS", sent=h('24') + h_coin, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    remaining = printed - g_coins[coin]

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp=f"Print price of drink updated {idx} ({price} - {g_coins[coin]})", sent=h('12'),
                  rcvd=str(res.hex()))
    res = res[2:]
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            printed = res.decode('utf-8')
            row.observed = printed
            printed = float(printed.strip().replace('€', ''))
            if remaining == printed:
                row.verdict = "Pass"
            else:
                row.verdict = "Fail"
        except (Exception,):
            row.verdict = "Error"
    g_history.append(row)


def tp18(idx=0):
    """
    Lorsque la boisson est entièrement payée, il n’est plus possible d’insérer de pièces
    """
    tpid = "TP/CF/DR/BV-18"
    n = 0
    drink = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        row.verdict = "Pass"
        row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
        drink = row.observed
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", tpid=tpid, exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    coin = 0
    res = comm.UtInsertCoin(coin)
    h_coin = format(coin, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == ERROR (drink paid, insert again {g_coins[coin]})",
                  sent=h('24') + h_coin,
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)


def tp19(idx=0):
    """
    Lorsqu’une boisson est entièrement payée, le texte affiché invite à récupérer la boisson
    """
    tpid = "TP/CF/DR/BV-19"
    n = 0
    drink = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        row.verdict = "Pass"
        row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
        drink = row.observed
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp="Print " + g_pixit["drinkMadeText"], sent=h('12'))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.datahex_received = str(res.hex())
        row.observed = res
        res = res[2:]
        if res.decode() == g_pixit["drinkMadeText"]:
            row.observed = g_pixit["drinkMadeText"]
            row.verdict = 'Pass'
        else:
            row.verdict = 'Fail'
    g_history.append(row)


def tp20(idx=0):
    """
    Lorsque la boisson est entièrement payée, la boisson est disponible
    """
    tpid = "TP/CF/DR/BV-20"
    n = 0
    drink = None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        row.verdict = "Pass"
        row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
        drink = row.observed
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    n += 1
    res = comm.UtGetDrink()
    row = Row.Row(n=n, tpid=tpid, prim="UtGetDrink", exp="UtSelectResult.Success == SUCCESS", sent=h('25'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)


def tp21(idx=0):
    """
    Si trop de pièces ont été insérées pour payer la boisson, le rendu monnaie est disponible
    """
    tpid = "TP/CF/DR/BV-21"
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        row.verdict = "Pass"
        row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    coins = [1, 1, 4]
    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    n += 1
    res = comm.UtGetChange()
    row = Row.Row(n=n, tpid=tpid, prim="UtGetChange", exp="UtSelectResult.Success == SUCCESS", sent=h('26'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp22(idx=0):
    """
    Tant que la boisson n’est pas récupérée, il est impossible de sélectionner la boisson
    """
    tpid = "TP/CF/DR/BV-22"
    n = 0
    drinks, drink = None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        try:
            row.verdict = "Pass"
            row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
            drink = row.observed
            drinks = infos["drinks"]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = f"Cannot get drinks and drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    for drink in drinks:
        cur_idx = drink["index"]
        h_idx = format(cur_idx, '02x')
        res = comm.UtSelectDrink(cur_idx)
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {cur_idx}", exp=f"UtSelectResult({cur_idx}).Success == ERROR", sent=h('21') + h_idx,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtValidateResult == SUCCESS"
                row.verdict = 'Fail'
            else:
                row.observed = "UtValidateResult == ERROR"
                row.verdict = 'Pass'
        g_history.append(row)
        if row.verdict in g_fails:
            return


def tp23(idx=0):
    """
    Tant qu’il reste de la monnaie à récupérer, il est impossible de sélectionner la boisson
    """
    tpid = "TP/CF/DR/BV-23"
    n = 0
    drinks, drink = None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        try:
            row.verdict = "Pass"
            row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
            drinks = infos["drinks"]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = f"Cannot get drinks and drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    coins = [1, 1, 4]
    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    for drink in drinks:
        cur_idx = drink["index"]
        h_idx = format(cur_idx, '02x')
        res = comm.UtSelectDrink(cur_idx)
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {cur_idx}", exp=f"UtSelectResult({cur_idx}).Success == ERROR", sent=h('21') + h_idx,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtValidateResult == SUCCESS"
                row.verdict = 'Fail'
            else:
                row.observed = "UtValidateResult == ERROR"
                row.verdict = 'Pass'
        g_history.append(row)
        if row.verdict in g_fails:
            return


def tp24(idx=0):
    tpid = "TP/CF/DR/BV-24"
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        try:
            row.verdict = "Pass"
            row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
        except (Exception,):
            row.verdict = "Fail"
            row.observed = f"Cannot get drinks and drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    coins = [1, 1, 4]

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    res = comm.UtGetDrink()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetDrink", exp="UtSelectResult.Success == SUCCESS", sent=h('25'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtGetPrint()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetPrint", exp="Print " + g_pixit["changeText"], sent=h('12'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        row.observed = res.decode('utf-8')
        res = res[2:]
        if res.decode('utf-8') == g_pixit["changeText"]:
            row.verdict = 'Pass'
        else:
            row.verdict = 'Fail'
    g_history.append(row)


def tp25(idx=0):
    """
    Lorsqu’une boisson et le rendu monnaie sont récupérés, le nombre de gobelets est diminué d'un
    """
    tpid = "TP/CF/DR/BV-25"
    n = 0
    nb_buckets, drinks, drink = 0, None, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists + get nb_buckets", sent=h('10'),
                  rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        # pprint(infos)
        try:
            row.verdict = "Pass"
            drink = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
            nb_buckets = infos["buckets"]
            row.observed = str(drink) + f"\n{nb_buckets} buckets remaining"
        except (Exception,):
            row.verdict = "Fail"
            row.observed = f"Cannot get the remaining number of buckets and/or drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx = format(idx, '02x')
    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    res = comm.UtGetDrink()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetDrink", exp="UtSelectResult.Success == SUCCESS", sent=h('25'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp=f"new_nb_buckets = nb_buckets({nb_buckets}) - 1", sent=h('10'),
                  rcvd=str(infos.hex()))
    infos = get_infos(infos)

    try:
        row.observed = infos["buckets"]
        new_nb_buckets = infos["buckets"]
        if new_nb_buckets == (nb_buckets - 1):
            row.verdict = "Pass"
        else:
            row.verdict = "Fail"
    except (Exception,):
        row.verdict = "Fail"
        row.observed = f"Cannot get the remaining number of buckets and/or drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp26(idx=0, sugar=5):
    """
    Lorsqu’une boisson et le rendu monnaie sont récupérés, le nombre d’unités de sucre est diminué d’autant de sucre
    sélectionné
    """
    tpid = "TP/CF/DR/BV-26"
    h_idx, h_sugar = format(idx, '02x'), format(sugar, '02x')
    n, max_idx, nb_sugar, drink = 0, 255, 0, None

    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="The chosen drink can be sweetened + nb_sugar", sent=h('10'),
                  rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        max_idx = infos["nbdrinks"]
        row.requisites = f"0 <= idx <= {max_idx - 1}"

        if idx >= max_idx:
            row.verdict = "Error"
            row.observed = f"Index {idx} out of drink range"
        else:
            if infos == "Inconc".encode():
                row.verdict = "Inconc"
            else:
                try:
                    nb_sugar = infos["sugar"]
                    drink = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
                    row.observed = str(drink)
                    can_be_sugared = drink["sweet"]
                    if can_be_sugared:
                        row.verdict = "Pass"
                        row.observed += " can be sweetened" + f"\nnb_sugar: {nb_sugar}"
                    else:
                        row.verdict = "Fail"
                        row.observed += " cannot be sweetened"

                except (Exception,):
                    row.verdict = "Fail"
                    row.observed = res
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtSetSugar(sugar)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetSugar({sugar})", exp="UtSelectResult.Success == SUCCESS", sent=h('22') + h_sugar, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    res = comm.UtGetDrink()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetDrink", exp="UtSelectResult.Success == SUCCESS", sent=h('25'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp=f"new_nb_sugar = nb_sugar({nb_sugar}) - {sugar}", sent=h('10'),
                  rcvd=str(infos.hex()))
    infos = get_infos(infos)

    try:
        row.observed = f"new_nb_sugar: {infos['sugar']}"
        new_nb_sugar = infos["sugar"]
        if new_nb_sugar == (nb_sugar - sugar):
            row.verdict = "Pass"
        else:
            row.verdict = "Fail"
    except (Exception,):
        row.verdict = "Fail"
        row.observed = f"Cannot get the remaining number of buckets and/or drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp27(idx=8):
    """
    Lorsqu’une boisson et le rendu monnaie sont récupérés, le nombre d’unités de sucre
    n’est pas diminué si la boisson ne peut pas avoir de sucre
    """
    tpid = "TP/CF/DR/BV-26"
    h_idx, drink = format(idx, '02x'), None
    n, max_idx, nb_sugar = 0, 255, 0

    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="The chosen drink can be sweetened + nb_sugar", sent=h('10'),
                  rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        max_idx = infos["nbdrinks"]
        row.requisites = f"0 <= idx <= {max_idx - 1}"

        if idx >= max_idx:
            row.verdict = "Error"
            row.observed = f"Index {idx} out of drink range"
        else:
            if infos == "Inconc".encode():
                row.verdict = "Inconc"
            else:
                try:
                    nb_sugar = infos["sugar"]
                    drink = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
                    row.observed = str(drink)
                    can_be_sugared = drink["sweet"]
                    if can_be_sugared:
                        row.verdict = "Fail"
                        row.observed += " can be sweetened"
                    else:
                        row.verdict = "Pass"
                        row.observed += " cannot be sweetened" + f"\nnb_sugar: {nb_sugar}"

                except (Exception,):
                    row.verdict = "Fail"
                    row.observed = res
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp="UtSelectResult.Success == SUCCESS", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    price = float(drink["price"].strip().replace('€', ''))
    coins = pay_exact(price)

    res = comm.UtValidate()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtValidate", exp="UtValidateResult == SUCCESS", sent=h('23'), rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtValidateResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtValidateResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for coin in coins:
        res = comm.UtInsertCoin(coin)
        h_coin = format(coin, '02x')
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtInsertCoin({coin}) (coin value = {g_coins[coin]}", exp=f"UtSelectResult == SUCCESS (insert {g_coins[coin]})", sent=h('24') + h_coin,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtSelectResult == SUCCESS"
                row.verdict = 'Pass'
            else:
                row.observed = "UtSelectResult == ERROR"
                row.verdict = 'Fail'
        g_history.append(row)
        if row.verdict in g_fails:
            return

    res = comm.UtGetDrink()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetDrink", exp="UtSelectResult.Success == SUCCESS", sent=h('25'),
                  rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp=f"new_nb_sugar = nb_sugar({nb_sugar})", sent=h('10'),
                  rcvd=str(infos.hex()))
    infos = get_infos(infos)

    try:
        row.observed = f"new_nb_sugar: {infos['sugar']}"
        new_nb_sugar = infos["sugar"]
        if new_nb_sugar == nb_sugar:
            row.verdict = "Pass"
        else:
            row.verdict = "Fail"
    except (Exception,):
        row.verdict = "Fail"
        row.observed = f"Cannot get the remaining number of sugar and/or drink idx {idx}"
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp28():
    """
    Lorsqu’une boisson est manquante, on ne peut pas la sélectionner
    """
    tpid = "TP/CF/DR/BV-28"
    n, idx = 0, 0
    h_idx = format(idx, '02x')

    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetNbDrinks(idx, 0)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetNbDrinks({idx}, {0})", exp="UtResult.Success == SUCCESS", sent=h('04')+h_idx, rcvd=str(res.hex()))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp=f"UtSelectResult({idx}).Success == ERROR", sent=h('21') + h_idx)
    row.datahex_received = str(res.hex())
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp29():
    """
    Lorsqu’il n’y a plus de gobelet, on ne peut pas sélectionner de boisson
    """
    tpid = "TP/CF/DR/BV-29"
    n, drinks = 0, None
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetNbBuckets(0)
    # print(res)
    h_buckets = format(0, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetNbBuckets({0})", exp="UtResult.Success == SUCCESS", sent=h('03') + h_buckets)
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Get list of drinks", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    # pprint(infos)
    if infos == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        try:
            drinks = infos["drinks"]
            row.verdict = "Pass"
            row.observed = drinks
        except (Exception,):
            row.verdict = "Fail"
            row.observed = "Drinks list empty"
    g_history.append(row)
    if row.verdict in g_fails:
        return

    for drink in drinks:
        cur_idx = drink["index"]
        h_idx = format(cur_idx, '02x')
        res = comm.UtSelectDrink(cur_idx)
        n += 1
        row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {cur_idx}", exp=f"UtSelectResult({cur_idx}).Success == ERROR", sent=h('21') + h_idx,
                      rcvd=str(res.hex()))
        if res == "Inconc".encode():
            row.verdict = "Inconc"
        else:
            if res[1] == 1:
                row.observed = "UtValidateResult == SUCCESS"
                row.verdict = 'Fail'
            else:
                row.observed = "UtValidateResult == ERROR"
                row.verdict = 'Pass'
        g_history.append(row)
        if row.verdict in g_fails:
            return


def tp30():
    """
    On ne peut pas sélectionner plus de sucre que le nombre d’unités de sucre restant
    """
    tpid = "TP/CF/DR/BV-30"
    n, idx, sugar = 0, 0, 5
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetNbSugar(sugar)
    h_sugar = format(sugar, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetNbSugar({sugar})", exp="UtResult.Success == SUCCESS", sent=h('02') + h_sugar)
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSelectDrink(idx)
    h_idx = format(idx, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSelectDrink at index {idx}", exp=f"Select drink {idx}", sent=h('21') + h_idx, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetSugar(sugar + 1)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetSugar({sugar})", exp="UtSelectResult.Success == ERROR", sent=h('22') + h_sugar, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Fail'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Pass'
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetSugar(sugar)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetSugar({sugar})", exp="UtSelectResult.Success == SUCCESS", sent=h('22') + h_sugar, rcvd=str(res.hex()))
    if res == "Inconc".encode():
        row.verdict = "Inconc"
    else:
        if res[1] == 1:
            row.observed = "UtSelectResult.Success == SUCCESS"
            row.verdict = 'Pass'
        else:
            row.observed = "UtSelectResult.Success == ERROR"
            row.verdict = 'Fail'
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp31(idx=0, amount=100):
    """
    Il est possible pour une boisson donnée de sélectionner le nombre restant
    """
    tpid = "TP/CF/DR/BV-31"
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    infos = comm.UtGetInfos()
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim="UtGetInfos", exp="Drink at chosen index exists", sent=h('10'), rcvd=str(infos.hex()))
    infos = get_infos(infos)
    max_idx = infos["nbdrinks"]
    row.requisites = f"0 <= idx <= {max_idx - 1}"

    if idx >= max_idx:
        row.verdict = "Error"
        row.observed = f"Index {idx} out of drink range"
    else:
        row.verdict = "Pass"
        row.observed = [drink for drink in infos["drinks"] if drink["index"] == idx][0]
    g_history.append(row)
    if row.verdict in g_fails:
        return

    h_idx, h_amount = format(idx, "02x"), format(amount, "02x")
    res = comm.UtSetNbDrinks(idx, amount)
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetNbDrinks({idx}, {amount})", exp="UtResult.Success == SUCCESS", sent=h('04') + h_idx + h_amount,
                  rcvd=str(res.hex()))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp32(sugar=200):
    """
    Il est possible pour une boisson donnée de sélectionner le nombre restant
    """
    tpid = "TP/CF/DR/BV-32"
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetNbSugar(sugar)
    h_sugar = format(sugar, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetNbSugar({sugar})", exp="UtResult.Success == SUCCESS", sent=h('02') + h_sugar)
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return


def tp33(bucket=100):
    """
    Il est possible pour une boisson donnée de sélectionner le nombre restant
    """
    tpid = "TP/CF/DR/BV-33"
    n = 0
    res = comm.UtInitialize()
    row = Row.Row(n=n, tpid=tpid, prim="UtInitialize", exp="UtResult.Success == SUCCESS", sent=h('00'), rcvd=str(res.hex()))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return

    res = comm.UtSetNbBuckets(bucket)
    # print(res)
    h_buckets = format(bucket, '02x')
    n += 1
    row = Row.Row(n=n, tpid=tpid, prim=f"UtSetNbBuckets({bucket})", exp="UtResult.Success == SUCCESS", sent=h('03') + h_buckets, rcvd=str(res.hex()))
    test_ut_result(res, row)
    g_history.append(row)
    if row.verdict in g_fails:
        return


@app.route("/", methods=['GET', 'POST'])
def index():
    global g_result, g_headers, g_history
    if request.method == 'POST':
        if request.form.get('testhex') == 'testhex':
            hexa = request.form.get('hex')
            if not hexa:
                hexa = '00'
            try:
                bytes.fromhex(hexa)
            except (Exception,):
                hexa = '00'
            g_result = comm.send_and_recv(hexa)
            row = Row.Row(tpid="Hexa Test", exp="Test", obs=g_result, ver="Test", req="Test", sent=h(hexa),
                          rcvd=g_result.hex())
            g_history.append(row)

        if request.form.get('generate') == 'generate csv':
            with open("report.csv", "w") as f_csv:
                writer = csv.DictWriter(f_csv, fieldnames=g_headers)
                writer.writeheader()
                for line in g_history:
                    writer.writerow(line.__dict__)

        if request.form.get('clean') == 'clean':
            g_history = []
            
        if request.form.get('action') == 'TP01':
            tp1()
        elif request.form.get('action') == 'TP02':
            tp2()
        elif request.form.get('action') == 'TP03':
            idx = int(request.form.get('p1tp3'))
            tp3(idx)
        elif request.form.get('action') == 'TP04':
            f_idx = int(request.form.get('p1tp4'))
            s_idx = int(request.form.get('p2tp4'))
            tp4(f_idx, s_idx)
        elif request.form.get('action') == 'TP05':
            idx = int(request.form.get('p1tp5'))
            sugar = int(request.form.get('p2tp5'))
            tp5(idx, sugar)
        elif request.form.get('action') == 'TP06':
            idx = int(request.form.get('p1tp6'))
            sugar = int(request.form.get('p2tp6'))
            tp6(idx, sugar)
        elif request.form.get('action') == 'TP07':
            sugar = int(request.form.get('p1tp7'))
            tp7(sugar)
        elif request.form.get('action') == 'TP08':
            sugar = int(request.form.get('p1tp8'))
            tp8(sugar)
        elif request.form.get('action') == 'TP09':
            tp9()
        elif request.form.get('action') == 'TP10':
            tp10()
        elif request.form.get('action') == 'TP11':
            tp11()
        elif request.form.get('action') == 'TP12':
            tp12()
        elif request.form.get('action') == 'TP13':
            tp13()
        elif request.form.get('action') == 'TP14':
            tp14()
        elif request.form.get('action') == 'TP15':
            tp15()
        elif request.form.get('action') == 'TP16':
            tp16()
        elif request.form.get('action') == 'TP17':
            tp17()
        elif request.form.get('action') == 'TP18':
            idx = int(request.form.get('p1tp18'))
            tp18(idx)
        elif request.form.get('action') == 'TP19':
            idx = int(request.form.get('p1tp19'))
            tp19(idx)
        elif request.form.get('action') == 'TP20':
            idx = int(request.form.get('p1tp20'))
            tp20(idx)
        elif request.form.get('action') == 'TP21':
            idx = int(request.form.get('p1tp21'))
            tp21(idx)
        elif request.form.get('action') == 'TP22':
            idx = int(request.form.get('p1tp22'))
            tp22(idx)
        elif request.form.get('action') == 'TP23':
            idx = int(request.form.get('p1tp23'))
            tp23(idx)
        elif request.form.get('action') == 'TP24':
            idx = int(request.form.get('p1tp24'))
            tp24(idx)
        elif request.form.get('action') == 'TP25':
            idx = int(request.form.get('p1tp25'))
            tp25(idx)
        elif request.form.get('action') == 'TP26':
            idx = int(request.form.get('p1tp26'))
            sugar = int(request.form.get('p2tp26'))
            tp26(idx, sugar)
        elif request.form.get('action') == 'TP27':
            idx = int(request.form.get('p1tp27'))
            tp27(idx)
        elif request.form.get('action') == 'TP28':
            tp28()
        elif request.form.get('action') == 'TP29':
            tp29()
        elif request.form.get('action') == 'TP30':
            tp30()
        elif request.form.get('action') == 'TP31':
            idx = int(request.form.get('p1tp31'))
            amount = int(request.form.get('p2tp31'))
            tp31(idx, amount)
        elif request.form.get('action') == 'TP32':
            sugar = int(request.form.get('p1tp32'))
            tp32(sugar)
        elif request.form.get('action') == 'TP33':
            bucket = int(request.form.get('p1tp33'))
            tp33(bucket)
        else:
            pass  # unknown
    elif request.method == 'GET':
        return render_template('index.html', history=g_history, result=g_result)
    
    return render_template("index.html", history=g_history, result=g_result)


if __name__ == '__main__':
    parser = ap.ArgumentParser()
    parser.add_argument("--host", help="IP Address (ipv4/6)", type=str, default='127.0.0.1')
    parser.add_argument("--port", help="port to use", type=int, default=4200)
    parser.add_argument("--timeout", help="socket timeout in seconds", type=float, default=5.0)
    args = parser.parse_args()
    comm.host = args.host
    comm.port = args.port
    comm.timeout = args.timeout
    app.run()
