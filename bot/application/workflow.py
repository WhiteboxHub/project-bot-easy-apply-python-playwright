import os
import time
import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from bot.application.form_filler import FormFiller
from bot.persistence.store import Store
from bot.utils.selectors import LOCATORS, get_locator
from bot.utils.logger import logger
from bot.utils.retry import retry
from bot.utils.human_interaction import HumanInteraction


class Workflow:
    def __init__(self, page: Page, uploads, blacklist_titles=None, execution_guard=None, dry_run=None, metrics=None):
        self.page = page
        self.uploads = uploads
        self.blacklist_titles = blacklist_titles or []
        self.store = Store()
        self.form_filler = FormFiller(self.page)
        self.locator = LOCATORS
        self.execution_guard = execution_guard
        self.dry_run = dry_run
        self.human = HumanInteraction(self.page)
        self.metrics = metrics

    def apply_to_job(self, jobID, phone_number):
        if self.metrics:
            self.metrics.increment("attempted")

        if self.execution_guard and not self.execution_guard.can_apply():
            if self.metrics:
                self.metrics.increment("skipped")
            return False

        self.get_job_page(jobID)
        time.sleep(1)

        button = self.get_easy_apply_button()

        if button is not False:
            if any(word in self.page.title() for word in self.blacklist_titles):
                logger.info('Skipping this application, a blacklisted keyword was found in the job position', 
                           job_id=jobID, step="apply", event="blacklist")
                string_easy = "* Contains blacklisted keyword"
                result = False
            else:
                string_easy = "* has Easy Apply Button"
                logger.info("Clicking the EASY apply button", job_id=jobID, step="apply", event="click_apply")
                button.click()
                time.sleep(1)
                self.form_filler.fill_out_fields(phone_number)

                result = self.send_resume(jobID)

                if result:
                    string_easy = "*Applied: Sent Resume"
                else:
                    string_easy = "*Did not apply: Failed to send Resume"
        elif "You applied on" in self.page.content():
            logger.info("You have already applied to this position.", job_id=jobID, step="apply", event="already_applied")
            string_easy = "* Already Applied"
            result = False
        else:
            logger.info("The Easy apply button does not exist.", job_id=jobID, step="apply", event="no_button")
            string_easy = "* Doesn't have Easy Apply Button"
            result = False

        logger.info(f"\nPosition {jobID}:\n {self.page.title()} \n {string_easy} \n", 
                   job_id=jobID, step="apply", event="summary")

        self.store.write_to_file(button, jobID, self.page.title(), result)
        return result

    @retry(max_attempts=3, delay=1)
    def get_job_page(self, jobID):
        job = 'https://www.linkedin.com/jobs/view/' + str(jobID)
        self.page.goto(job, wait_until="domcontentloaded")

    @retry(max_attempts=3, delay=1)
    def get_easy_apply_button(self):
        """
        Find and return the Easy Apply button
        """
        try:
            button_selector = get_locator("easy_apply_button")
            buttons = self.page.locator(button_selector).all()
            
            for button in buttons:
                if "Easy Apply" in button.text_content():
                    button.wait_for(state="visible", timeout=5000)
                    return button
            
            logger.debug("Easy Apply button not found", step="get_button")
            return False
        except Exception as e:
            if self.metrics:
                self.metrics.increment("failed")
            logger.debug(f"Easy Apply button not found: {e}", step="get_button", exception=e)
            return False

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

    @retry(max_attempts=5, delay=1)
    def send_resume(self, jobID=None) -> bool:
        """
        Navigate through multi-step application form
        """
        try:
            submitted = False
            loop = 0
            while loop < 20:  # Increased loop limit for multi-page forms
                time.sleep(1)
                
                # Upload resume
                resume_selector = get_locator("upload_resume")
                if self.is_present(resume_selector):
                    try:
                        resume = self.uploads.get("Resume")
                        if resume:
                            abs_resume = os.path.abspath(resume)
                            self.page.locator(resume_selector).first.set_input_files(abs_resume)
                            logger.info(f"Uploaded resume: {abs_resume}", job_id=jobID, step="upload_resume")
                    except Exception as e:
                        logger.error(f"Resume upload failed: {e}", job_id=jobID, step="upload_resume", exception=e)

                # Upload cover letter
                cv_selector = get_locator("upload_cv")
                if self.is_present(cv_selector):
                    cv = self.uploads.get("Cover Letter")
                    if cv:
                        try:
                            abs_cv = os.path.abspath(cv)
                            self.page.locator(cv_selector).first.set_input_files(abs_cv)
                            logger.info(f"Uploaded cover letter: {abs_cv}", job_id=jobID, step="upload_cv")
                        except Exception as e:
                            pass

                # Click 'Follow Company' if present
                follow_selector = get_locator("follow")
                follow_elements = self.get_elements("follow")
                if follow_elements:
                    for element in follow_elements:
                        try:
                            element.click()
                            logger.info("Clicked 'Follow Company' checkbox", job_id=jobID, step="follow")
                        except:
                            pass

                # Check for submit button
                if len(self.get_elements("submit")) > 0:
                    elements = self.get_elements("submit")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        
                        if self.dry_run and not self.dry_run.validate_submit():
                            submitted = True
                            logger.info("Fake success for dry run", job_id=jobID, step="submit", event="dry_run_success")
                            break
                        
                        element.click()
                        logger.info("Application Submitted", job_id=jobID, step="submit", event="success")
                        submitted = True
                        if self.metrics:
                            self.metrics.increment("submitted")
                        break
                    
                    if submitted:
                        break  # Exit the WHILE loop immediately

                # Check for errors
                elif len(self.get_elements("error")) > 0:
                    logger.warning("⚠️ Form contains errors or missing required fields.", job_id=jobID, step="form_error")
                    
                    # Try to solve automatically first
                    logger.info("Attempting to auto-solve questions...", job_id=jobID, step="auto_solve")
                    self.form_filler.process_questions()
                    
                    time.sleep(2)
                    
                    # Check if errors still exist
                    if len(self.get_elements("error")) > 0:
                        logger.info("🛑 PAUSED: Bot cannot solve these questions. PLEASE SOLVE THEM MANUALLY.", 
                                   job_id=jobID, step="manual_intervention")
                        logger.info("⏰ I will wait indefinitely until you clear the errors. You can take as much time as you need.", 
                                   job_id=jobID, step="waiting")
                        
                        # Wait forever until errors are cleared
                        while len(self.get_elements("error")) > 0:
                            time.sleep(5)
                            # Check if the job was closed or we navigated away
                            if "You applied on" in self.page.content() or "application was sent" in self.page.content():
                                break
                            if self.is_present(get_locator("easy_apply_button")):
                                break
                        
                        logger.info("✅ Errors cleared! Resuming...", job_id=jobID, step="resuming")
                    
                    continue  # Try the page again

                # Check for next button
                elif len(self.get_elements("next")) > 0:
                    elements = self.get_elements("next")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()

                # Check for review button
                elif len(self.get_elements("review")) > 0:
                    elements = self.get_elements("review")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()

                # Check for follow button (alternative location)
                elif len(self.get_elements("follow")) > 0:
                    elements = self.get_elements("follow")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()
                
                loop += 1  # Avoid infinite loop if stuck

        except Exception as e:
            logger.error(f"Cannot apply to this job: {e}", job_id=jobID, step="apply_loop", exception=e)
            if self.metrics:
                self.metrics.increment("failed")

        if submitted and self.execution_guard:
            self.execution_guard.on_success()

        return submitted
