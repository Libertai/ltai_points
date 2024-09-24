"""Main module."""
from .fetcher import get_account_registrations, get_aleph_rewards, get_pending_rewards, get_staked_amounts, get_corechanel_statuses
from .supply import get_instant_allocs, get_supply_info, get_linear_allocs
from datetime import datetime, timezone, timedelta
from .ethereum import get_web3
import pprint
import math
import web3

def compute_score_multiplier(score: float) -> float:
    """
    Compute the score multiplier
    """
    if score < 0.2:
        # The score is zero below 20%
        return 0
    elif score >= 0.8:
        # The score is 1 above 80%
        return 1
    else:
        # The score is normalized between 20% and 80%
        assert 0.2 <= score <= 0.8
        return (score - 0.2) / 0.6
    
def compute_reward_multiplier(ratio: float) -> float:
    """
    Compute the reward multiplier.
    If ratio is between 0.9 and 1, the reward multiplier is 1.
    If ratio is under 0.9 apply y=-sqrt(-x+0.9)+1
    If ratio is over 1 apply y=0.5sqrt(x-1)+1
    """
    if ratio < 0.4:
        return 0
    if ratio < 0.9:
        return -math.sqrt(-ratio + 0.9) + 1
    elif ratio > 1:
        return 0.5 * math.sqrt(ratio - 1) + 1
    else:
        return 1
    
linked_addresses = dict()
address_identifiers = dict()
nodes_addresses = dict()
    
async def get_address_reward_multiplier(address: str, previous_mints: dict, 
                                  balances: dict) -> float:
    """
    Get the reward multiplier for an address.
    ratio = holdings / minted
    """
    if address not in balances or address not in previous_mints:
        return 1
    return compute_reward_multiplier(balances[address] / previous_mints[address])

async def get_address_cluster_reward_multiplier(address: str, previous_mints: dict,
                                                balances: dict):
    """ use linked_addresses to get the reward multiplier for any address of a cluster (we add all balances together) """
    linked_addresses = get_linked_addresses(address)
    total_balance = sum([balances[addr] for addr in linked_addresses if addr in balances])
    total_minted = sum([previous_mints[addr] for addr in linked_addresses if addr in previous_mints])
    if total_minted < 100:
        return 1
    return compute_reward_multiplier(total_balance / total_minted)

async def process_round(reward_round, reward_time, totals, registrations, settings):
    ratio = settings['aleph_reward_ratio']
    bonus_ratio = settings['bonus_ratio']
    
    days_since_start = (reward_time - settings['reward_start_ts']) / 86400
    print(f"Processing rewards for {reward_time} ({days_since_start} days since start)")
    decay = settings['daily_decay'] ** int((reward_time - settings['reward_start_ts']) / 86400)
    distribution_ratio = ratio * decay
    
    # decrease the bonus linearly over the bonus duration
    distribution_bonus_ratio = 1 
    if days_since_start < settings['bonus_duration']:
        distribution_bonus_ratio = bonus_ratio * (1 - min(1, days_since_start / settings['bonus_duration']))

    # now check which addresses should have the bonus for this round (only if they registered before the bonus limit, and before this distribution)
    bonus_addresses = [address for address, registration_time in registrations.items()
                        if registration_time < reward_time and registration_time < settings['bonus_limit_ts']]
    round_total = 0
    round_rewards = 0
    for address, value in reward_round.items():
        round_total += value
        
        if address not in totals:
            totals[address] = 0
        reward = value * distribution_ratio
        round_rewards += reward
        if address in bonus_addresses:
            reward *= distribution_bonus_ratio

        totals[address] += reward
    print(f"Round total: {round_total}, rewards: {round_rewards}, decay: {decay}, distribution ratio: {distribution_ratio}")

async def get_staked_amounts(status):
    message_totals = {}

    for node in status['nodes']:
        node_address = node.get('reward', node['owner'])
        message_totals[node_address] = message_totals.get(node_address, 0) + 200000
        for address, amount in node['stakers'].items():
            message_totals[address] = message_totals.get(address, 0) + amount

    return message_totals

