# This file re-exports functions from role_channel_utils for backward compatibility

from utils.role_channel_utils import (
    is_role_at_top, 
    send_role_position_warning, 
    send_role_setup_error,
    disable_optional_cogs
)

# Re-export these functions to maintain compatibility
__all__ = ["is_role_at_top", "send_role_position_warning", "send_role_setup_error", "disable_optional_cogs"]
