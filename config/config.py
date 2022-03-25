TV_INTERVAL_1_MINUTE = "1m"
TV_INTERVAL_5_MINUTES = "5m"
TV_INTERVAL_15_MINUTES = "15m"
TV_INTERVAL_30_MINUTES = "30m"
TV_INTERVAL_1_HOUR = "1h"
TV_INTERVAL_2_HOURS = "2h"
TV_INTERVAL_4_HOURS = "4h"
TV_INTERVAL_1_DAY = "1d"
TV_INTERVAL_1_WEEK = "1W"
TV_INTERVAL_1_MONTH = "1M"

INTERVAL_EXPRESS = [TV_INTERVAL_5_MINUTES, TV_INTERVAL_15_MINUTES, TV_INTERVAL_30_MINUTES]
INTERVAL_SHORT = [TV_INTERVAL_15_MINUTES, TV_INTERVAL_30_MINUTES, TV_INTERVAL_1_HOUR]
INTERVAL_MIDDLE = [TV_INTERVAL_1_HOUR, TV_INTERVAL_2_HOURS, TV_INTERVAL_4_HOURS]
INTERVAL_LONG = [TV_INTERVAL_1_DAY, TV_INTERVAL_1_WEEK, TV_INTERVAL_1_MONTH]

INTERVAL = INTERVAL_SHORT  # PARAMETER

RECOMMENDATION_ALL = ["STRONG_BUY", "BUY", "NEUTRAL", "STRONG_SELL", "SELL"]

FILTER_STRONG_BUY = ["STRONG_BUY"]
FILTER_BUY = ["STRONG_BUY", "BUY"]
FILTER_BUY_WEAK = ["BUY", "NEUTRAL"]
FILTER_NEUTRAL = ["NEUTRAL"]
FILTER_SELL_WEAK = ["SELL", "NEUTRAL"]
FILTER_SELL = ["STRONG_SELL", "SELL"]
FILTER_STRONG_SELL = ["STRONG_SELL"]

FILTER = FILTER_BUY     # PARAMETER


EXCHANGE_BINANCE = "binance"
EXCHANGE_FTX = "ftx"
EXCHANGE = EXCHANGE_FTX  # PARAMETER

SCREENER_TYPE = "crypto"

PAIR_USD = "/USD"
PAIR_USDT = "/USDT"
PAIR_EUR = "/EUR"

PRICE_TOP_GAINER = 50     # PARAMETER

VOLUME_THRESHOLD = 10000
VOLUME_FILTERED_BY_INFO = True

datapath = '.\datas\orcl-1995-2014.txt'

COLUMNS_TRADES = ['id', 'time', 'pair', 'init_price', 'trade_size', 'net_price', 'commission', 'gross_price', 'current_u_value', 'current_trade_val', 'profit_loss']
COLUMNS_TRADES_RECORDS = ['id', 'time', 'cash', 'positive_trades', 'negative_trades', 'open_trades', 'total_nb_trades', 'portfolio_value']

COLUMNS_BUY_SELL = ['pair', 'ranking','score', '24h', '1h', 'buy', 'sell', 'neutral']

COLUMNS_POSITION_RECORDS = ['id', 'time', 'cash', 'positive_trades', 'negative_trades', 'open_trades', 'total_nb_trades', 'portfolio_value']

MULTITHREADING_POOL = "./POOL/"

BUYING_SCORE_THRESHOLD = 0
INIT_SYMBOL ='BTC/USD'
TRADE_SIZE = 100  # $100
STOP_LOSS = -0.10
GET_PROFIT = 0.15