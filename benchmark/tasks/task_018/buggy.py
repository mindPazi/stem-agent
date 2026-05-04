def max_profit(prices):
    if not prices:
        return 0
    max_price = prices[0]
    profit = 0
    for price in prices[1:]:
        profit = max(profit, price - max_price)
        max_price = max(max_price, price)
    return profit
