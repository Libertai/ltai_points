""" Handle supply management.
The pool dict is passed around to increment the distributed amount.

Example supply file:
max_supply: 60000000
pools:
  raise:
    total: 15000000
    initial: 0.5
    type: linear
    duration: 730
  airdrop:
    total: 21000000
    type: points
  reserves:
    total: 15000000
    initial: 0.3333333333333333
    type: linear
    duration: 2400
  team:
    total: 9000000
    initial: 0.1111111111111111
    type: linear
    duration: 2400
    
allocations:
  - address: 0x8430493c7CC24Df1c130f9d729Ce4FCf40F05215
    amount: 1000000
    pool: team
    type: instant
  - address: 0x8430493c7CC24Df1c130f9d729Ce4FCf40F05215
    amount: 8000000
    pool: team
    type: linear
    duration: 2400
  - address: 0x8430493c7CC24Df1c130f9d729Ce4FCf40F05215
    amount: 5000000
    pool: reserves
    type: instant
  - address: 0x8430493c7CC24Df1c130f9d729Ce4FCf40F05215
    amount: 10000000
    pool: reserves
    type: linear
    duration: 2400
"""
import yaml
import web3
from datetime import datetime, date, timezone

def get_supply_info(settings):
    # we read a yaml file defined in settings with the allocs details
    w3 = web3.Web3()
    filename = settings['supply_filename']
    with open(filename, 'r') as f:
        supply_info = yaml.safe_load(f)
        pools = supply_info['pools']
        for pool in pools.values():
            if 'distributed' not in pool:
              pool['distributed'] = 0
        max_supply = supply_info['max_supply']
        allocations = supply_info['allocations']
        for alloc in allocations:
            alloc['address'] = w3.to_checksum_address(alloc['address'])
            alloc['distributed'] = 0
        return pools, max_supply, allocations
    
def get_instant_allocs(allocations, pools=None):
    instant_allocs = {}
    for alloc in allocations:
        if alloc['type'] == 'instant':
            instant_allocs[alloc['address']] = instant_allocs.get(alloc['address'], 0) + alloc['amount']
            if pools is not None:
                pool = pools.get(alloc['pool'], None)
                if pool:
                    pool['distributed'] += alloc['amount']
    return instant_allocs

def get_linear_allocs(settings, allocations, check_date, pools=None):
    # check_date is a text isoformat object, we compare with settings['tge_ts'] to get the number of days since the TGE
    # linear duration is in days.
    linear_allocs = {}
    tge = datetime.fromtimestamp(settings['tge_ts'], timezone.utc)
    check_time = datetime.fromisoformat(check_date).replace(tzinfo=timezone.utc)
    if check_time < tge:
        return {}

    days_since_tge = (check_time - tge).days
    
    for alloc in allocations:
        if alloc['type'] == 'linear':
            days_since_tge = (check_time - tge).days
            max_amount = alloc['amount']
            daily_amount = max_amount / alloc['duration']
            alloc_amount = min(max_amount, daily_amount * days_since_tge)
            linear_allocs[alloc['address']] = linear_allocs.get(alloc['address'], 0) + alloc_amount
            if pools is not None:
                pool = pools.get(alloc['pool'], None)
                if pool:
                    pool['distributed'] += alloc_amount

    return linear_allocs