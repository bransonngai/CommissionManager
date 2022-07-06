import os
import configparser

from BATrader.utils.product_checker import determine_product_type
import BATrader.utils as util

# stock
ini_stock = configparser.ConfigParser()
ini_stock.read(os.path.join(os.path.dirname(__file__), 'commissions_stock.ini'))

# futures
ini_future = configparser.ConfigParser()
ini_future.read(os.path.join(os.path.dirname(__file__), 'commissions_future.ini'))

# Option
ini_option = configparser.ConfigParser()
ini_option.read(os.path.join(os.path.dirname(__file__), 'commissions_option.ini'))

# US Stock
ini_us_stock = configparser.ConfigParser()
ini_us_stock.read(os.path.join(os.path.dirname(__file__), 'commissions_us_stock.ini'))

# US Stock
ini_multiplier = configparser.ConfigParser()
ini_multiplier.read(os.path.join(os.path.dirname(__file__), 'futures_multiplier.ini'))

# broker name pair
brokers_name = {'耀才': 'bsgroup',
                '招銀': 'cmbi',
                '六福': 'lukfook',
                '富途': 'futu',
                '致富': 'chief',
                '一通': 'iaccess',
                '時富': 'cash',
                '輝立': 'poems'}

# action pair
buy_phase_chinese = ['買', '買入', '進']
sell_phase_chinese = ['賣', '賣出', '沽出', '沽空']


def return_config_as_dic(ini):
    conf = {}
    ret = ini.sections()

    for key in ret:
        conf[key] = {}
        items = ini.items(key)
        for item in items:
            conf[key][item[0]] = item[1]
            
    return conf


# make them float
config_stock = return_config_as_dic(ini_stock)
config_stock = {k.lower(): {item: float(fee) for item, fee in v.items()} for k, v in config_stock.items()}

config_future = return_config_as_dic(ini_future)
config_future = {k.lower(): {item.lower(): float(fee) for item, fee in v.items()} for k, v in config_future.items()}

config_us_stock = return_config_as_dic(ini_us_stock)
config_us_stock = {k.lower(): {item.lower(): float(fee) for item, fee in v.items()} for k, v in config_us_stock.items()}

config_option = return_config_as_dic(ini_option)
config_option = {k.lower(): {item.lower(): float(fee) for item, fee in v.items()} for k, v in config_option.items()}

config_multiplier = return_config_as_dic(ini_multiplier)


# =============================================================================
# Below mostly using by Excel
# =============================================================================
def total_comm_option(broker:str, product:str, position, execution= False):
    
    if broker in list(brokers_name.keys()):
        broker = brokers_name[broker]
    
    if broker.lower() not in config_option.keys():
        raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_option.keys()))))
        
    c = config_option[broker.lower()]
    
    if execution:
        return c['{}_execution_fee'.format(product.lower())]
    
    return c[product.lower()] * position


def total_comm_stock(p,
                     q,
                     broker: str = '',
                     sym: str = '',
                     hk_comm_scheme: dict = {},
                     turnover: float = 0,
                     round_to: int = 2):
    """ using by excel """

    # using broker to look up scheme
    if broker:
        hk_comm_scheme = config_stock.get(broker.lower(), None)
        if not hk_comm_scheme:
            raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_stock.keys()))))

    if not turnover:
        turnover = p * q
    
    comm = max(hk_comm_scheme['comm_min'], turnover * hk_comm_scheme['comm'])
    trans_levy = hk_comm_scheme['trans_levy'] * turnover
    trading_fee = hk_comm_scheme['trading_fee'] * turnover
    clearing_fee = max(hk_comm_scheme['clearing_fee_min'], turnover * hk_comm_scheme['clearing_fee'])
    stamp_duty = max(1, turnover * hk_comm_scheme['stamp_duty'])
    frc_levy = turnover * hk_comm_scheme['frc_levy']

    total_comm = comm + trans_levy + trading_fee + clearing_fee + stamp_duty + frc_levy
    
    if sym:
        if type(sym) == float:
            sym = int(sym)  # excel will pass 175.0 , trim it by int
        sym = str(sym)
        if util.is_cbbc(sym) or util.is_warrant(sym):
            total_comm -= stamp_duty
    
    return round(total_comm, round_to)


def total_comm_futures(p,
                       q,
                       broker: str = '',
                       sym: str = '',
                       hk_future_scheme: dict = {},
                       round_to: int = 0):

    # if chinese, covnert it to english
    if broker:
        hk_future_scheme = config_future.get(broker.lower(), None)
        if not hk_future_scheme:
            raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_future.keys()))))
    
    comm = hk_future_scheme[sym.upper()]  # each one commission
    return round(q * comm, round_to)


