from datetime import datetime
import pandas as pd
import uuid
import ccxt
import config
import screener
import tools
import merge
import concurrent.futures

class MyExchanger:

    def __init__(self, exchange, cash, filter_buy, intervals):
        self.start_time = datetime.now()
        self.trade_time = datetime.now()
        self.exchanger_name = exchange
        self.exchange = screener.get_exchange()
        self.markets = self.exchange.load_markets()
        self.filter = filter_buy
        self.intervals = intervals

        self.position = False
        self.cash = cash
        self.portfolio_value = 0
        self.positive_trades = 0
        self.negative_trades = 0
        self.open_trades = 0
        self.nb_trades = 0
        self.nb_records = 0

        self.commission = self.markets[config.INIT_SYMBOL]['taker']
        self.df_trades = pd.DataFrame(columns=config.COLUMNS_TRADES)
        self.df_position_records = pd.DataFrame(columns=config.COLUMNS_POSITION_RECORDS)

        self.df_trades_records = pd.DataFrame(columns=config.COLUMNS_TRADES_RECORDS)
        self.lst_crypto_to_buy = []
        self.df_crypto_to_buy = pd.DataFrame(columns=config.COLUMNS_BUY_SELL)
        self.lst_crypto_to_sell = []
        self.df_crypto_to_sell = pd.DataFrame(columns=config.COLUMNS_BUY_SELL)
        self.lst_crypto_in_portfolio = []
        self.multithreading = True
        self.multithreading_nb_split = 20

    def next_step(self):
        if self.position == False:
            self.update_lst_crypto_for_buying()
            self.rank_list_of_crypto_to_buy()
            self.buy_list_of_pairs()
        else:
            self.update_my_positions()
            self.sell_list_of_pairs()
            self.update_lst_crypto_for_buying()
            self.rank_list_of_crypto_to_buy()
            self.buy_list_of_pairs()

    def buy_list_of_pairs(self):
        self.trade_time = datetime.now()
        for symbol in self.lst_crypto_to_buy:
            list_raw_trade = []

            list_raw_trade.append(self.nb_trades)                   # id
            self.nb_trades = self.nb_trades+1
            list_raw_trade.append(self.trade_time)                  # time
            list_raw_trade.append(symbol)                           # pair

            price = self.get_crypto_price(symbol)
            list_raw_trade.append(price)                            # init price

            trade_size = self.get_crypto_trade_size(price)
            list_raw_trade.append(trade_size)                       # trade size

            net_price = round(price * trade_size, 4)
            list_raw_trade.append(net_price)                        # net price

            commission = self.get_crypto_commission(net_price)
            list_raw_trade.append(commission)                       # commission

            gross_price = round((net_price + commission), 4)
            list_raw_trade.append(gross_price)                      # gross price

            list_raw_trade.append(price)                            # current unit value
            list_raw_trade.append(round(price*trade_size, 4))       # current trade value

            list_raw_trade.append(-commission)                      # profit loss

            if(price != 0):
                self.authorize_transaction(gross_price, list_raw_trade)

        self.update_position_record()

    def buy_pair(self):
        return

    def sell_list_of_pairs(self):
        self.trade_time = datetime.now()
        for symbol in self.lst_crypto_to_buy:
            list_raw_trade = []

    def sell_pair(self):
        return

    def get_trade_size(self):
        return

    def update_my_positions(self):
        self.update_get_profit_stop_lost()
        self.update_low_ranking()

    def update_get_profit_stop_lost(self):
        self.exchange = screener.get_exchange()
        self.markets = self.exchange.load_markets()

        list_ids = self.df_trades['id'].to_list()
        self.df_trades = self.df_trades.set_index('id', drop=False)
        for id in list_ids:
            symbol = self.df_trades.loc[id, 'pair']
            gross_price = self.df_trades['gross_price'][id]
            init_price = self.df_trades['init_price'][id]
            trade_size = self.df_trades['trade_size'][id]
            actual_price = self.get_crypto_price(symbol)
            new_value = trade_size * actual_price
            roi = new_value - gross_price
            if roi >= 0:
                if roi / gross_price * 100 >= config.GET_PROFIT:
                    self.lst_crypto_to_sell.append(symbol)
            else:
                if roi / gross_price * 100 <= config.STOP_LOSS:
                    self.lst_crypto_to_sell.append(symbol)

    def update_low_ranking(self):
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

    def rank_list_of_crypto_to_buy(self):
        self.df_crypto_to_buy['pair'] = self.lst_crypto_to_buy
        self.df_crypto_to_buy = self.df_crypto_to_buy.set_index('pair', drop=False)

        for crypto in self.lst_crypto_to_buy:
            self.df_crypto_to_buy['buy'][crypto], self.df_crypto_to_buy['sell'][crypto], self.df_crypto_to_buy['neutral'][crypto] = screener.get_crypto_score(crypto, self.exchanger_name, self.intervals)
            self.df_crypto_to_buy['24h'][crypto], self.df_crypto_to_buy['1h'][crypto] = screener.get_actual_trend(crypto, self.markets)
        # Compute a score based on TDView and 24h and 1h trends
        self.df_crypto_to_buy['score'] = self.df_crypto_to_buy['buy'] + self.df_crypto_to_buy['24h'] + self.df_crypto_to_buy['1h'] - 2 * self.df_crypto_to_buy['sell'] - self.df_crypto_to_buy['neutral']
        self.df_crypto_to_buy.sort_values(by=['score'], ascending=True, inplace=True)
        self.df_crypto_to_buy.reset_index(inplace=True, drop=True)
        self.df_crypto_to_buy['ranking'] = self.df_crypto_to_buy.index.tolist()
        self.df_crypto_to_buy.sort_values(by=['ranking'], ascending=False, inplace=True)
        self.df_crypto_to_buy.reset_index(inplace=True, drop=True)

        # Get rid of lower score
        self.df_crypto_to_buy.drop(self.df_crypto_to_buy[self.df_crypto_to_buy.score <= config.BUYING_SCORE_THRESHOLD].index, inplace=True)

        self.lst_crypto_to_buy = self.df_crypto_to_buy['pair'].tolist()

    def get_crypto_price(self, symbol):
        return round(float(self.markets[symbol]['info']['price']), 4)

    def get_crypto_commission(self, price):
        return round(price * self.commission, 4)

    def get_crypto_trade_size(self, price):
        try:
            if(price > config.TRADE_SIZE):
                return round(config.TRADE_SIZE * 2 / price, 1)
            else:
                return round(config.TRADE_SIZE / price, 1)
        except:
            return 0

    def add_buy_transaction(self, list):
        self.df_trades.loc[len(self.df_trades)] = list

    def add_records_transaction(self, list):
        self.df_position_records.loc[len(self.df_position_records)] = list

    def authorize_transaction(self, transation_gross, list):
        if self.cash >= transation_gross:
            self.position = True
            self.cash = self.cash - transation_gross
            self.add_buy_transaction(list)
            self.open_trades = self.open_trades + 1
            return True
        else:
            self.nb_trades = self.nb_trades - 1
            return False

    def update_position_record(self):
        id = self.nb_records
        self.nb_records = self.nb_records + 1
        time = self.trade_time
        cash = self.cash
        positive_trades = self.positive_trades
        negative_trades = self.negative_trades
        open_trades = self.open_trades
        total_nb_trades = self.nb_trades
        portfolio_value = self.df_trades['current_trade_val'].sum()
        list = [id, time, cash, positive_trades, negative_trades, open_trades, total_nb_trades, portfolio_value]
        self.add_records_transaction(list)

        print(list)






