import os
import time
import logging
import re
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from bot.application.form_filler import FormFiller
from bot.application.smart_form_filler import SmartFormFiller
from bot.persistence.store import Store
from bot.utils.selectors import LOCATORS, get_locator
from bot.utils.logger import logger
from bot.utils.retry import retry
from bot.utils.human_interaction import HumanInteraction


class Workflow:
    def __init__(self, page: Page, uploads, blacklist_titles=None, execution_guard=None, dry_run=None, metrics=None, candidate_profile=None):
        self.page = page
        self.uploads = uploads
        self.blacklist_titles = blacklist_titles or []
        self.store = Store()
        self.candidate_profile = candidate_profile
        
        # Use SmartFormFiller if candidate profile provided, otherwise old FormFiller
        if candidate_profile:
            self.form_filler = SmartFormFiller(self.page, candidate_profile)
        else:
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
                
                try:
                    button.click()
                    logger.debug("Waiting for modal to open...", job_id=jobID, step="apply")
                    time.sleep(2)  # Wait for modal to fully open
                    
                    # Form filling happens inside send_resume now
                    result = self.send_resume(jobID)

                    if result:
                        string_easy = "*Applied: Sent Resume"
                    else:
                        string_easy = "*Did not apply: Failed to send Resume"
                        
                except Exception as e:
                    logger.error(f"Error during application: {e}", job_id=jobID, step="apply", exception=e)
                    result = False
                    string_easy = "*Error during application"
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
        
        # CRITICAL: Close any open modals before moving to next job
        self.close_modal()
        
        return result
    
    def close_modal(self):
        """Close any open Easy Apply modals to prevent interference with next job"""
        try:
            # 1. Handle "Discard application?" confirmation modal (Priority)
            # This often appears if we try to close the main modal with unsaved changes
            if self.is_present(".artdeco-modal[role='alertdialog']") or self.is_present(".artdeco-modal-overlay"):
                logger.debug("Potential discard/confirmation modal detected", step="cleanup")
                
                # Strategy A: Look for "Discard" button by text (most reliable)
                try:
                    discard_btn = self.page.get_by_text("Discard", exact=True).first
                    if discard_btn.is_visible(timeout=1000):
                        discard_btn.click()
                        logger.info("Clicked 'Discard' text button", step="cleanup")
                        time.sleep(1)
                except:
                    pass
                
                # Strategy B: Selectors
                discard_selectors = [
                    "button[data-test-dialog-primary-btn]",
                    "button[data-control-name='discard_application_confirm_btn']"
                ]
                for sel in discard_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if btn.is_visible(timeout=500):
                            btn.click()
                            logger.info("Clicked Discard button (selector)", step="cleanup")
                            time.sleep(1)
                            break
                    except:
                        continue

            # 2. Close main Easy Apply modal
            modal_selectors = [
                "button[aria-label='Dismiss']",
                "button[data-test-modal-close-btn]",
                ".artdeco-modal__dismiss",
                "button.artdeco-modal__dismiss"
            ]
            
            modal_closed = False
            for selector in modal_selectors:
                try:
                    close_btn = self.page.locator(selector).first
                    if close_btn.count() > 0 and close_btn.is_visible(timeout=1000):
                        close_btn.click()
                        logger.debug("Clicked Close (X) button", step="cleanup")
                        time.sleep(1)
                        modal_closed = True
                        
                        # 3. Discard modal might appear AFTER clicking close
                        if self.is_present(".artdeco-modal[role='alertdialog']") or self.is_present("text=Discard"):
                            logger.info("Discard modal appeared after closing", step="cleanup")
                            discard_btn = self.page.get_by_text("Discard", exact=True).first
                            if discard_btn.is_visible(timeout=2000):
                                discard_btn.click()
                                logger.info("Clicked Discard (after close)", step="cleanup")
                                time.sleep(1)
                        return
                except:
                    continue
            
            # 4. Fallback: Press Escape
            if not modal_closed:
                self.page.keyboard.press("Escape")
                logger.debug("Pressed Escape to close modal", step="cleanup")
                time.sleep(1)
                
                # Check for discard modal again
                if self.is_present("text=Discard"):
                     self.page.get_by_text("Discard", exact=True).click()
                     logger.info("Clicked Discard after Escape", step="cleanup")
                     time.sleep(1)
            
        except Exception as e:
            logger.debug(f"Modal cleanup attempt failed (might not be open): {e}", step="cleanup")

    def wait_for_submit_confirmation(self, jobID):
        try:
            logger.info("⏸️ Application paused for manual review before submission.", job_id=jobID, step="confirmation")
            
            # Inject the modal via evaluate
            self.page.evaluate("""() => {
                // Clear any existing overlay
                const existing = document.getElementById('bot-submission-overlay');
                if (existing) existing.remove();

                const overlay = document.createElement('div');
                overlay.id = 'bot-submission-overlay';
                // Use pointer-events: none so user can click/scroll the page behind it
                overlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 9999999; pointer-events: none; display: flex; align-items: flex-start; justify-content: flex-end; padding: 30px; transition: opacity 0.3s ease;';
                
                const modal = document.createElement('div');
                // Re-enable pointer events for the modal itself
                modal.style.cssText = 'background: #121212; color: white; padding: 24px; border-radius: 24px; width: 380px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); font-family: "Outfit", "Inter", -apple-system, system-ui, sans-serif; border: 1px solid #333; text-align: left; transform: translateY(-20px); opacity: 0; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.1); pointer-events: auto;';
                
                const header = document.createElement('div');
                header.style.cssText = 'display: flex; align-items: center; gap: 12px; margin-bottom: 16px;';
                
                const icon = document.createElement('div');
                icon.innerHTML = '🚀';
                icon.style.cssText = 'font-size: 28px;';
                
                const title = document.createElement('h2');
                title.innerText = 'Review & Submit';
                title.style.cssText = 'font-size: 20px; margin: 0; font-weight: 800; background: linear-gradient(135deg, #ff4500, #ff8c00); -webkit-background-clip: text; -webkit-text-fill-color: transparent;';
                
                header.appendChild(icon);
                header.appendChild(title);
                
                const desc = document.createElement('p');
                desc.innerText = 'The bot has finished filling the form. Please review the application on the left and then decide:';
                desc.style.cssText = 'font-size: 14px; margin-bottom: 20px; color: #bbb; line-height: 1.5;';
                
                const btnContainer = document.createElement('div');
                btnContainer.style.cssText = 'display: flex; gap: 12px;';
                
                const proceedBtn = document.createElement('button');
                proceedBtn.innerText = 'Submit Now';
                proceedBtn.style.cssText = 'background: #ff4500; color: white; border: none; padding: 12px 20px; border-radius: 12px; cursor: pointer; font-weight: 700; font-size: 14px; flex: 1.5; transition: all 0.2s;';
                proceedBtn.onmouseenter = () => proceedBtn.style.background = '#ff571a';
                proceedBtn.onmouseleave = () => proceedBtn.style.background = '#ff4500';
                
                const skipBtn = document.createElement('button');
                skipBtn.innerText = 'Skip Job';
                skipBtn.style.cssText = 'background: #2a2a2a; color: #ddd; border: 1px solid #444; padding: 12px 20px; border-radius: 12px; cursor: pointer; font-weight: 600; font-size: 14px; flex: 1; transition: all 0.2s;';
                skipBtn.onmouseenter = () => skipBtn.style.background = '#333';
                skipBtn.onmouseleave = () => skipBtn.style.background = '#2a2a2a';
                
                proceedBtn.onclick = () => { 
                    window.bot_submit_action = 'proceed'; 
                    modal.style.transform = 'translateY(-20px)';
                    modal.style.opacity = '0';
                    setTimeout(() => overlay.remove(), 400);
                };
                
                skipBtn.onclick = () => { 
                    window.bot_submit_action = 'skip'; 
                    modal.style.transform = 'translateY(-20px)';
                    modal.style.opacity = '0';
                    setTimeout(() => overlay.remove(), 400);
                };
                
                btnContainer.appendChild(skipBtn);
                btnContainer.appendChild(proceedBtn);
                modal.appendChild(header);
                modal.appendChild(desc);
                modal.appendChild(btnContainer);
                overlay.appendChild(modal);
                document.body.appendChild(overlay);
                
                // Trigger animation
                setTimeout(() => {
                    modal.style.transform = 'translateY(0)';
                    modal.style.opacity = '1';
                }, 50);
                
                window.bot_submit_action = null;
            }""")
            
            # Wait for user action
            start_time = time.time()
            max_wait = 1800  # 30 minutes
            
            while (time.time() - start_time) < max_wait:
                try:
                    action = self.page.evaluate("() => window.bot_submit_action")
                    if action == 'proceed':
                        logger.info("✅ User confirmed submission. Proceeding...", job_id=jobID, step="confirmation")
                        return True
                    elif action == 'skip':
                        logger.info("⏭️ User skipped submission.", job_id=jobID, step="confirmation")
                        return False
                except Exception as e:
                    # If browser is closed, stop waiting
                    if "closed" in str(e).lower() or "target" in str(e).lower():
                        logger.warning("Browser closed during confirmation wait.", job_id=jobID, step="confirmation")
                        return False
                    raise e
                    
                time.sleep(1)
            
            # Timeout
            logger.warning("⏰ Submission confirmation timed out after 30 mins.", job_id=jobID, step="confirmation")
            self.page.evaluate("() => { const o = document.getElementById('bot-submission-overlay'); if(o) o.remove(); }")
            return False
            
        except Exception as e:
            logger.error(f"Error in submission confirmation: {e}", step="confirmation")
            return True # Fallback to proceed if error occurs in UI injection

    @retry(max_attempts=3, delay=1)
    def get_job_page(self, jobID):
        """
        Don't navigate to full job page - LinkedIn hides Easy Apply button there!
        Instead, just ensure the job card is clicked to show preview panel on right.
        The job card should already be clicked by search.py, so we just wait a bit.
        """
        import time
        logger.debug(f"Waiting for job preview panel to load for job {jobID}", step="get_job_page")
        time.sleep(0.5)  # Minimal wait - card already clicked in search.py
        # Stay on search results page - Easy Apply button is in the preview panel!

    @retry(max_attempts=3, delay=1)
    def get_easy_apply_button(self):
        """
        Find and return the Easy Apply button in the preview panel
        (NOT the full job page - LinkedIn hides it there!)
        """
        try:
            # Wait for preview panel to load
            import time
            logger.debug("Waiting for preview panel with Easy Apply button...", step="get_button")
            time.sleep(5)  # Wait for preview panel to fully load
            
            # Debug: Count all buttons on page
            try:
                all_buttons = self.page.locator("button").count()
                logger.debug(f"Total buttons on page: {all_buttons}", step="get_button")
            except:
                pass
            
            # Try primary selector first (ID)
            button_selector = get_locator("easy_apply_button")
            logger.debug(f"Looking for Easy Apply button with selector: {button_selector}", step="get_button")
            
            try:
                # Wait for button to appear with longer timeout
                self.page.wait_for_selector(button_selector, timeout=10000, state="visible")
                buttons = self.page.locator(button_selector).all()
                logger.debug(f"Primary selector found {len(buttons)} buttons", step="get_button")
                
                for button in buttons:
                    try:
                        text = button.text_content(timeout=2000)
                        if text and ("Easy Apply" in text or "Continue" in text):
                            logger.debug(f"Found Apply button: {text.strip()}", step="get_button")
                            return button
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Primary selector didn't find button: {e}", step="get_button")
            
            # Try fallback selector
            fallback_selector = get_locator("easy_apply_button", use_fallback=True)
            if fallback_selector and fallback_selector != button_selector:
                logger.debug(f"Trying fallback selector: {fallback_selector}", step="get_button")
                try:
                    self.page.wait_for_selector(fallback_selector, timeout=10000, state="visible")
                    buttons = self.page.locator(fallback_selector).all()
                    logger.debug(f"Fallback selector found {len(buttons)} buttons", step="get_button")
                    
                    for button in buttons:
                        try:
                            text = button.text_content(timeout=2000)
                            if text and ("Easy Apply" in text or "Continue" in text):
                                logger.debug(f"Found Apply button with fallback: {text.strip()}", step="get_button")
                                return button
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Fallback selector didn't find button: {e}", step="get_button")
            
            # Try text-based selector as last resort
            try:
                logger.debug("Trying text-based selector", step="get_button")
                button = self.page.get_by_role("button", name=re.compile("Easy Apply|Continue", re.I)).first
                if button.is_visible(timeout=2000):
                    logger.debug("Found apply button with text selector", step="get_button")
                    return button
            except Exception as e:
                logger.debug(f"Text-based selector didn't find button: {e}", step="get_button")
            
            # Debug: Try to find ANY button with "Easy Apply" in text
            try:
                logger.debug("Searching for any button containing 'Easy Apply' text...", step="get_button")
                all_buttons = self.page.locator("button").all()
                for i, btn in enumerate(all_buttons[:30]):  # Check first 30 buttons
                    try:
                        text = btn.text_content(timeout=1000)
                        if text and ("Easy Apply" in text or "Continue" in text):
                            logger.debug(f"Found button with text at index {i}: {text.strip()}", step="get_button")
                            # Get its attributes
                            btn_id = btn.get_attribute("id", timeout=1000)
                            btn_class = btn.get_attribute("class", timeout=1000)
                            logger.debug(f"  ID: {btn_id}, Class: {btn_class}", step="get_button")
                            return btn
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Manual search failed: {e}", step="get_button")
            
            logger.debug("Easy Apply button not found after all attempts", step="get_button")
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

                # FILL FORM FIELDS FIRST (before clicking buttons)
                logger.debug("Attempting to fill form fields...", job_id=jobID, step="fill_form")
                if hasattr(self.form_filler, 'fill_all_fields'):
                    # SmartFormFiller
                    self.form_filler.fill_all_fields()
                else:
                    # Old FormFiller (fallback)
                    pass
                
                time.sleep(1)  # Let fields settle

                # Check for submit button
                if len(self.get_elements("submit")) > 0:
                    elements = self.get_elements("submit")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        
                        if self.dry_run and not self.dry_run.validate_submit():
                            submitted = True
                            logger.info("Fake success for dry run", job_id=jobID, step="submit", event="dry_run_success")
                            break
                        
                        # NEW: Wait for user confirmation before final click
                        if not self.wait_for_submit_confirmation(jobID):
                            logger.warning("Submission cancelled by user", job_id=jobID, step="submit")
                            submitted = False
                            break # Skip this job
                            
                        # Click submit
                        element.click()
                        logger.info("Clicked Submit button", job_id=jobID, step="submit")
                        
                        # CRITICAL: VERIFY SUBMISSION - Wait longer and check thoroughly!
                        logger.info("⏳ Verifying submission...", job_id=jobID, step="submit")
                        time.sleep(4)  # Wait longer for LinkedIn response
                        
                        # Check if errors appeared after submit
                        if len(self.get_elements("error")) > 0:
                            logger.warning("⚠️ Submit failed - errors appeared", job_id=jobID, step="submit")
                            submitted = False
                            break  # Continue to error handling
                        
                        # Check if modal is still visible (multiple ways)
                        modal_gone = False
                        try:
                            # Method 1: Check if Easy Apply modal disappeared
                            if not self.is_present(".jobs-easy-apply-modal"):
                                modal_gone = True
                            
                            # Method 2: Check if submit button disappeared
                            if not self.is_present("button[aria-label='Submit application']"):
                                modal_gone = True
                            
                            # Method 3: Look for success confirmation
                            if self.is_present(".artdeco-modal__content"):
                                content = self.page.locator(".artdeco-modal__content").first.text_content(timeout=2000)
                                if "application" in content.lower() and "sent" in content.lower():
                                    modal_gone = True
                                    logger.info("✅ Success confirmation found", job_id=jobID, step="submit")
                        except:
                            pass
                        
                        if modal_gone:
                            logger.info("✅ Application Submitted Successfully!", job_id=jobID, step="submit", event="success")
                            submitted = True
                            if self.metrics:
                                self.metrics.increment("submitted")
                            
                            # WAIT for modal to fully close before moving on
                            time.sleep(2)
                            break
                        else:
                            # Modal still open - might be more pages or error
                            logger.warning("⚠️ Modal still open after submit - might need more pages", job_id=jobID, step="submit")
                            submitted = False
                        
                        break
                    
                    if submitted:
                        break  # Exit the WHILE loop

                # Check for errors
                elif len(self.get_elements("error")) > 0:
                    logger.warning("⚠️ Form contains errors or missing required fields.", job_id=jobID, step="form_error")
                    
                    # Fill fields again - maybe something was missed
                    logger.info("Re-attempting to fill fields...", job_id=jobID, step="retry_fill")
                    if hasattr(self.form_filler, 'fill_all_fields'):
                        self.form_filler.fill_all_fields()
                    
                    time.sleep(2)
                    
                    # AUTO-SKIP: Instead of pausing and waiting for user input, skip this job
                    # This reduces manual work and keeps the bot running.
                    if len(self.get_elements("error")) > 0:
                        logger.warning("🛑 Form still has errors after retry. Skipping this job to keep automation running.", 
                                   job_id=jobID, step="auto_skip")
                        
                        # Note: close_modal() is called in apply_to_job() so we just break here
                        break 
                    
                    continue  # Try the page again if errors were potentially fixed

                # Check for next button
                elif len(self.get_elements("next")) > 0:
                    elements = self.get_elements("next")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()
                        logger.info("Clicked Next button", job_id=jobID, step="next")
                        break

                # Check for review button
                elif len(self.get_elements("review")) > 0:
                    elements = self.get_elements("review")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()
                        logger.info("Clicked Review button", job_id=jobID, step="review")
                        break

                # Check for follow button (alternative location)
                elif len(self.get_elements("follow")) > 0:
                    elements = self.get_elements("follow")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()
                        logger.info("Clicked Follow button", job_id=jobID, step="follow")
                        break
                
                else:
                    # No buttons found - might be done or stuck
                    logger.warning(f"⚠️ No Next/Review/Submit buttons found (loop {loop})", job_id=jobID, step="no_action")
                    
                    # Check if we're actually done
                    if not self.is_present(".jobs-easy-apply-modal"):
                        logger.info("Modal closed - application likely complete", job_id=jobID, step="complete")
                        submitted = True
                        break
                    
                    # Check if there are unfilled fields
                    if self.is_present(".jobs-easy-apply-form-section__grouping"):
                        logger.warning("Form fields still present but no buttons - might need manual intervention", job_id=jobID)
                
                loop += 1  # Avoid infinite loop if stuck
                
                # Log progress every 5 loops
                if loop % 5 == 0:
                    logger.info(f"Application loop iteration {loop}/20", job_id=jobID, step="progress")

            # Loop completed without submission
            if not submitted:
                logger.warning(f"⚠️ Loop completed ({loop} iterations) without successful submission", job_id=jobID, step="incomplete")
                if self.metrics:
                    self.metrics.increment("failed")

        except Exception as e:
            logger.error(f"Cannot apply to this job: {e}", job_id=jobID, step="apply_loop", exception=e)
            if self.metrics:
                self.metrics.increment("failed")

        if submitted and self.execution_guard:
            self.execution_guard.on_success()

        return submitted