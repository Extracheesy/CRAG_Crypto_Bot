from datetime import datetime
import pandas as pd
import uuid
import ccxt
import time
import config
import screener
import tools
import merge
import concurrent.futures

class MyExchanger:

    def __init__(self, exchange, cash, filter_buy, intervals):
        print('Strategy based on:', filter_buy)
        self.start_time = datetime.now()
        self.trade_time = datetime.now()

        self.exchanger_name = exchange
        self.exchange = screener.get_exchange()
        self.markets = self.exchange.load_markets()
        self.filter = filter_buy
        self.intervals = intervals

        self.cash = cash
        self.init_cash = cash
        self.position = False
        self.portfolio_value = 0
        self.positive_trades = 0
        self.negative_trades = 0
        self.open_trades = 0
        self.nb_trades = 0
        self.nb_records = 0

        self.commission = self.markets[config.INIT_SYMBOL]['taker']
        self.df_trades = pd.DataFrame(columns=config.COLUMNS_TRADES)

        self.df_position_records = pd.DataFrame(columns=config.COLUMNS_POSITION_RECORDS)
        self.df_trade_records = pd.DataFrame(columns=config.COLUMNS_TRADES_RECORDS)

        self.lst_crypto_to_buy = []
        self.df_crypto_to_buy = pd.DataFrame(columns=config.COLUMNS_BUY_SELL)
        self.buy_queued = False

        self.lst_crypto_to_sell = []
        self.sell_queued = False

        self.multithreading = False
        self.multithreading_nb_split = 20
        self.fdp = True

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
            id = self.nb_trades
            self.nb_trades = self.nb_trades+1
            time = self.trade_time
            price = self.get_crypto_price(symbol)
            trade_size = self.get_crypto_trade_size(price)
            net_price = round(price * trade_size, 4)
            commission = self.get_crypto_commission(net_price)
            gross_price = round((net_price + commission), 4)
            current_price = price
            current_trade_value = round(price*trade_size, 4)
            profit_loss = -commission
            list_raw_trade = [id, time, symbol, price, trade_size, net_price, commission, gross_price, current_price,
                              current_trade_value, profit_loss]
            if(price != 0):
                self.authorize_transaction(gross_price, list_raw_trade)

        self.update_position_record()
        self.clear_buy()

    def clear_buy(self):
        self.df_crypto_to_buy = pd.DataFrame(columns=config.COLUMNS_BUY_SELL)
        self.lst_crypto_to_buy = []
        self.buy_queued = False

    def clear_sell(self):
        self.lst_crypto_to_sell = []
        self.buy_queued = False

    def sell_list_of_pairs(self):
        if self.sell_queued:
            self.trade_time = datetime.now()
            list_ids = self.df_trades['id'].to_list()
            self.df_trades = self.df_trades.set_index('id', drop=False)
            for id in list_ids:
                try:
                    symbol = self.df_trades.loc[id, 'pair']
                except:
                    # print('id: ', id)
                    # self.df_trades.to_csv('DEBUG.csv')
                    symbol = self.df_trades.loc['pair'][id]

                if symbol in self.lst_crypto_to_sell:
                    # print('selling id: ', id)
                    # print('selling symbol: ', symbol)
                    self.update_position_sell_record(id, symbol)

            self.df_trades.reset_index(inplace=True, drop=True)
            self.clear_sell()

    def remove_trade_after_sell(self, id):
        self.df_trades.drop([id], axis=0, inplace=True)

    def update_my_positions(self):
        self.update_sell_list()

    def update_sell_list(self):
        # build sell list from positions / trades
        list_ids = self.df_trades['id'].to_list()
        self.df_trades = self.df_trades.set_index('id', drop=False)
        for id in list_ids:
            symbol = self.df_trades.loc[id, 'pair']
            gross_price = self.df_trades['gross_price'][id]
            init_price = self.df_trades['init_price'][id]
            trade_size = self.df_trades['trade_size'][id]
            actual_price = self.get_crypto_price(symbol)
            new_value = trade_size * actual_price
            roi = float(new_value - gross_price)
            if(gross_price != 0):
                if roi >= 0:
                    if float(roi) / float(gross_price) * float(100) >= float(config.GET_PROFIT):
                        self.lst_crypto_to_sell.append(symbol)
                else:
                    if float(roi) / float(gross_price) * float(100) <= float(config.STOP_LOSS):
                        self.lst_crypto_to_sell.append(symbol)
            else:
                print('ERROR GROSS_PRICE == 0!!!',symbol, gross_price)

            score = self.update_low_ranking(symbol)
            if score < 0:
                self.lst_crypto_to_sell.append(symbol)
        if(len(self.lst_crypto_to_sell) == 0):
            self.clear_sell()
        else:
            self.sell_queued = True
            self.lst_crypto_to_sell = list(set(self.lst_crypto_to_sell))

        self.df_trades.reset_index(inplace=True, drop=True)


    def update_low_ranking(self, symbol):
        score = screener.get_tradingview_recommendation_score(symbol, self.intervals)
        return score

    def get_tradingview_recommendation_list_multi(self, list_crypto_symbols):
        list_tradingview = screener.get_tradingview_recommendation_list(list_crypto_symbols, self.filter)
        df = pd.DataFrame(list_tradingview, columns=['symbol'])
        filename = config.MULTITHREADING_POOL + str(uuid.uuid4()) + '_result.csv'
        df.to_csv(filename)

    def update_lst_crypto_for_buying(self):
        if self.fdp:
            df_crypto_symbols = screener.get_df_selected_data_from_fdp()
            df_crypto_symbols = screener.filter_df_level(df_crypto_symbols, self.filter, config.RECOMMENDATION_ALL.copy())
            list_reinforced = df_crypto_symbols['symbol'].to_list()
        else:
            symbols = self.exchange.symbols
            symbols = list(filter(screener.custom_filter, symbols))
            list_crypto_symbols = screener.filter_symbol_by_volume(symbols, self.markets)
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

        self.lst_crypto_to_buy = list_reinforced
        if len(self.lst_crypto_to_buy) > 0:
            self.buy_queued = True
        else:
            self.buy_queued = False

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
        # Select the best pairs based on score and BUYING_SCORE_THRESHOLD
        self.df_crypto_to_buy.drop(self.df_crypto_to_buy[self.df_crypto_to_buy.score <= config.BUYING_SCORE_THRESHOLD].index, inplace=True)

        self.lst_crypto_to_buy = self.df_crypto_to_buy['pair'].tolist()

    def get_crypto_price(self, symbol):
        try:
            time.sleep(self.exchange.rateLimit / 1000)
            self.exchange = screener.get_exchange()
            self.markets = self.exchange.load_markets()
        except:
            SUCCESS = False
            while SUCCESS == False:
                time.sleep(5)
                print("CCXT TIMEOUT")
                try:
                    self.exchange = screener.get_exchange()
                    self.markets = self.exchange.load_markets()
                    SUCCESS = True
                except:
                    SUCCESS = False

        return round(float(self.markets[symbol]['info']['price']), 4)

    def get_crypto_commission(self, price):
        return round(price * self.commission, 4)

    def get_crypto_trade_size(self, price):
        try:
            if(price > config.TRADE_SIZE):
                return round(config.TRADE_SIZE / price, 5)
            else:
                return round(config.TRADE_SIZE / price, 4)
        except:
            return 0

    def add_buy_transaction(self, list):
        self.df_trades.loc[len(self.df_trades)] = list

    def add_records_transaction(self, list):
        self.df_position_records.loc[len(self.df_position_records)] = list

    def add_records_trade(self, list):
        self.df_trade_records.loc[len(self.df_trade_records)] = list

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
        self.update_position_current_price()

        id = self.nb_records
        transaction = "BUY"
        self.nb_records = self.nb_records + 1
        time = self.trade_time
        cash = self.cash
        positive_trades = self.positive_trades
        negative_trades = self.negative_trades
        open_trades = self.open_trades
        total_nb_trades = self.nb_trades
        portfolio_value = self.df_trades['current_trade_val'].sum()
        global_value = portfolio_value + cash
        roi = global_value * 100 / self.init_cash
        list = [id, time, transaction, round(cash,1), positive_trades, negative_trades, open_trades, total_nb_trades,
                round(portfolio_value,1), round(global_value,1), round(roi - 100.0, 4)]
        self.add_records_transaction(list)
        self.dump_logs()
        print("BUY STATUS: ", list)

    def update_position_sell_record(self, id_trade, symbol):
        self.update_position_current_price()

        id = self.nb_records
        self.nb_records = self.nb_records + 1
        time = self.trade_time
        transaction = "SELL"
        actual_price = self.get_crypto_price(symbol)
        sell_price = actual_price * self.df_trades['trade_size'][id_trade]
        self.cash = self.cash + sell_price
        cash = self.cash
        initial_gross = self.df_trades['gross_price'][id_trade]
        if (sell_price > initial_gross):
            self.positive_trades = self.positive_trades + 1
        else:
            self.negative_trades = self.negative_trades + 1
        positive_trades = self.positive_trades
        negative_trades = self.negative_trades
        self.open_trades = self.open_trades - 1
        open_trades = self.open_trades
        total_nb_trades = self.nb_trades
        self.remove_trade_after_sell(id_trade)
        portfolio_value = self.df_trades['current_trade_val'].sum()
        global_value = portfolio_value + cash
        roi = global_value * 100 / self.init_cash
        list = [id, time, transaction, round(cash,1), positive_trades, negative_trades, open_trades, total_nb_trades,
                round(portfolio_value,1), round(global_value,1), round(roi - 100.0, 4)]
        self.add_records_transaction(list)
        self.dump_logs()
        print("SELL STATUS: ", list)

    def update_position_current_price(self):
        add_new_row = True
        for i in self.df_trades.index.tolist():
            self.df_trades['current_u_value'][i] = self.get_crypto_price(self.df_trades['pair'][i])
            self.df_trades['current_trade_val'][i] = self.df_trades['current_u_value'][i] * self.df_trades['trade_size'][i]

            if add_new_row:
                new_row_data = [self.nb_records, self.trade_time]
                nb_columns = len(self.df_trade_records.columns)

                if len(self.df_trade_records.columns) == 2:
                    row_empty_data = []
                else:
                    row_empty_data = [''] * (nb_columns - 2)
                new_row_data = new_row_data + row_empty_data
                self.add_records_trade(new_row_data)
                add_new_row = False

            symbol = self.df_trades['pair'][i]
            if symbol in self.df_trade_records.columns:
                if config.LOG_PRICE_RAW == True:
                    self.df_trade_records.loc[(len(self.df_trade_records)-1), symbol] = round(self.df_trades['current_trade_val'][i], 4)
                else:
                    self.df_trade_records.loc[(len(self.df_trade_records) - 1), symbol] = round((self.df_trades['current_u_value'][i] - self.df_trades['init_price'][i]) / self.df_trades['init_price'][i] * 100, 4)
            else:
                self.df_trade_records.insert(len(self.df_trade_records.columns), symbol, '')
                if config.LOG_PRICE_RAW == True:
                    self.df_trade_records.loc[(len(self.df_trade_records)-1), symbol] = round(self.df_trades['current_trade_val'][i], 4)
                else:
                    self.df_trade_records.loc[(len(self.df_trade_records) - 1), symbol] = round((self.df_trades['current_u_value'][i] - self.df_trades['init_price'][i]) / self.df_trades['init_price'][i] * 100, 4)

    def dump_logs(self):
        if self.nb_records % 5 == 0:
            self.df_position_records.to_csv('./LOG/positions_log.csv')
            self.df_trade_records.to_csv('./LOG/trades_log.csv')
            self.df_trades.to_csv('./LOG/active_trades_log.csv')


