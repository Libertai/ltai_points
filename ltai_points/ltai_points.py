"""Main module."""
from .fetcher import get_account_registrations, get_aleph_rewards, get_pending_rewards, get_staked_amounts
from datetime import datetime, timezone
import pprint

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

async def process_virtual_daily_round(round_date, staked_amounts, totals, registrations, settings):
    ratio = settings['staked_ratio']
    bonus_ratio = settings['bonus_ratio']
    reward_time = datetime.fromisoformat(round_date).replace(tzinfo=timezone.utc).timestamp()
    days_since_start = int(reward_time - settings['reward_start_ts']) / 86400
    stakers_daily_base = settings['aleph_reward_stakers_daily_base']
    nodes_daily_base = settings['aleph_reward_nodes_daily_base']
    daily_base = stakers_daily_base + nodes_daily_base
    decay = settings['daily_decay'] ** days_since_start
    daily_ltai = daily_base * decay * ratio

    total_staked = sum(staked_amounts.values())
    ltai_ratio = daily_ltai / total_staked

    distribution_bonus_ratio = 1
    bonus_addresses = [address for address, registration_time in registrations.items()
                        if registration_time < reward_time and registration_time < settings['bonus_limit_ts']]
    if reward_time < settings['bonus_limit_ts']:
        distribution_bonus_ratio = 1 + ((bonus_ratio-1) * (1 - min(1, days_since_start / settings['bonus_duration'])))
    
    for address, value in staked_amounts.items():
        if address not in totals:
            totals[address] = 0
        reward = value * ltai_ratio
        if address in bonus_addresses:
            reward *= distribution_bonus_ratio
        totals[address] += reward

    print(daily_ltai)
    print(round_date, sum(staked_amounts.values()))

async def compute_points(settings, dbs):
    ratio = settings['aleph_reward_ratio']
    bonus_ratio = settings['bonus_ratio']
    totals = {}

    registrations, counts = await get_account_registrations(settings)
    print(f"Found {len(registrations)} registrations")
    
    all_bonus_addresses = [address for address, registration_time in registrations.items()
                           if registration_time < settings['bonus_limit_ts']]
    
    for address in all_bonus_addresses:
        if address not in totals:
            totals[address] = 10
            
    pending_rewards, pending_time = await get_pending_rewards(settings)
    pending_totals = {}
    await process_round(pending_rewards, pending_time, pending_totals, registrations, settings)
    
    last_time = 0
    first_time = 0
    async for reward_round, reward_time in get_aleph_rewards(settings):
        if reward_time > last_time or last_time == 0:
            last_time = reward_time
        if reward_time < first_time or first_time == 0:
            first_time = reward_time
        await process_round(reward_round, reward_time, totals, registrations, settings)
        
    pending_date = datetime.fromtimestamp(pending_time, timezone.utc).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    today_staked_amounts = None
    async for ddate, staked_amounts in get_staked_amounts(settings, dbs):
        
        dtotals = totals
        if ddate >= pending_date:
            dtotals = pending_totals
            
            if ddate == today:
                today_staked_amounts = staked_amounts
                continue
            
        await process_virtual_daily_round(ddate, staked_amounts, totals, registrations, settings)

    # now we do a virtual pending based on last amounts for today
    # what part of the day as a ratio has passed ?
    # last_date is a string, let's get a timestamp at utc
    today_time = datetime.fromisoformat(today).replace(tzinfo=timezone.utc).timestamp()
    pending_ratio = (datetime.now(timezone.utc).timestamp() - today_time) / 86400
    day_pending_reward = {}
    await process_virtual_daily_round(today, today_staked_amounts, day_pending_reward, registrations, settings)
    day_pending_reward = {address: value * pending_ratio for address, value in day_pending_reward.items()}
    # now we merge this with the existing pending
    pending_totals = {address: value + day_pending_reward.get(address, 0) for address, value in pending_totals.items()}
    


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
        "first_time": first_time,
        "last_time": last_time,
        "pending_time": pending_time,
        "ratio": ratio,
        "reward_start": settings['reward_start_ts'],
        "daily_decay": settings['daily_decay'],
        "total_rewards": sum(totals.values()),
        "boosted_addresses": all_bonus_addresses,
    }
    
    return totals, pending_totals, info