"""
Configuration for API quota management.
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class QuotaConfig:
    """Configuration for different API quota tiers."""
    
    # Free tier limits (default)
    FREE_TIER = {
        "requests_per_minute": 15,
        "requests_per_day": 1500,
        "tokens_per_minute": 32000,
        "max_wait_time": 300,  # 5 minutes max wait
        "retry_attempts": 3
    }
    
    # Paid tier limits (for future upgrade)
    PAID_TIER = {
        "requests_per_minute": 300,
        "requests_per_day": 50000,
        "tokens_per_minute": 4000000,
        "max_wait_time": 60,   # 1 minute max wait
        "retry_attempts": 5
    }
    
    @classmethod
    def get_config(cls, tier: str = "free") -> Dict[str, Any]:
        """Get configuration for specified tier."""
        if tier.lower() == "paid":
            return cls.PAID_TIER.copy()
        return cls.FREE_TIER.copy()
    
    @classmethod
    def get_conservative_config(cls) -> Dict[str, Any]:
        """Get conservative configuration to avoid quota issues."""
        config = cls.FREE_TIER.copy()
        # Use more conservative limits to avoid hitting quota
        config.update({
            "requests_per_minute": 10,  # Reduced from 15
            "tokens_per_minute": 25000,  # Reduced from 32000
            "retry_attempts": 2  # Reduced retries
        })
        return config

# Rate limiting strategies
PROCESSING_STRATEGIES = {
    "batch": {
        "description": "Process videos in batches with delays",
        "frames_per_batch": 5,
        "delay_between_batches": 60,  # seconds
        "max_concurrent_requests": 2
    },
    "conservative": {
        "description": "Conservative processing to minimize quota usage",
        "frames_per_batch": 3,
        "delay_between_batches": 90,  # seconds
        "max_concurrent_requests": 1,
        "skip_visual_analysis": False,
        "reduce_prompt_complexity": True
    },
    "emergency": {
        "description": "Emergency mode when quota is critically low",
        "frames_per_batch": 1,
        "delay_between_batches": 120,  # seconds
        "max_concurrent_requests": 1,
        "skip_visual_analysis": True,
        "use_fallback_responses": True
    }
}

def get_processing_strategy(quota_usage_percent: float) -> Dict[str, Any]:
    """Get appropriate processing strategy based on quota usage."""
    if quota_usage_percent > 90:
        return PROCESSING_STRATEGIES["emergency"]
    elif quota_usage_percent > 70:
        return PROCESSING_STRATEGIES["conservative"]
    else:
        return PROCESSING_STRATEGIES["batch"]

def get_daily_processing_strategy(daily_usage_percent: float) -> Dict[str, Any]:
    """Get processing strategy based on daily usage percentage."""
    
    if daily_usage_percent < 50:
        return {
            "description": "Conservative processing",
            "frames_per_batch": 5,
            "delay_between_batches": 10,
            "skip_visual_analysis": False
        }
    elif daily_usage_percent < 80:
        return {
            "description": "Batch processing",
            "frames_per_batch": 3,
            "delay_between_batches": 30,
            "skip_visual_analysis": False
        }
    else:
        return {
            "description": "Emergency mode",
            "frames_per_batch": 1,
            "delay_between_batches": 60,
            "skip_visual_analysis": True
        }
