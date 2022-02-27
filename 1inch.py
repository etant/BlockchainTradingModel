import json
import requests
from security import *
from decimal import Decimal


class OneInchExchange:

    base_url = 'https://api.1inch.exchange'
    chains = dict(
        polygon = "137",
        arbitrum = "42161")
    versions = dict(

        v4 = "v4.0"
    )

    endpoints = dict(
        swap = "swap",
        quote = "quote",
        tokens = "tokens",
        protocols = "protocols",
        protocols_images = "protocols/images",
        approve_spender = "approve/spender",
        approve_calldata = "approve/calldata"
    )

    tokens = dict()
    tokens_by_address = dict()
    protocols = []
    protocols_images = []

    def __init__(self, address, chain='ethereum'):
        self.address = address
        self.version = 'v4.0'
        self.chain_id = self.chains[chain]
        self.chain = chain
        self.get_tokens()
        # self.get_protocols()
        # self.get_protocols_images()


    def _get(self, url, params=None, headers=None):
        """ Implements a get request """
        try:
            response = requests.get(url, params=params, headers=headers)
            payload = json.loads(response.text)
            data = payload
        except requests.exceptions.ConnectionError as e:
            print("ConnectionError when doing a GET request from {}".format(url))
            data = None
        return data


    def health_check(self):
        url = '{}/v4.0/{}/healthcheck'.format(
            self.base_url, self.chain_id)
        response = requests.get(url)
        result = json.loads(response.text)
        if not result.__contains__('status'):
            return result
        return result['status']


    def get_tokens(self):
        url = '{}/{}/{}/tokens'.format(
            self.base_url, self.version, self.chain_id)
        result = self._get(url)
        if not result.__contains__('tokens'):
            return result
        for key in result['tokens']:
            token = result['tokens'][key]
            self.tokens_by_address[key] = token
            self.tokens[token['symbol']] = token
        return self.tokens


    def get_protocols(self):
        url = '{}/{}/{}/protocols'.format(
            self.base_url, self.version, self.chain_id)
        result = self._get(url)
        if not result.__contains__('protocols'):
            return result
        self.protocols = result
        return self.protocols


    def get_protocols_images(self):
        url = '{}/{}/{}/protocols/images'.format(
            self.base_url, self.version, self.chain_id)
        result = self._get(url)
        if not result.__contains__('protocols'):
            return result
        self.protocols_images = result
        return self.protocols_images


    def get_quote(self, from_token_symbol:str, to_token_symbol:str, amount:int):
        url = '{}/{}/{}/quote'.format(
            self.base_url, self.version, self.chain_id)
        url = url + '?fromTokenAddress={}&toTokenAddress={}&amount={}'.format(
            self.tokens[from_token_symbol]['address'],
            self.tokens[to_token_symbol]['address'],
            format(Decimal(10**self.tokens[from_token_symbol]['decimals'] \
                * amount).quantize(Decimal('1.')), 'n'))
        result = self._get(url)
        return result


    def do_swap(self, from_token_symbol:str, to_token_symbol:str,
        amount:int, slippage:int):
        self.get_allowance(token_symbol= from_token_symbol)
        url = '{}/{}/{}/swap'.format(
            self.base_url, self.version, self.chain_id)
        amount = self.convert_amount_to_decimal(from_token_symbol,amount)
        url = url + "?fromTokenAddress={}&toTokenAddress={}&amount={}".format(
            self.tokens[from_token_symbol]['address'],
            self.tokens[to_token_symbol]['address'],
            amount)
        url = url + '&fromAddress={}&slippage={}'.format(
            self.address, slippage)

        txn = self._get(url)["tx"]
        if "description" in txn.keys():
            if "balance" in txn["description"]:
                return (txn["description"])

        txn["value"] = int(txn["value"])
        txn["nonce"]  = web3.eth.getTransactionCount(wallet)

        txn["gasPrice"] = int(txn["gasPrice"])
        txn["to"] = web3.toChecksumAddress(txn["to"])
        txn["chainId"] = int(self.chain_id)

        signAndSend(txn)

    def convert_amount_to_decimal(self, token_symbol, amount):
        decimal = self.tokens[token_symbol]['decimals']

        return int(amount*(10**decimal))

    def get_allowance(self, token_symbol:str):
        url = '{}/{}/{}/approve/allowance'.format(
            self.base_url, self.version, self.chain_id)
        url = url + "?tokenAddress={}&walletAddress={}".format(
            self.tokens[token_symbol]['address'],
            self.address)
        result = self._get(url)
        if result['allowance'] == '0':
            return self.approve_transaction(token_symbol = token_symbol)

        return result

    def approve_transaction(self, token_symbol:str):
        url = '{}/{}/{}/approve/transaction'.format(
            self.base_url, self.version, self.chain_id)
        url = url + "?tokenAddress={}".format(
            self.tokens[token_symbol]['address'])
        txn = self._get(url)
        txn["gas"] = 311658
        txn["nonce"]  = web3.eth.getTransactionCount(wallet)

        txn["gasPrice"] = int(txn["gasPrice"])
        txn["to"] = web3.toChecksumAddress(txn["to"])
        txn["chainId"] = int(self.chain_id)
        txn['value'] = int(txn["value"])
        signAndSend(txn)

def signAndSend(txn):


    signed_tx = web3.eth.account.signTransaction(txn,key)

    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)

    print (web3.toHex(tx_hash))

if __name__ == '__main__':
    exchange = OneInchExchange(wallet,"polygon")
    # amt = exchange.convert_amount_to_decimal("USDT",.1)


    #exchange.get_allowance(token_symbol = "WBTC")
    #print(web3.eth.getTransactionReceipt(0x903309cbff2be7740c14829bad8bfe3d6d8ee00373837cb632d85df0ae5ade19))
    exchange.do_swap(from_token_symbol='MATIC', to_token_symbol='USDT', amount=0.5,slippage = 1)
    # txn = eth_exchange.approve_transaction("USDT")
