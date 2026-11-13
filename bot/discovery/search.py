import time
import random
import logging
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlencode, urlparse

from bot.application.workflow import Workflow
from bot.utils.delays import sleep_random
from bot.utils.selectors import LOCATORS, get_locator
from bot.utils.logger import logger
from bot.utils.retry import retry
from bot.utils.stale_guard import safe_action
from bot.discovery.job_identity import JobIdentity
from bot.discovery.scroll_tracker import ScrollTracker
from bot.utils.human_interaction import HumanInteraction
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


class Search:
    def __init__(self, page: Page, workflow: Workflow, blacklist=None, experience_level=None, phone_number=None):
        self.page = page
        self.workflow = workflow
        self.blacklist = blacklist or []
        self.experience_level = experience_level or []
        self.locator = LOCATORS
        self.MAX_SEARCH_TIME = 60 * 60
        self.phone_number = phone_number

    def start_apply(self, positions, locations):
        combos = []
        while len(combos) < len(positions) * len(locations):
            position = positions[random.randint(0, len(positions) - 1)]
            location = locations[random.randint(0, len(locations) - 1)]
            combo = (position, location)
            if combo not in combos:
                combos.append(combo)
                logger.info(f"Applying to {position}: {location}", step="search_init")
                if self.applications_loop(position, location) is False:
                    return
            if len(combos) > 500:
                break

    def applications_loop(self, position, location):
        start_offset = 0
        start_time = time.time()
        scroll_tracker = ScrollTracker(self.page)
        human = HumanInteraction(self.page)
        last_fallback_job_id = None
        repeated_fallback_job_count = 0

        logger.info("Looking for jobs.. Please wait..", step="job_search", event="start")

        self.next_jobs_page(position, location, start_offset)
        logger.info("Looking for jobs.. Please wait..", step="job_search", event="page_loaded")

        while time.time() - start_time < self.MAX_SEARCH_TIME:
            try:
                logger.info(f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search", 
                           step="job_search", event="timer")
                sleep_random(0.5, 1.0)

                # Check if search results container is present
                search_selector = get_locator("search")
                if self.is_present(search_selector):
                    scrollresults = self.page.locator(search_selector).first
                    
                    # Get current scroll height
                    current_height = scrollresults.evaluate("el => el.scrollHeight")
                    
                    # Scroll down with human-like behavior
                    for i in range(300, int(current_height), 300):
                        scrollresults.evaluate(f"el => el.scrollTo(0, {i})")
                        time.sleep(random.uniform(0.1, 0.3))

                    if not scroll_tracker.update_scroll(current_height):
                        if scroll_tracker.should_stop():
                            logger.warning("Scroll limits reached, moving to next page", step="job_search", event="scroll_stop")
                            start_offset += 25
                            self.next_jobs_page(position, location, start_offset)
                            continue
                
                
                # Extract jobs
                links_selector = get_locator("links")
                logger.debug(f"Using job card selector: {links_selector}", step="job_search")

                if not self.is_present(links_selector):
                    fallback_selector = get_locator("links", use_fallback=True)
                    if fallback_selector:
                        logger.warning(
                            f"No cards with primary selector, trying fallback: {fallback_selector}",
                            step="job_search",
                        )
                        links_selector = fallback_selector
                
                if self.is_present(links_selector):
                    # Wait a bit for job cards to fully load
                    time.sleep(random.uniform(1, 2))
                    
                    links = self.page.locator(links_selector).all()
                    logger.info(f"Found {len(links)} job cards on page", step="job_search", event="cards_found")
                    
                    if len(links) == 0:
                        # Try fallback selector
                        fallback_selector = get_locator("links", use_fallback=True)
                        logger.warning(f"No cards with primary selector, trying fallback: {fallback_selector}", step="job_search")
                        if fallback_selector:
                            links = self.page.locator(fallback_selector).all()
                            logger.info(f"Fallback found {len(links)} job cards", step="job_search", event="cards_found_fallback")
                    
                    page_job_ids = set()
                    for i, link in enumerate(links):
                        try:
                            # Check if element is visible before processing
                            if not link.is_visible():
                                continue
                            
                            try:
                                link_text = link.text_content(timeout=3000) or ""
                            except Exception:
                                link_text = ""

                            job_id = JobIdentity.extract_job_id(link)
                            clicked_for_preview = False
                            if not job_id and "Easy Apply" in link_text:
                                try:
                                    link.click(timeout=5000, force=False)
                                    clicked_for_preview = True
                                    time.sleep(1.5)
                                    selected_job_ids = parse_qs(urlparse(self.page.url).query).get("currentJobId", [])
                                    selected_job_id = selected_job_ids[0] if selected_job_ids else None
                                    if selected_job_id and selected_job_id.isdigit():
                                        job_id = selected_job_id
                                except Exception as click_err:
                                    logger.warning(
                                        f"Could not select Easy Apply result {i}: {click_err}",
                                        step="job_search",
                                        event="card_error",
                                    )

                            if job_id:
                                page_job_ids.add(job_id)
                            if job_id and not scroll_tracker.is_processed(job_id):
                                if 'Applied' not in link_text:
                                    if link_text not in self.blacklist:
                                        logger.info(f"Found new job: {job_id}", step="job_search", event="found_job")
                                        
                                        # CRITICAL: Click the job card to show preview panel
                                        # Don't click the title link, click the card container
                                        try:
                                            # Click on the job card div, NOT the title link
                                            # This shows the preview panel with Easy Apply button
                                            if not clicked_for_preview:
                                                link.click(timeout=5000, force=False)
                                                time.sleep(1.5)  # Wait for preview panel to load
                                            logger.debug(f"Selected job card {job_id} for preview", step="job_search")
                                        except Exception as click_err:
                                            logger.warning(f"Could not click job card: {click_err}", step="job_search")
                                        
                                        applied = self.workflow.apply_to_job(job_id, self.phone_number)
                                        scroll_tracker.add_job(job_id)
                                        if not applied and self.workflow.application_needs_review:
                                            logger.warning(
                                                "Stopping search because the current Easy Apply form needs review; "
                                                "leaving it open without saving or discarding.",
                                                job_id=job_id,
                                                step="job_search",
                                                event="application_left_open",
                                            )
                                            return False
                                        if applied:
                                            logger.info(
                                                "Application confirmed; continuing through the current search results.",
                                                job_id=job_id,
                                                step="job_search",
                                                event="application_success_continue_search",
                                            )
                                    else:
                                        logger.info(f"Skipping blacklisted job: {job_id}", step="job_search", event="blacklisted")
                                        scroll_tracker.add_job(job_id)  # Blacklisted but processed
                                else:
                                    logger.debug(f"Already applied to job: {job_id}", step="job_search", event="already_applied")
                                    scroll_tracker.add_job(job_id)  # Already applied
                            elif job_id:
                                logger.debug(f"Job {job_id} already processed", step="job_search", event="duplicate")
                        except Exception as e:
                            logger.warning(f"Error processing job card {i}: {e}", step="job_search", event="card_error")
                            continue
                    
                    if page_job_ids and all(
                        scroll_tracker.is_processed(job_id) for job_id in page_job_ids
                    ):
                        logger.info(
                            "All visible jobs on this results page were already handled; loading the next results page.",
                            step="job_search",
                            event="page_jobs_exhausted",
                        )
                        start_offset += 25
                        self.next_jobs_page(position, location, start_offset)
                        continue

                    if scroll_tracker.should_stop():
                        start_offset += 25
                        self.next_jobs_page(position, location, start_offset)

                else:
                    logger.warning(f"No job cards found with selector: {links_selector}", step="job_search", event="no_cards")
                    self._log_results_markup(search_selector)
                    selected_job_ids = parse_qs(urlparse(self.page.url).query).get("currentJobId", [])
                    selected_job_id = selected_job_ids[0] if selected_job_ids else None
                    if selected_job_id and selected_job_id.isdigit():
                        if selected_job_id == last_fallback_job_id:
                            repeated_fallback_job_count += 1
                        else:
                            last_fallback_job_id = selected_job_id
                            repeated_fallback_job_count = 0
                        if repeated_fallback_job_count >= 3:
                            logger.warning(
                                "LinkedIn returned the same selected job for four consecutive result offsets; "
                                "stopping this search because the offset was not advancing.",
                                job_id=selected_job_id,
                                step="job_search",
                                event="result_offset_stalled",
                            )
                            return

                        logger.info(
                            f"No card wrapper found; trying selected job {selected_job_id} at result offset {start_offset}",
                            job_id=selected_job_id,
                            step="job_search",
                            event="selected_job_fallback",
                        )
                        if not scroll_tracker.is_processed(selected_job_id):
                            applied = self.workflow.apply_to_job(selected_job_id, self.phone_number)
                            scroll_tracker.add_job(selected_job_id)
                            if not applied and self.workflow.application_needs_review:
                                logger.warning(
                                    "Stopping search because the current Easy Apply form needs review; "
                                    "leaving it open without saving or discarding.",
                                    job_id=selected_job_id,
                                    step="job_search",
                                    event="application_left_open",
                                )
                                return False
                            if applied:
                                logger.info(
                                    "Application confirmed; checking the next result offset for the current search.",
                                    job_id=selected_job_id,
                                    step="job_search",
                                    event="application_success_continue_search",
                                )
                            else:
                                logger.info(
                                    "Selected job had no confirmed application; checking the next result offset.",
                                    job_id=selected_job_id,
                                    step="job_search",
                                    event="selected_job_skipped_continue_search",
                                )
                        start_offset += 1
                        self.next_jobs_page(position, location, start_offset)
                        scroll_tracker.reset()
                        continue

                    try:
                        job_links = self.page.locator("a[href*='/jobs/view/']").count()
                        logger.warning(
                            f"No supported job cards found at {self.page.url}; "
                            f"job-detail links detected: {job_links}. Stopping this search instead of paging repeatedly.",
                            step="job_search",
                            event="search_markup_unrecognized",
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not inspect job links ({e}); stopping this search instead of paging repeatedly.",
                            step="job_search",
                            event="search_markup_unrecognized",
                        )
                    return

            except Exception as e:
                logger.error(f"Search loop error: {e}", step="job_search", event="error", exception=e)
                break

    def _log_results_markup(self, search_selector):
        try:
            search_selectors = [
                selector
                for selector in (
                    search_selector,
                    get_locator("search", use_fallback=True),
                )
                if selector
            ]
            sample = self.page.evaluate(
                """selectors => {
                    const summarize = element => ({
                        tag: element.tagName.toLowerCase(),
                        className: typeof element.className === 'string' ? element.className.slice(0, 160) : '',
                        role: element.getAttribute('role'),
                        viewName: element.getAttribute('data-view-name'),
                        jobId: element.getAttribute('data-job-id')
                            || element.getAttribute('data-occludable-job-id')
                            || element.getAttribute('data-entity-urn'),
                        href: element.getAttribute('href'),
                        text: (element.innerText || element.textContent || '')
                            .replace(/\\s+/g, ' ').trim().slice(0, 140)
                    });
                    let root = null;
                    let matchedSelector = null;
                    for (const selector of selectors) {
                        try {
                            root = document.querySelector(selector);
                            if (root) {
                                matchedSelector = selector;
                                break;
                            }
                        } catch (error) {
                            continue;
                        }
                    }
                    const scope = root || document.body;
                    const descendants = Array.from(scope.querySelectorAll(
                        ':scope > *, :scope > * > *, :scope > * > * > *'
                    )).filter(element => (element.innerText || '').trim().length > 0).slice(0, 18);
                    const anchors = Array.from(scope.querySelectorAll('a')).slice(0, 18);
                    const marked = Array.from(scope.querySelectorAll(
                        '[data-job-id], [data-occludable-job-id], [data-entity-urn], [data-view-name], [role="listitem"]'
                    )).slice(0, 18);
                    return {
                        matchedSelector: matchedSelector,
                        container: root ? summarize(root) : null,
                        descendants: descendants.map(summarize),
                        anchors: anchors.map(summarize),
                        marked: marked.map(summarize)
                    };
                }""",
                search_selectors,
            )
            logger.warning(
                f"Job results DOM sample: {sample}",
                step="job_search",
                event="results_dom_sample",
            )
        except Exception as e:
            logger.warning(
                f"Could not inspect job results markup: {e}",
                step="job_search",
                event="results_dom_sample_failed",
            )

    @retry(max_attempts=3, delay=1)
    def next_jobs_page(self, position, location, start_offset):
        params = {
            "f_AL": "true",
            "keywords": position,
            "location": location,
            "start": str(start_offset),
        }
        if self.experience_level:
            params["f_E"] = ",".join(map(str, self.experience_level))
        url = "https://www.linkedin.com/jobs/search/?" + urlencode(params)
        
        logger.info(
            f"Loading jobs at result offset {start_offset}: {url[:100]}...",
            step="next_jobs_page",
        )
        self.page.goto(url, wait_until="domcontentloaded")
        self.load_page()
        return start_offset + 25

    def load_page(self, sleep=1):
        """
        Wait for initial navigation to settle before inspecting the job results.
        """
        self.page.locator("body").wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(max(0, int(sleep * 1000)))
        return BeautifulSoup(self.page.content(), "lxml")

    def get_elements(self, type) -> list:
        """
        Get elements by type from locators
        """
        selector = get_locator(type)
        if selector and self.is_present(selector):
            return self.page.locator(selector).all()
        return []

    def is_present(self, selector):
        """
        Check if element is present on page
        """
        try:
            return self.page.locator(selector).count() > 0
        except:
            return False
