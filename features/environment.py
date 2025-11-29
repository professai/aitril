"""
Behave environment configuration for AiTril BDD tests
"""
import asyncio
import os
from pathlib import Path


def before_all(context):
    """Set up before all tests"""
    # Create event loop for async operations
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)

    # Initialize unified settings from environment variables
    # Tests use environment variables, ensuring settings.json is created
    from aitril.settings import Settings
    from aitril.cache import SessionCache

    context.settings = Settings()
    context.cache = SessionCache(session_name='test')

    # Store original settings path for cleanup
    context.test_settings_dir = Path.home() / '.aitril'


def after_all(context):
    """Clean up after all tests"""
    # Close event loop
    if hasattr(context, 'loop'):
        context.loop.close()

    # Clean up test session from cache
    if hasattr(context, 'cache'):
        try:
            context.cache.clear_session('test')
        except:
            pass


def before_scenario(context, scenario):
    """Set up before each scenario"""
    context.received_events = []
    context.websocket = None


def after_scenario(context, scenario):
    """Clean up after each scenario"""
    # Close WebSocket if open
    if hasattr(context, 'ws') and context.ws:
        try:
            asyncio.get_event_loop().run_until_complete(context.ws.close())
        except:
            pass