def compute_score_multiplier(score: float) -> float:
    """
    Compute the score multiplier
    """
    if score < 0.2:
        # The score is zero below 20%
        return 0
    elif score >= 0.8:
        # The score is 1 above 80%
        return 1
    else:
        # The score is normalized between 20% and 80%
        assert 0.2 <= score <= 0.8
        return (score - 0.2) / 0.6

async def link_addresses(node_hash, node_owner, reward_address):
    """ We try to find cheaters who move their rewards to a different address
    to game the system """
    if node_hash not in linked_addresses:
        nodes_addresses[node_hash] = set()
    nodes_addresses[node_hash].add(reward_address)
    nodes_addresses[node_hash].add(node_owner)
    return nodes_addresses[node_hash]

async def process_address_links():
    """ populate linked_addresses based on the nodes addresses """
    for node_hash, addresses in nodes_addresses.items():
        for address in addresses:
            if address not in linked_addresses:
                linked_addresses[address] = set()
            linked_addresses[address].update(addresses)
    
    for i in range(2):
        for key, values in list(linked_addresses.items()):
            if key not in values:
                values.add(key)
            for value in values:
                if value not in linked_addresses:
                    linked_addresses[value] = set()
                linked_addresses[value].update(values)

def get_linked_addresses(address):
    """ we need to find all addresses linked to one in any of the node """
    if address not in linked_addresses:
        return set([address])
    
    linked_addresses[address].add(address)
    return linked_addresses[address]


async def process_virtual_daily_round(round_date, status, totals, registrations, settings, day_ratio=1):
    w3 = web3.Web3()
    ratio = settings['staked_ratio']
    distrib_ratio = settings['aleph_reward_ratio']
    bonus_ratio = settings['bonus_ratio']
    reward_time = datetime.fromisoformat(round_date).replace(tzinfo=timezone.utc).timestamp()
    days_since_start = int(reward_time - settings['reward_start_ts']) / 86400
    stakers_daily_base = settings['aleph_reward_stakers_daily_base']
    nodes_daily_base = settings['aleph_reward_nodes_daily_base']

    active_nodes = [node for node in status['nodes'] if node["status"] == "active"]
    resource_nodes = {rnode['hash']: rnode for rnode in status['resource_nodes']}
    per_day_stakers = (
            (math.log10(len(active_nodes)) + 1) / 3
        ) * stakers_daily_base

    per_node = nodes_daily_base / len(active_nodes)
    
    daily_base = per_day_stakers + nodes_daily_base
    decay = settings['daily_decay'] ** days_since_start
    daily_ltai = daily_base * decay * ratio
    distrib_decayed_ratio = distrib_ratio * decay

    staked_amounts = await get_staked_amounts(status)

    total_staked = sum(staked_amounts.values())
    ltai_ratio = daily_ltai / total_staked

    def compute_resource_node_rewards(decentralization_factor):
        return (
            (
                settings['aleph_reward_resource_node_monthly_base']
                + (
                    settings['aleph_reward_resource_node_monthly_variable']
                    * decentralization_factor
                )
            )
            / (365/12)
        )

    distribution_bonus_ratio = 1
    settings_bonus_addresses = settings['bonus_addresses']
    bonus_addresses = [address for address, registration_time in registrations.items()
                        if registration_time < reward_time and registration_time < settings['bonus_limit_ts']]
    # add the settings bonus addresses
    bonus_addresses += settings_bonus_addresses
    bonus_addresses = [w3.to_checksum_address(address) for address in bonus_addresses]
    if reward_time < settings['bonus_limit_ts']:
        distribution_bonus_ratio = 1 + ((bonus_ratio-1) * (1 - min(1, days_since_start / settings['bonus_duration'])))
    
    def increment_address_amount(address, amount):
        address = w3.to_checksum_address(address)
        if address not in totals:
            totals[address] = 0
        reward = amount
        if address in bonus_addresses:
            reward *= distribution_bonus_ratio
        totals[address] += reward * day_ratio
    
    for address, value in staked_amounts.items():
        increment_address_amount(address, value * ltai_ratio)

    for node in active_nodes:
        reward_address = node["owner"]
        this_node = per_node

        rnodes = node["resource_nodes"]
        paid_node_count = 0
        for rnode_id in rnodes:
            rnode = resource_nodes.get(rnode_id, None)
            if rnode is None:
                continue
            if rnode["status"] != "linked": # how could this happen?
                continue

            rnode_reward_address = rnode["owner"]
            try:
                rtaddress = w3.to_checksum_address(rnode.get("reward", None))
                if rtaddress:
                    rnode_reward_address = rtaddress
            except Exception:
                print("Bad reward address, defaulting to owner")

            crn_multiplier = compute_score_multiplier(rnode["score"])

            assert 0 <= crn_multiplier <= 1, "Invalid value of the score multiplier"

            this_resource_node = (
                compute_resource_node_rewards(rnode["decentralization"])
                * crn_multiplier
            )

            if crn_multiplier > 0:
                paid_node_count += 1
            
            if paid_node_count <= settings['aleph_node_max_paid']: # we only pay the first N nodes
                await link_addresses(rnode["hash"], rnode["owner"], rnode_reward_address)
                increment_address_amount(rnode_reward_address, this_resource_node*distrib_decayed_ratio)

        if paid_node_count > settings['aleph_node_max_paid']:
            paid_node_count = settings['aleph_node_max_paid']

        score_multiplier = compute_score_multiplier(node["score"])
        assert 0 <= score_multiplier <= 1, "Invalid value of the score multiplier"

        linkage = 0.7 + (0.1 * paid_node_count)

        if linkage > 1: # Cap the linkage at 1
            linkage = 1

        assert 0.7 <= linkage <= 1, "Invalid value of the linkage"

        this_node_modifier = linkage * score_multiplier

        this_node = this_node * this_node_modifier

        try:
            taddress = w3.to_checksum_address(node.get("reward", None))
            if taddress:
                reward_address = taddress
        except Exception:
            print("Bad reward address, defaulting to owner")

        await link_addresses(node["hash"], node["owner"], reward_address)
        increment_address_amount(reward_address, this_node*distrib_decayed_ratio)

        for addr, value in node["stakers"].items():
            sreward = ((value / total_staked) * per_day_stakers) * this_node_modifier
            increment_address_amount(addr, sreward*distrib_decayed_ratio)

    # print(daily_ltai)
    # print(round_date, sum(staked_amounts.values()))

