"""Main module."""
from .fetcher import get_account_registrations, get_aleph_rewards
import pprint


async def compute_points(settings):
    ratio = settings['aleph_reward_ratio']
    bonus_ratio = settings['bonus_ratio']
    totals = {}

    registrations, counts = await get_account_registrations(settings)

    async for reward_round, reward_time in get_aleph_rewards(settings):
        decay = settings['daily_decay'] ** ((reward_time - settings['reward_start_ts']) / 86400)
        distribution_ratio = decay * ratio

        # now check which addresses should have the bonus for this round (only if they registered before the bonus limit, and before this distribution)
        bonus_addresses = [address for address, registration_time in registrations.items()
                           if registration_time < reward_time and registration_time < settings['bonus_limit_ts']]
        
        for address, value in reward_round.items():
            if address not in totals:
                totals[address] = 0
            reward = value * distribution_ratio
            if address in bonus_addresses:
                reward *= bonus_ratio

            totals[address] += reward

    all_bonus_addresses = [address for address, registration_time in registrations.items()
                           if registration_time < settings['bonus_limit_ts']]

    pprint.pprint({
        address: (value, address in all_bonus_addresses) for address, value in totals.items()
    })

    # now let's print the count of addresses that have the bonus compared to the ones that don't
    bonus_count = len([address for address in totals if address in all_bonus_addresses])
    total_count = len(totals)
    print(f"Total addresses: {total_count}, bonus addresses: {bonus_count}, ratio: {bonus_count/total_count}")