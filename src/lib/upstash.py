from src.config.env import UPSTASH_TOKEN, UPSTASH_URL
from upstash_vector import Index

index = Index(
    url=UPSTASH_URL,
    token=UPSTASH_TOKEN
)
