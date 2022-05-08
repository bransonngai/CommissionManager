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
        
def total_comm_stock(broker: str, p, q, sym= ''):
    ''' using by excel '''
    if broker in list(brokers_name.keys()):
        broker = brokers_name[broker]
    
    if broker.lower() not in config_stock.keys():
        raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_stock.keys()))))
    
    c = config_stock[broker.lower()]
    turnover = p * q
    
    comm = max(c['comm_min'], turnover * c['comm'])
    trans_levy = c['trans_levy'] * turnover
    trading_fee = c['trading_fee'] * turnover
    clearing_fee = max(c['clearing_fee_min'], turnover * c['clearing_fee'])
    stamp_duty = max(1, turnover * c['stamp_duty'])
    
    
    total_comm = comm + trans_levy + trading_fee + clearing_fee + stamp_duty
    
    if sym:
        if type(sym) == float:
            sym = int(sym)  # excel will pass 175.0 , trim it by int
        sym = str(sym)
        if util.is_cbbc(sym) or util.is_warrant(sym):
            total_comm -= stamp_duty
    
    return total_comm

def total_comm_futures(broker, product, q):
    # if chinese, covnert it to english
    if broker in list(brokers_name.keys()):
        broker = brokers_name[broker]
    
    if broker.lower() not in config_future.keys():
        raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_future.keys()))))
    
    c =  config_future[broker.lower()]
    return c[product.lower()] * q

def total_comm_us_stock(broker:str, shares, price, action:str):
    
    if broker in list(brokers_name.keys()):
        broker = brokers_name[broker]
    
    if broker.lower() not in config_us_stock.keys():
        raise ValueError('Broker no found. Available broker is: {}'.format(','.join(list(config_us_stock.keys()))))
        
    # chinese action
    action_buy_dic = dict(zip(buy_phase_chinese,['buy'] * len(buy_phase_chinese)))
    action_sell_dic = dict(zip(sell_phase_chinese,['sell'] * len(sell_phase_chinese)))
    if action in list(action_buy_dic.keys()):
        action = 'buy'
    elif action in list(action_sell_dic.keys()):
        action = 'sell'
        
    c = config_us_stock[broker.lower()]

    fee = 0   
    
    comm = max(c['comm_min'], shares * c['comm'])
    platform_fee = max(c['platform_fee_min'], shares * c['platform_fee'])
    clearing_fee = c['clearing_fee'] * shares
    
    fee += comm + platform_fee + clearing_fee
    
    if action.lower() == 'sell' or action.lower() == 's':
        sfc_fee = max(c['sfc_fee'] * (shares* price),  c['sfc_fee_min'])
        trading_levy = max(c['trading_levy'] * shares, c['trading_levy_min']) # 交易活動費
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
    
    
    def __init__(self, broker_name, round_up_to= 2):
        self.broker = broker_name
        self.round_up_to = round_up_to
        
        #commission_profiles = ini_Manager('commission').return_config_as_dic()
        #self.comm = commission_profiles[broker_name]
        
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
        mini = float(self.comm['min'])
        comm = float(self.comm['comm']) / 100
        levy = float(self.comm['levy']) / 100
        trans = float(self.comm['trans']) / 100
        ccass = float(self.comm['ccass']) / 100
        ccass_min = float(self.comm['ccass_min'])
        stamp = float(self.comm['stamp']) / 100
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
    


