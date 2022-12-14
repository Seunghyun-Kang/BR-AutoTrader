class StockDetail:
    def __init__(self, name, code, quantity, price, profit, profit_rate, even_price):
        self.__name = name
        self.__code = code
        self.__quantity = quantity
        self.__price = price
        self.__profit = profit
        self.__profit_rate = profit_rate
        self.__even_price = even_price

    @property
    def name(self):
        return self.__name
    @property
    def code(self):
        return self.__code
    @property
    def quantity(self):
        return self.__quantity
    @property
    def price(self):
        return self.__price
    @property
    def profit(self):
        return self.__profit
    @property
    def profit_rate(self):
        return self.__profit_rate
    @property
    def even_price(self):
        return self.__even_price
