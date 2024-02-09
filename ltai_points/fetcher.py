import math
from aleph.sdk.client import AlephHttpClient
from aleph.sdk.query.filters import PostFilter
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


async def get_aleph_rewards(settings):
    ratio = settings['aleph_reward_ratio']
    
    async with AlephHttpClient() as client:
        posts = fetch_posts(client,
                            filter=PostFilter(channels=["FOUNDATION"], addresses=[settings['aleph_reward_sender']], tags=['distribution']))
        
        totals = {}
        
        async for post in posts:
            if post.time < settings['reward_start']:
                break
            
            has_success = False
            for target in post.content['targets']:
                if target['success']:
                    has_success = True
                    
            if not has_success:
                # unsuccessful distribution, ignore.
                continue
            
            for address, value in post.content['rewards'].items():
                if address not in totals:
                    totals[address] = 0
                totals[address] += value * ratio
                
            print(post.time)
        pprint.pprint(totals)
