
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

load_dotenv()

def get_settings():
    return {
        'api_endpoint': os.environ.get('API_ENDPOINT', 'https://api2.aleph.im'),
        'aleph_reward_sender': os.environ.get('ALEPH_REWARD_SENDER', '0x3a5CC6aBd06B601f4654035d125F9DD2FC992C25'),
        'aleph_calculation_sender': os.environ.get('ALEPH_CALCULATION_SENDER', '0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10'),
        'aleph_corechannel_sender': os.environ.get('ALEPH_CORECHANNEL_SENDER', '0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10'),
        'aleph_node_max_paid': int(os.environ.get('ALEPH_NODE_MAX_PAID', '5')),
        'aleph_reward_resource_node_monthly_base': int(os.environ.get('ALEPH_REWARD_RESOURCE_NODE_MONTHLY_BASE', '250')),
        'aleph_reward_resource_node_monthly_variable': int(os.environ.get('ALEPH_REWARD_RESOURCE_NODE_MONTHLY_VARIABLE', '1250')),
        'reward_start_ts': float(os.environ.get('REWARD_START', 1704067200)),
        'tge_ts': float(os.environ.get('RAISE_START', 1718712000)),
        'aleph_reward_stakers_daily_base': 15000,
        'aleph_reward_nodes_daily_base': 15000,
        'ethereum_pkey': os.environ.get('ETHEREUM_PKEY'),
        'ethereum_api_server': os.environ.get('ETHEREUM_API_SERVER', 'https://base-rpc.publicnode.com'),
        'ethereum_chain_id': int(os.environ.get('ETHEREUM_CHAIN_ID', '8453')),
        'ethereum_min_height': int(os.environ.get('ETHEREUM_MIN_HEIGHT', '15961530')),
        'ethereum_token_contract': os.environ.get('ETHEREUM_TOKEN_CONTRACT', '0xF8B1b47AA748F5C7b5D0e80C726a843913EB573a'),
        'ethereum_batch_size': int(os.environ.get('ETHEREUM_BATCH_SIZE', '400')),
        'aleph_reward_ratio': float(os.environ.get('ALEPH_REWARD_RATIO', '0.35')),
        'daily_decay': float(os.environ.get('DAILY_DECAY', '0.99722')),
        'bonus_ratio': float(os.environ.get('BONUS_RATIO', '1.5')),
        'bonus_duration': int(os.environ.get('BONUS_DURATION', '365')),  # duration of the bonus in days
        'staked_ratio': float(os.environ.get('STAKED_RATIO', '0.7')),
        # limit date to register for the bonus '2024-02-26 12:00:00'
        'bonus_limit_ts': datetime.fromisoformat(os.environ.get('BONUS_LIMIT_DATE', '2024-02-26 12:00:00').replace('Z', '+00:00')).replace(tzinfo=timezone.utc).timestamp(),
        'channel': os.environ.get('CHANNEL', 'LIBERTAI'),
        'tag': os.environ.get('TAG', 'mainnet'),
        'post_type': os.environ.get('POST_TYPE', 'calculation'),
        'aggregate_key': os.environ.get('AGGREGATE_KEY', 'tokens'),
        'pending_aggregate_key': os.environ.get('PENDING_AGGREGATE_KEY', 'pending_tokens'),
        'estimated_aggregate_key': os.environ.get('ESTIMATED_AGGREGATE_KEY', 'estimated_3yr_tokens'),
        'db_path': os.environ.get('DB_PATH', './database'),
        'bonus_addresses': os.environ.get('BONUS_ADDRESSES', '').split(','),  # list of addresses to receive the bonus,
        'supply_filename': os.environ.get('SUPPLY_FILENAME', 'supply.yaml'),
    }