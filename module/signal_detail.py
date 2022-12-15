class SignalDetail:
    def __init__(self, code, signal_date, signal_type, signal_price, signal_count):
        self.__code = code
        self.__signal_date = signal_date
        self.__signal_type = signal_type
        self.__signal_price = signal_price
        self.__signal_count = signal_count

    @property
    def code(self):
        return self.__code

    @property
    def signal_date(self):
        return self.__signal_date

    @property
    def signal_type(self):
        return self.__signal_type

    @property
    def signal_price(self):
        return self.__signal_price

    @property
    def signal_count(self):
        return self.__signal_count

        