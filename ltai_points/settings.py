
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

load_dotenv()

def get_settings():
    return {
        'api_endpoint': os.environ.get('API_ENDPOINT', 'https://api2.aleph.im'),
        'aleph_reward_sender': os.environ.get('ALEPH_REWARD_SENDER', '0x3a5CC6aBd06B601f4654035d125F9DD2FC992C25'),
        'reward_start_ts': int(os.environ.get('REWARD_START', 1704067200)),
        'ethereum_pkey': os.environ.get('ETHEREUM_PKEY'),
        'aleph_reward_ratio': float(os.environ.get('ALEPH_REWARD_RATIO', '1.0')),
        'daily_decay': float(os.environ.get('DAILY_DECAY', '0.9966')),
        'bonus_ratio': float(os.environ.get('BONUS_RATIO', '1.5')),
        # limit date to register for the bonus '2024-02-26 12:00:00'
        'bonus_limit_ts': datetime.fromisoformat(os.environ.get('BONUS_LIMIT_DATE', '2024-02-26 12:00:00').replace('Z', '+00:00')).replace(tzinfo=timezone.utc).timestamp(),
        'channel': os.environ.get('CHANNEL', 'LIBERTAI'),
        'tag': os.environ.get('TAG', 'mainnet'),
        'post_type': os.environ.get('POST_TYPE', 'calculation'),
    }