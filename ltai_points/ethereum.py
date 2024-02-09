from aleph.sdk.chains.ethereum import ETHAccount

import logging
LOGGER = logging.getLogger(__name__)

def get_account(settings):
    account = ETHAccount(settings['ethereum_pkey'])
    return account
