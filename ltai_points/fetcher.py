import math
from datetime import datetime, timezone, date
from aleph.sdk.client import AlephHttpClient
from aleph.sdk.query.filters import PostFilter, MessageFilter
from aleph_message.models import MessageType
import pprint

import logging
LOGGER = logging.getLogger(__name__)

async def fetch_posts(client, filter, per_page=20):
    posts = await client.get_posts(
        post_filter=filter, 
        page_size=per_page
    )
    target_pages = math.ceil(posts.pagination_total / posts.pagination_per_page)
    
    for page in range(2, target_pages+1):
        
        for post in posts.posts:
            yield post
        
        LOGGER.debug(f"processing page {page}/{target_pages}")
        posts = await client.get_posts(
            post_filter=filter,
            page=page, 
            page_size=per_page
        )
    
    for post in posts.posts:
        yield post

async def fetch_messages(client, filter, per_page=20):
    messages = await client.get_messages(
        message_filter=filter, 
        page_size=per_page
    )
    target_pages = math.ceil(messages.pagination_total / messages.pagination_per_page)
    print(messages.pagination_total, messages.pagination_per_page, target_pages)
    if target_pages > 1:
        for page in range(2, target_pages+1):
            
            for message in messages.messages:
                yield message
            
            LOGGER.debug(f"processing page {page}/{target_pages}")
            messages = await client.get_messages(
                message_filter=filter,
                page=page, 
                page_size=per_page
            )

            print('page', page, '/', target_pages)
    
    for message in messages.messages:
        yield message

async def fetch_sampled_messages(client, filter, per_day=12, splits=4):
    # we get the stat_date of the filter
    start_date = filter.start_date
    now = datetime.now(timezone.utc).timestamp()
    # we get the number of days between the start and now
    days = (now - start_date) / 86400
    # we get the first batch to get the pagination info
    messages = await client.get_messages(
        message_filter=filter, 
        page_size=per_day
    )

    per_day = int(per_day / splits)

    # we get the number of messages per day
    messages_per_day = messages.pagination_total / days

    # we get the number of pages total
    target_pages = math.ceil(messages.pagination_total / per_day)
    last_date = None

    if target_pages > 1:
        for page in range(2, target_pages+1):
            # should we skip this page as we already got something that day?
            # we process twice per day anyway, just in case
            if page % (int(messages_per_day/per_day)/splits):
                continue

            for message in messages.messages:
                if message.time.date() == last_date:
                    continue

                yield message
                last_date = message.time.date()
                print(message.time.date())

            messages = await client.get_messages(
                message_filter=filter,
                page=page, 
                page_size=per_day
            )
            print('page', page, '/', target_pages)

    for message in messages.messages:
        if message.time.date() == last_date:
            continue

        yield message
        last_date = message.time.date()

    

    target_pages = math.ceil(messages.pagination_total / messages.pagination_per_page)
    # we get the total number of messages
    total_messages = messages.pagination_total
    # we get the number of messages to get
    messages_to_get = int(messages_per_day * days)


async def get_pending_rewards(settings):
    # we only get one post, the last one
    async with AlephHttpClient() as client:
        posts = await client.get_posts(
            post_filter=PostFilter(channels=["FOUNDATION"],
                                   addresses=[settings['aleph_calculation_sender']],
                                   tags=['calculation'],
                                   types=['staking-rewards-distribution']),
            page_size=1
        )
        return posts.posts[0].content['rewards'], posts.posts[0].time
    
async def get_staked_amounts(settings, dbs):
    staked_db = dbs['staked_amounts']
    last_date = await staked_db.get_last_available_key()
    print(last_date)
    if last_date is None:
        last_date = settings['reward_start_ts']
    else:
        last_date = datetime.fromisoformat(last_date).timestamp()
        print(last_date)

    seen_dates = set()

    async for key, values in staked_db.retrieve_entries():
        yield key, values
        seen_dates.add(key)

    async with AlephHttpClient() as client:
        messages = fetch_sampled_messages(client,
                                  filter=MessageFilter(channels=["FOUNDATION"],
                                                       message_types=[MessageType.aggregate],
                                                       addresses=[settings['aleph_corechannel_sender']],
                                                       start_date=float(last_date)),
                                  per_day=10)
        
        async for message in messages:
            if message.content.key == "corechannel":
                message_totals = {}
                message_date = message.time.date().isoformat()
                if message_date in seen_dates:
                    continue

                for node in message.content.content['nodes']:
                    node_address = node.get('reward_address', node['owner'])
                    message_totals[node_address] = message_totals.get(node_address, 0) + 200000
                    for address, amount in node['stakers'].items():
                        message_totals[address] = message_totals.get(address, 0) + amount

                yield (message_date, message_totals)
                await staked_db.store_entry(message_date, message_totals)

async def get_aleph_rewards(settings):
    async with AlephHttpClient() as client:
        posts = fetch_posts(client,
                            filter=PostFilter(channels=["FOUNDATION"],
                                              addresses=[settings['aleph_reward_sender']],
                                              tags=['distribution'],
                                              types=['staking-rewards-distribution']),
                            per_page=50)
        
        async for post in posts:
            if 'mainnet' not in post.content['tags']:
                continue
            
            if post.time < settings['reward_start_ts']:
                break
            
            has_success = False
            for target in post.content['targets']:
                if target['success']:
                    has_success = True
                    
            if not has_success:
                # unsuccessful distribution, ignore.
                continue

            yield post.content['rewards'], post.time

# we are searching for the first message of the user in the channel
async def get_account_registrations(settings):
    registrations = {}
    counts = {}
    async with AlephHttpClient() as client:
        messages = fetch_messages(client,
                                  filter=MessageFilter(channels=["LIBERTAI"],
                                                       message_types=[MessageType.aggregate],
                                                       end_date=settings['bonus_limit_ts']),
                                  per_page=1000)
        
        async for message in messages:
            if message.content.key == "libertai" and message.content.content.get('registered', False):
                if message.sender not in registrations:
                    registrations[message.sender] = message.time.timestamp()
                    counts[message.sender] = 1
                else:
                    # check if the message date is before the current registration date
                    if message.time.timestamp() < registrations[message.sender]:
                        registrations[message.sender] = message.time.timestamp()
                    counts[message.sender] += 1

                print(f"user {message.sender} registered at {message.time}")
    return registrations, counts