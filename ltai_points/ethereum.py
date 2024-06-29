from functools import lru_cache
import json
import os
from pathlib import Path

import web3
from web3._utils.events import (
    construct_event_topic_set,
)
from web3._utils.method_formatters import log_entry_formatter
try:
    from web3.contract import get_event_data
except ImportError:
    from web3._utils.events import get_event_data

from aleph.sdk.chains.ethereum import ETHAccount
from eth_account import Account
from hexbytes import HexBytes

import logging
LOGGER = logging.getLogger(__name__)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

def get_account(settings):
    account = ETHAccount(settings['ethereum_pkey'])
    return account

def get_eth_account(settings):
    if settings['ethereum_pkey']:
        pri_key = HexBytes(settings['ethereum_pkey'])
        try:
            account = Account.privateKeyToAccount(pri_key)
        except AttributeError:
            account = Account.from_key(pri_key)
        return account
    else:
        return None


def get_web3(settings):
    w3 = None
    if settings['ethereum_api_server']:
        w3 = web3.Web3(web3.providers.rpc.HTTPProvider(settings['ethereum_api_server']))
    else:
        from web3.auto.infura import w3 as iw3

        assert w3.isConnected()
        w3 = iw3

    return w3

@lru_cache(maxsize=2)
def get_token_contract_abi():
    return json.load(
        open(os.path.join(Path(__file__).resolve().parent, "abi/ltai.json"))
    )

def get_token_contract(settings, web3):

    address_validator = getattr(web3, "toChecksumAddress",
                                getattr(web3, "to_checksum_address", None))

    tokens = web3.eth.contract(
        address=address_validator(settings['ethereum_token_contract']),
        abi=get_token_contract_abi(),
    )
    return tokens

def get_gas_info(web3):
    latest_block = web3.eth.get_block("latest")
    base_fee_per_gas = latest_block.baseFeePerGas   # Base fee in the latest block (in wei)
    max_priority_fee_per_gas = web3.to_wei(1, 'gwei') # Priority fee to include the transaction in the block
    max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas # Maximum amount you’re willing to pay 
    return max_fee_per_gas, max_priority_fee_per_gas

async def mint_tokens(settings, web3, targets, nonce=None, owner=False):
    tokens = get_token_contract(settings, web3)
    account = get_eth_account(settings)
    # now we call bulkMint, that takes two args: an array of addresses and an array of amounts
    # we need to convert the targets dict to two arrays and the amount to 18 decimal places
    addresses = []
    amounts = []

    for target, amount in targets.items():
        addresses.append(target)
        amounts.append(int(amount * (10**18)))

    max_fee, max_priority = get_gas_info(web3)
    
    if nonce is None:
        nonce= web3.eth.get_transaction_count(account.address)

    fn = tokens.functions.bulkMint
    if owner:
        fn = tokens.functions.ownerBulkMint

    tx = fn(addresses, amounts).build_transaction({
        'chainId': settings['ethereum_chain_id'],
        'gas': 12000000,
        'nonce': nonce,
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': max_priority
    })

    signed_tx = account.sign_transaction(tx)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash, nonce

async def get_logs_query(web3, contract,
                   start_height, end_height, topics,
                   load_mode='rpc', explorer_api_key=None,
                   explorer_api_path=None):
    LOGGER.debug(f'getting events for {start_height} to {end_height}')
    if load_mode == 'rpc':
        try:
            w3_get_logs = web3.eth.getLogs
        except AttributeError:
            w3_get_logs = web3.eth.get_logs

        logs = w3_get_logs({'address': contract.address,
                                'fromBlock': start_height,
                                'toBlock': end_height,
                                'topics': topics})
        for log in logs:
            yield log
    elif load_mode == 'explorer':
        params = {
            "module": "logs",
            "action": "getLogs",
            "fromBlock": start_height,
            "toBlock": end_height,
            "address": contract.address,
            "apikey": explorer_api_key
        }
        for i, topic in enumerate(topics):
            params[f"topic{i}"] = topic
            if i > 0:
                params[f"topic{i-1}_{i}_opr"] = "and"

        resp = requests.get(
            explorer_api_path,
            params=params
        )
        for item in resp.json()['result']:
            item['blockHash'] = None
            yield log_entry_formatter(item)



async def get_logs(web3, contract, start_height, topics=None, load_mode="rpc",
             explorer_api_key=None, explorer_api_path=None, logger=LOGGER):
    try:
        logs = get_logs_query(web3, contract,
                              start_height+1, 'latest', topics=topics,
                              load_mode=load_mode, explorer_api_key=explorer_api_key,
                              explorer_api_path=explorer_api_path)
        async for log in logs:
            yield log
    except ValueError as e:
        # we got an error, let's try the pagination aware version.
        if (getattr(e, 'args')
                and len(e.args)
                and not (-33000 < e.args[0]['code'] <= -32000)):
            return

        try:
            last_block = web3.eth.blockNumber
        except AttributeError:
            last_block = web3.eth.block_number
#         if (start_height < config.ethereum.start_height.value):
#             start_height = config.ethereum.start_height.value

        end_height = start_height + 2000

        while True:
            try:
                logs = get_logs_query(web3, contract,
                                      start_height, end_height, topics=topics,
                                      load_mode=load_mode)
                async for log in logs:
                    yield log

                start_height = end_height + 1
                end_height = start_height + 2000

                if start_height > last_block:
                    logger.info("Ending big batch sync")
                    break

            except ValueError as e:
                LOGGER.error(f"Error getting logs: {e}")
                if -33000 < e.args[0]['code'] <= -32000:
                    end_height = start_height + 200
                else:
                    raise


async def get_all_previous_mints(settings, web3, logger=LOGGER, load_mode='rpc'):
    tokens = get_token_contract(settings, web3)
    abi = tokens.events.Transfer._get_event_abi()

    topic = construct_event_topic_set(abi, web3.codec)
    mints = {}

    async for i in get_logs(web3, tokens, settings['ethereum_min_height'], topics=topic,
                            load_mode=load_mode, logger=logger):
        evt_data = get_event_data(web3.codec, abi, i)

        tx_hash = evt_data['transactionHash'].hex()

        tx_detail = evt_data['args']
        if tx_detail['from'] != ZERO_ADDRESS:
            continue

        address = tx_detail['to']
        amount = tx_detail['value'] / (10**18)
        mints[address] = mints.get(address, 0) + amount
    return mints



    mints = tokens.events.mint().getLogs(fromBlock=settings['ethereum_min_height'])
    # now we do a total of all mints for each address
    mints = {}
    for mint in mints:
        address = mint['args']['to']
        amount = mint['args']['amount'] / (10**18)
        mints[address] = mints.get(address, 0) + amount
    return mints