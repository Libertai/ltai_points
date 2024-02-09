
from dotenv import load_dotenv
import os
load_dotenv()

def get_settings():
    return {
        'api_endpoint': os.environ.get('API_ENDPOINT', 'https://api2.aleph.im'),
        'aleph_reward_sender': os.environ.get('ALEPH_REWARD_SENDER', '0x3a5CC6aBd06B601f4654035d125F9DD2FC992C25'),
        'reward_start': int(os.environ.get('REWARD_START', 1704067200)),
        'ethereum_pkey': os.environ.get('ETHEREUM_PKEY'),
        'aleph_reward_ratio': float(os.environ.get('ALEPH_REWARD_RATIO', '0.1'))
    }