async def compute_points(settings, dbs, previous_mints, balances, pools, allocations, last_distribution_time, last_distribution_times):
    w3 = web3.Web3()
    ratio = settings['aleph_reward_ratio']
    bonus_ratio = settings['bonus_ratio']
    totals = {}
    pending_totals = {}

    registrations, counts = await get_account_registrations(settings)
    print(f"Found {len(registrations)} registrations")
            
    settings_bonus_addresses = [w3.to_checksum_address(address) for address in settings['bonus_addresses']]
    for address in settings_bonus_addresses:
        if address not in totals:
            totals[address] = 1000
    
    all_bonus_addresses = [address for address, registration_time in registrations.items()
                           if registration_time < settings['bonus_limit_ts']]
    
    for address in all_bonus_addresses:
        if address not in totals:
            totals[address] = 10
            
    last_time = 0
    first_time = 0

    last_distribution_datetime = datetime.fromtimestamp(last_distribution_time, timezone.utc)
    last_distribution_date = datetime.fromtimestamp(last_distribution_time, timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc)
    today_date = datetime.now(timezone.utc).date()
    today = today_date.isoformat()

    today_status = None
    async for ddate, status in get_corechanel_statuses(settings, dbs):
        
        dtotals = totals
        # if ddate >= pending_date:
        #     dtotals = pending_totals
            
        # if ddate == today:
        #     today_status = status
        #     continue

        if ddate == today:
            # we need to process the pending rewards for today
            ttime = None
            if ddate == last_distribution_date:
                # if distribution happened today, start then
                ttime = last_distribution_time
            else:
                # if not, start at the beginning of the day
                ttime = datetime.fromisoformat(today).replace(tzinfo=timezone.utc).timestamp()

            pending_ratio = (now.timestamp() - ttime) / 86400
            await process_virtual_daily_round(today, status, pending_totals, registrations, settings, day_ratio=pending_ratio)

        elif ddate == last_distribution_date:
            # on distribution day, pending ratio is time from distribution till midnight
            pending_ratio = (last_distribution_datetime.replace(hour=23, minute=59, second=59).timestamp() - last_distribution_time) / 86400
            await process_virtual_daily_round(today, status, pending_totals, registrations, settings, day_ratio=pending_ratio)

        elif ddate > last_distribution_date:
            await process_virtual_daily_round(ddate, status, pending_totals, registrations, settings)
        
        # in all cases add to totals
        await process_virtual_daily_round(ddate, status, totals, registrations, settings)


    # we process the address clusters now
    await process_address_links()

    total_airdrop = sum(totals.values())
    pools['airdrop']['distributed'] = total_airdrop

    # we apply the modifier to the rewards before adding the linear allocs
    for address in pending_totals:
        reward_multiplier = await get_address_cluster_reward_multiplier(address, previous_mints, balances)
        pending_totals[address] *= reward_multiplier

    # first handle the linear allocs from the beginning
    linear_allocs = get_linear_allocs(settings, allocations, now, pools=pools)
    for address, value in linear_allocs.items():
        addr = w3.to_checksum_address(address)
        if addr not in totals:
            totals[addr] = 0
        totals[addr] += value

        if addr not in previous_mints:
            # first mint, let's give it it's linear alloc
            pending_totals[addr] = pending_totals.get(addr, 0) + value

    # now we handle them since last distribution for pendings
    linear_allocs = get_linear_allocs(settings, allocations, now, start_time=last_distribution_datetime)
    for address, value in linear_allocs.items():
        addr = w3.to_checksum_address(address)
        if addr not in pending_totals:
            pending_totals[addr] = 0

        if addr in previous_mints: # we didn't distribute it whole
            pending_totals[addr] += value

    instant_allocs = get_instant_allocs(allocations, pools)
    for address, value in instant_allocs.items():
        addr = w3.to_checksum_address(address)
        if addr not in totals:
            totals[addr] = 0
        totals[addr] += value

        if addr not in previous_mints:
            # first mint, let's give it it's instant alloc
            pending_totals[addr] = pending_totals.get(addr, 0) + value

    # let's create an estimate of rewards over the next 36 months based on just today if everyone stays the same
    estimates_totals = {}
    if today_status is not None:
        for i in range(365*3):
            day = (today_date + timedelta(days=i)).isoformat()
            await process_virtual_daily_round(day, today_status, estimates_totals, registrations, settings)
        # apply the reward multiplier
        for address in estimates_totals:
            reward_multiplier = await get_address_cluster_reward_multiplier(address, previous_mints, balances)
            estimates_totals[address] *= reward_multiplier

    # now add the linear allocs to the estimate totals
    estimates_date = (today_date + timedelta(days=365*3)).isoformat()
    linear_allocs = get_linear_allocs(settings, allocations, estimates_date)
    for address, value in linear_allocs.items():
        if address not in estimates_totals:
            estimates_totals[address] = 0
        estimates_totals[address] += value
    
    pprint.pprint({
        address: (value, address in all_bonus_addresses) for address, value in totals.items()
    })
    pprint.pprint({
        address: value for address, value in pending_totals.items()
    })

    # now let's print the count of addresses that have the bonus compared to the ones that don't
    bonus_count = len([address for address in totals if address in all_bonus_addresses])
    total_count = len(totals)
    print(f"Total addresses: {total_count}, bonus addresses: {bonus_count}, ratio: {bonus_count/total_count}")
    # now print the reward total
    print(f"Total rewards: {sum(totals.values())}")
    print(f"Total pending: {sum(pending_totals.values())}")
    
    info = {
        "ratio": ratio,
        "reward_start": settings['reward_start_ts'],
        "daily_decay": settings['daily_decay'],
        "total_rewards": sum(totals.values()),
        "boosted_addresses": all_bonus_addresses,
        "pools": pools
    }
    
    return totals, pending_totals, estimates_totals, info