
from .ethereum import get_account

from aleph.sdk.client import AuthenticatedAlephHttpClient

# async def post_state(settings, points):
#     account = get_account(settings)
#     async with AuthenticatedAlephHttpClient(account, api_server=settings['api_endpoint']) as client:
#         message, status = await client.create_post(
#             {
#                 "tags": ['calculation', settings['tag']],
#                 "points": points,
#             },
#             post_type=settings['post_type'],
#             channel=settings['channel'],
#         )
#         print(status, message)
        
async def post_state(settings, points, boosted_addresses):
    account = get_account(settings)
    async with AuthenticatedAlephHttpClient(account, api_server=settings['api_endpoint']) as client:
        message, status = await client.create_aggregate(
            settings['aggregate_key'],
            points,
            channel=settings['channel'],
        )
        print(status, message)
        message, status = await client.create_aggregate(
            'info',
            {
                "boosted_addresses": boosted_addresses,
            },
            channel=settings['channel'],
        )
        print(status, message)