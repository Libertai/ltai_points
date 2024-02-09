from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import (
    AliasChoices,
    AmqpDsn,
    BaseModel,
    Field,
    ImportString,
    PostgresDsn,
    RedisDsn,
)

class Settings(BaseSettings):

    api_endpoint: str = Field(alias='api_endpoint', default='https://api2.aleph.im')  
    aleph_reward_sender: str = Field(alias='aleph_reward_sender', default='0x3a5CC6aBd06B601f4654035d125F9DD2FC992C25')
    

    model_config = SettingsConfigDict(env_prefix='ltai_points_', env_file='.env', env_file_encoding='utf-8')
