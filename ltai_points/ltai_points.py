"""Main module."""
from .fetcher import get_account_registrations, get_aleph_rewards
import pprint


async def compute_points(settings):
    ratio = settings['aleph_reward_ratio']
    bonus_ratio = settings['bonus_ratio']
    totals = {}

    registrations, counts = await get_account_registrations(settings)
    
    all_bonus_addresses = [address for address, registration_time in registrations.items()
                           if registration_time < settings['bonus_limit_ts']]
    
    for address in all_bonus_addresses:
        if address not in totals:
            totals[address] = 10

    async for reward_round, reward_time in get_aleph_rewards(settings):
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

    

    pprint.pprint({
        address: (value, address in all_bonus_addresses) for address, value in totals.items()
    })

    # now let's print the count of addresses that have the bonus compared to the ones that don't
    bonus_count = len([address for address in totals if address in all_bonus_addresses])
    total_count = len(totals)
    print(f"Total addresses: {total_count}, bonus addresses: {bonus_count}, ratio: {bonus_count/total_count}")
    # now print the reward total
    print(f"Total rewards: {sum(totals.values())}")
    
    return totals, all_bonus_addresses