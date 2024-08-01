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

def get_linear_allocs(settings, allocations, check_time, start_time=None, pools=None):
    linear_allocs = {}
    tge = datetime.fromtimestamp(settings['tge_ts'], timezone.utc)
    
    if isinstance(check_time, str):
        check_time = datetime.fromisoformat(check_time).replace(tzinfo=timezone.utc)
    else:
        check_time = check_time.replace(tzinfo=timezone.utc)
    
    if check_time < tge:
        return {}

    if start_time is None:
        start_time = tge
    else:
        start_time = start_time.replace(tzinfo=timezone.utc)
        start_time = max(start_time, tge)  # Ensure start_time is not before TGE

    for alloc in allocations:
        if alloc['type'] == 'linear':
            max_amount = alloc['amount']
            duration_minutes = alloc['duration'] * 24 * 60  # Convert days to minutes
            minute_amount = max_amount / duration_minutes
            
            alloc_start = max(start_time, tge + timedelta(days=alloc.get('cliff', 0)))
            minutes_since_start = max(0, (check_time - alloc_start).total_seconds() / 60)
            
            alloc_amount = min(max_amount, minute_amount * minutes_since_start)
            linear_allocs[alloc['address']] = linear_allocs.get(alloc['address'], 0) + alloc_amount
            
            if pools is not None:
                pool = pools.get(alloc['pool'], None)
                if pool:
                    pool['distributed'] += alloc_amount

    return linear_allocs