import math
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
    
    for message in messages.messages:
        yield message

async def get_aleph_rewards(settings):
    
    async with AlephHttpClient() as client:
        posts = fetch_posts(client,
                            filter=PostFilter(channels=["FOUNDATION"], addresses=[settings['aleph_reward_sender']], tags=['distribution']))
        
        async for post in posts:
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
                                  filter=MessageFilter(channels=["LIBERTAI"], message_types=[MessageType.aggregate]),
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