def total_comm_us_stock(shares,
                        price,
                        action: str,
                        broker: str = '',
                        us_stock_scheme: dict = {},
                        round_to: int = 2):
    if broker:
        us_stock_scheme = config_us_stock.get(broker.lower(), None)
        if not us_stock_scheme:
            raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_us_stock.keys()))))
        
    # chinese action
    action_buy_dic = dict(zip(buy_phase_chinese,['buy'] * len(buy_phase_chinese)))
    action_sell_dic = dict(zip(sell_phase_chinese,['sell'] * len(sell_phase_chinese)))
    if action in list(action_buy_dic.keys()):
        action = 'buy'
    elif action in list(action_sell_dic.keys()):
        action = 'sell'

    fee = 0   
    
    comm = max(us_stock_scheme['comm_min'], shares * us_stock_scheme['comm'])
    platform_fee = max(us_stock_scheme['platform_fee_min'], shares * us_stock_scheme['platform_fee'])
    clearing_fee = us_stock_scheme['clearing_fee'] * shares
    
    fee += comm + platform_fee + clearing_fee
    
    if action.lower() == 'sell' or action.lower() == 's':
        sfc_fee = max(us_stock_scheme['sfc_fee'] * (shares* price),  us_stock_scheme['sfc_fee_min'])
        trading_levy = max(us_stock_scheme['trading_levy'] * shares, us_stock_scheme['trading_levy_min']) # 交易活動費
        fee += sfc_fee
        fee += trading_levy
        
    return fee


def ipo_margin_fee(loan_amount, interest_rate, loan_duration):
    return (loan_amount * (interest_rate / 100)) * (loan_duration/ 365)


def futures_multipier(product):
    """
    期貨一Tick代表多少跳動
    """
    product = str.lower(product)
    return float(config_multiplier[product]['multiplier'])


# =============================================================================
# Commission Manager (Depreciated)
# =============================================================================
class CommissionManager:
    """
    I will look up config/commission.ini
    """

    def __init__(self,
                 broker_name: str,
                 round_up_to: int = 2):

        self.broker = broker_name.lower()
        self.round_up_to = round_up_to
        
        # self.commission_profiles = util.ini_Manager('commission').return_config_as_dic()
        self.comm_stock = config_stock.get(self.broker, None)
        self.comm_future = config_future.get(self.broker, None)
        self.comm_us_stock = config_us_stock.get(self.broker, None)
        self.comm_option = config_option.get(self.broker, None)

        self.multipler = config_multiplier

    def change_broker(self, new_broker_name):
        self.__init__(broker_name=new_broker_name, round_up_to=self.round_up_to)

    def hk_stock(self,
                 p: float = None,
                 q: float = None,
                 sym: str = '',
                 turnover: float = 0):
        return total_comm_stock(p=p,
                                q=q,
                                sym=sym,
                                turnover=turnover,
                                hk_comm_scheme=self.comm_stock,
                                round_to=self.round_up_to)

    def transaction_cost_by_sym(self, sym: str, p: float= '', q: float= '', turnover: float= ''):
        """
        Parameters
        ----------
        sym : str
            DESCRIPTION.
        p : float, optional
            DESCRIPTION. The default is ''.
        q : float, optional
            DESCRIPTION. The default is ''.
        turnover : float, optional
            DESCRIPTION. The default is ''.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        product = determine_product_type(sym)
        if product == 'STOCKS':
            # using stocks fee
            if not p and not q and turnover:
                return self.transaction_cost_by_turnover(turnover)
            elif not turnover and p and q:
                return self.transaction_cost(p, q)
            else:
                print('CALC COMMISSION ERROR in CommissionManager')
                return 0
        elif product == 'FUTURES':
            return self.transaction_cost_futures(q, sym) # sym need to be like MHIF or HSIF etc.

    def transaction_cost(self, p, q):
    
        # return if no transcation
        if p == 0 and q == 0:
            return 0
    
        from math import ceil
        mini = float(self.comm_stock['comm_min'])
        comm = float(self.comm_stock['comm']) / 100
        levy = float(self.comm_stock['trans_levy']) / 100
        trans = float(self.comm_stock['trans']) / 100
        ccass = float(self.comm_stock['ccass']) / 100
        ccass_min = float(self.comm_stock['ccass_min'])
        stamp = float(self.comm_stock['stamp']) / 100
        # margin_rate = float(self.comm['margin_rate']) / 100
    
        # comm?
        if q == 0:
            turnover = p
        else:
            turnover = p * q
    
        # using ternary a if condition else b
        commission = (turnover * comm) if (turnover * comm) > mini else mini
        trading_levy = turnover * levy
        transaction_fee = turnover * trans
        ccass_fee = (turnover * ccass) if (turnover * ccass) > ccass_min else ccass_min
        stamp_duty = ceil(turnover * stamp)
    
        transaction_cost = commission + trading_levy + transaction_fee + ccass_fee + stamp_duty
        return round(transaction_cost, self.round_up_to)
    
    def transaction_cost_by_turnover(self, turnover):
        return self.transaction_cost(turnover, 0)
    
    def transaction_cost_futures(self, q, product='hsif'):
        product = str.lower(product)
        if product == 'hsif' or product == 'mhif':
            comm = float(self.comm['comm_%s' % product])
            sfc = float(self.comm['sfc_%s' % product])
            trans = float(self.comm['trans_%s' % product])
    
            transaction_cost = (comm + sfc + trans) * int(q)
            return transaction_cost
        else:
            print('product no found')
            return 0


if __name__ == '__main__':
    cmm = CommissionManager('FUTU')
    # print(total_comm_stock(100, 100, 'FUTU'))
    print(total_comm_us_stock(2, 600, 'buy', 'FUTU'))
    print(total_comm_us_stock(2, 600, 'sell', 'FUTU'))
    ini = util.ini_Manager('commission').return_config_as_dic()

    print(cmm.transaction_cost_by_sym('700', 100, 100))
    pass
