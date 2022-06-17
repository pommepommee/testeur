price = 18
d_coins = {0: 0.1, 1: 0.2, 2: 0.5, 3: 1.0, 4: 2.0}


# to_pay = []
# i = 4
# while price > 0:
#     if price >= coins[i]:
#         to_pay.append(i)
#         price -= coins[i]
#         price = round(price, 2)
#     else:
#         i -= 1
#
# print(to_pay)


coins = [0, 1, 2, 4, 5]
paid = round(sum(d_coins[coin] for coin in coins), 1)
print(paid)
