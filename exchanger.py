from datetime import datetime
import pandas as pd
import uuid
import config
import screener
import tools
import merge
import concurrent.futures

class MyExchanger:

    def __init__(self, exchange, cash, filter_buy, intervals):
        self.start_time = datetime.now()
        self.exchanger_name = exchange
        self.exchange = screener.get_exchange()
        self.markets = self.exchange.load_markets()
        self.filter = filter_buy
        self.intervals = intervals
        self.position = False
        self.cash = cash
        self.cash_empty = False
        self.portfolio_value = 0
        self.portfolio_size = 0
        self.portfolio_full = False
        self.nb_trades = 0
        self.commissions = 0
        self.df_trades = pd.DataFrame(columns=config.COLUMNS_TRADES)
        self.df_trades_records = pd.DataFrame(columns=config.COLUMNS_RECORDS)
        self.lst_crypto_to_buy = []
        self.lst_crypto_to_sell = []
        self.lst_crypto_in_portfolio = []
        self.multithreading = True
        self.multithreading_nb_split = 10

    def next_step(self):
        if self.position == False:
            self.update_lst_crypto_for_buying()
            self.buy_list_of_pairs()
        else:
            self.sell_listof_pairs()
            self.update_lst_crypto_for_buying()
            self.buy_list_of_pairs()

    def buy_list_of_pairs(self):
        return

    def buy_pair(self):
        return

    def sell_listof_pairs(self):
        return

    def sell_pair(self):
        return

    def sizer(self):
        return

    def get_tradingview_recommendation_list_multi(self, list_crypto_symbols):
        list_tradingview = screener.get_tradingview_recommendation_list(list_crypto_symbols, self.filter)
        df = pd.DataFrame(list_tradingview, columns=['symbol'])
        filename = config.MULTITHREADING_POOL + str(uuid.uuid4()) + '_result.csv'
        df.to_csv(filename)

    def update_lst_crypto_for_buying(self):
        start_time = datetime.now()

        symbols = self.exchange.symbols

        print("list symbols available: ", len(symbols))
        symbols_total_size = len(symbols)

        symbols = list(filter(screener.custom_filter, symbols))
        print("symbol filtered: ", symbols_total_size - len(symbols))

        list_crypto_symbols = screener.filter_symbol_by_volume(symbols, self.markets)

        print("low volume symbol dropped: ", len(symbols) - len(list_crypto_symbols))
        print("symbol remaining: ", len(list_crypto_symbols))

        list_price = screener.get_market_price_changes(list_crypto_symbols, self.markets)

        if self.multithreading:
            global_split_list = tools.split_list_into_list(list_crypto_symbols, self.multithreading_nb_split)

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(global_split_list)) as executor:
                executor.map(self.get_tradingview_recommendation_list_multi, global_split_list)

            df_tradingview = merge.merge_csv_to_df(config.MULTITHREADING_POOL, "*_result.csv")
            list_tradingview = df_tradingview['symbol'].tolist()
        else:
            list_tradingview = screener.get_tradingview_recommendation_list(list_crypto_symbols, self.filter)

        list_reinforced = screener.get_price_and_tradingview_common(list_price, list_tradingview)
        print("common symbol: ", len(list_reinforced))
        print(list_reinforced)

        end_time = datetime.now()
        duration_time = end_time - start_time
        print('duration: ', duration_time)

        self.lst_crypto_to_buy = list_reinforced


