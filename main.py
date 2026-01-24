import yaml
import logging
from bot.utils.logger import logger

from bot.core.browser import Browser
from bot.core.session import Session
from bot.application.workflow import Workflow
from bot.discovery.search import Search
from bot.core.execution_guard import ExecutionGuard
from bot.core.dry_run import DryRun
from bot.core.metrics import Metrics
import atexit
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == '__main__':
    with open("config.yaml", 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    # Get credentials from environment variables
    username = os.getenv('LINKEDIN_USERNAME', parameters.get('username'))
    password = os.getenv('LINKEDIN_PASSWORD', parameters.get('password'))
    phone_number = os.getenv('PHONE_NUMBER', parameters.get('phone_number'))

    # Validate parameters
    assert len(parameters['positions']) > 0, "At least one position must be specified"
    assert len(parameters['locations']) > 0, "At least one location must be specified"
    assert username is not None, "Username must be provided"
    assert password is not None, "Password must be provided"
    assert phone_number is not None, "Phone number must be provided"

    uploads = parameters.get('uploads', {})
    blacklist = parameters.get('blacklist', [])
    blacklist_titles = parameters.get('blackListTitles', [])
    experience_level = parameters.get('experience_level', [])
    
    # Execution Guard & Dry Run Configuration
    execution_config = parameters.get('execution', {})
    max_apps = execution_config.get('max_applications_per_run', 10)
    cooldown = execution_config.get('cooldown_seconds', 90)
    is_dry_run = execution_config.get('dry_run', True)

    logger.info("Starting Easy Apply Bot (Playwright Version)", step="init")
    
    execution_guard = ExecutionGuard(max_apps, cooldown)
    dry_run = DryRun(is_dry_run)
    metrics = Metrics()
    
    # Register summary on exit
    atexit.register(metrics.print_summary)

    # Initialize Core Components
    profile_path = parameters.get('profile_path', '')
    browser = Browser(profile_path=profile_path if profile_path else None)
    page = browser.get_page()
    
    # Login
    session = Session(page)
    session.login(username, password)

    # Application & Search Components
    workflow = Workflow(page, uploads, blacklist_titles, 
                       execution_guard=execution_guard, dry_run=dry_run, metrics=metrics)
    
    search = Search(page, workflow, blacklist, experience_level, phone_number)
    
    locations = [l for l in parameters['locations'] if l is not None]
    positions = [p for p in parameters['positions'] if p is not None]

    try:
        search.start_apply(positions, locations)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user", step="shutdown", event="keyboard_interrupt")
    except Exception as e:
        logger.error(f"Bot encountered an error: {e}", step="shutdown", event="error", exception=e)
    finally:
        logger.info("Closing browser...", step="shutdown", event="cleanup")
        browser.close()
        logger.info("Bot shutdown complete", step="shutdown", event="complete")
