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
    def __init__(self, page: Page, uploads, blacklist_titles=None, execution_guard=None, dry_run=None, metrics=None, candidate_profile=None, review_mode=False):
        self.page = page
        self.uploads = uploads
        self.blacklist_titles = blacklist_titles or []
        self.store = Store()
        self.candidate_profile = candidate_profile
        self.review_mode = review_mode
        self.metrics = metrics
        self.dry_run = dry_run
        self.execution_guard = execution_guard
        
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
        self.application_needs_review = False

    def _application_dialog(self):
        dialogs = self.page.locator("dialog[open], [role='dialog'], .jobs-easy-apply-modal")
        visible_dialogs = dialogs.all()
        for dialog in reversed(visible_dialogs):
            try:
                if dialog.is_visible() and dialog.get_by_role(
                    "button",
                    name="Submit application",
                    exact=True,
                ).filter(visible=True).count():
                    return dialog
            except Exception:
                continue
        for dialog in reversed(visible_dialogs):
            try:
                if dialog.is_visible():
                    return dialog
            except Exception:
                continue
        return self.page

    def apply_to_job(self, jobID, phone_number):
        self.application_needs_review = False
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
                
                # Extract job details and record application start
                try:
                    browser_title = self.page.title()
                    # Parse title: "Job Title | Company | LinkedIn"
                    parts = browser_title.split(' | ')
                    job_title = parts[0].strip() if len(parts) > 0 else "Unknown"
                    company = parts[1].strip() if len(parts) > 1 else "Unknown"
                    
                    # Record application start with comprehensive tracking
                    candidate_id = self.candidate_profile.get('name', 'default') if self.candidate_profile else 'default'
                    self.store.start_application(
                        job_id=jobID,
                        job_title=job_title,
                        company=company,
                        candidate_id=candidate_id,
                        job_url=self.page.url
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse job details for tracking: {e}", job_id=jobID)
                
                try:
                    # Record start time for duration tracking
                    start_time = time.time()
                    
                    button.click()
                    logger.debug("Waiting for modal to open...", job_id=jobID, step="apply")
                    time.sleep(2)  # Wait for modal to fully open
                    
                    # Form filling happens inside send_resume now
                    self.application_needs_review = True
                    result = self.send_resume(jobID, start_time)
                    if result:
                        self.application_needs_review = False

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
        
        if result:
            self.close_modal()
        elif self.application_needs_review:
            logger.warning(
                "Application was not confirmed. Leaving the Easy Apply form open; no save or discard action was taken.",
                job_id=jobID,
                step="cleanup",
                event="application_left_open",
            )
        else:
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
            self._native_submit_clicked = False
            logger.info("⏸️ Application paused for manual review before submission.", job_id=jobID, step="confirmation")
            
            # Inject the modal via evaluate
            self.page.evaluate("""() => {
                window.bot_submit_action = null;

                const isNativeSubmitButton = (button) => {
                    const label = (button.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ').toLowerCase();
                    const text = (button.innerText || '').trim().replace(/\\s+/g, ' ').toLowerCase();
                    return label === 'submit application' ||
                        label === 'submit your application' ||
                        text === 'submit application' ||
                        text === 'submit your application';
                };

                // Clear any existing overlay
                const existing = document.getElementById('bot-submission-overlay');
                if (existing) existing.remove();

                const overlay = document.createElement('div');
                overlay.id = 'bot-submission-overlay';
                // Use pointer-events: none so user can click/scroll the page behind it
                overlay.style.cssText = 'position: fixed !important; top: 0 !important; right: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; z-index: 2147483647 !important; pointer-events: none !important; display: flex !important; align-items: flex-start !important; justify-content: flex-end !important; padding: 16px !important; box-sizing: border-box !important;';
                
                const modal = document.createElement('div');
                modal.style.cssText = 'background: #121212 !important; color: #ffffff !important; padding: 22px !important; border-radius: 20px !important; width: min(420px, calc(100vw - 32px)) !important; box-sizing: border-box !important; box-shadow: 0 16px 42px rgba(0,0,0,0.7) !important; font-family: "Outfit", "Inter", -apple-system, system-ui, sans-serif !important; border: 2px solid #ff6a00 !important; text-align: left !important; pointer-events: auto !important;';
                
                const header = document.createElement('div');
                header.style.cssText = 'display: flex !important; align-items: center !important; gap: 12px !important; margin: 0 0 12px !important;';
                
                const icon = document.createElement('div');
                icon.innerHTML = '🚀';
                icon.style.cssText = 'font-size: 28px !important;';
                
                const title = document.createElement('h2');
                title.innerText = 'Review & Submit';
                title.style.cssText = 'font-size: 24px !important; margin: 0 !important; font-weight: 900 !important; line-height: 1.2 !important; background: linear-gradient(135deg, #ff4500, #ffb000) !important; -webkit-background-clip: text !important; background-clip: text !important; -webkit-text-fill-color: transparent !important; filter: drop-shadow(0 1px 5px rgba(255, 115, 0, 0.35)) !important;';
                
                header.appendChild(icon);
                header.appendChild(title);
                
                const desc = document.createElement('p');
                desc.innerText = 'The bot has finished filling the form. Review the application on the left, then choose Submit Now.';
                desc.style.cssText = 'font-size: 15px !important; margin: 0 0 18px !important; color: #f1f1f1 !important; line-height: 1.5 !important;';
                
                const btnContainer = document.createElement('div');
                btnContainer.style.cssText = 'display: flex !important; gap: 12px !important;';
                
                const proceedBtn = document.createElement('button');
                proceedBtn.innerText = 'Submit Now';
                proceedBtn.style.cssText = 'position: relative !important; z-index: 1 !important; opacity: 1 !important; filter: none !important; background: #ffbf00 !important; color: #111111 !important; border: 4px solid #ffffff !important; outline: 2px solid #b45309 !important; padding: 14px 18px !important; border-radius: 12px !important; cursor: pointer !important; font-weight: 900 !important; font-size: 19px !important; letter-spacing: 0.2px !important; flex: 1.5 !important; min-height: 62px !important; text-shadow: none !important; box-shadow: 0 0 0 3px #ffbf00, 0 8px 22px rgba(0,0,0,0.7) !important;';
                proceedBtn.onmouseenter = () => proceedBtn.style.setProperty('background', '#ffd54f', 'important');
                proceedBtn.onmouseleave = () => proceedBtn.style.setProperty('background', '#ffbf00', 'important');
                
                const skipBtn = document.createElement('button');
                skipBtn.innerText = 'Skip Job';
                skipBtn.style.cssText = 'background: #2a2a2a !important; color: #ffffff !important; border: 1px solid #666666 !important; padding: 13px 14px !important; border-radius: 12px !important; cursor: pointer !important; font-weight: 700 !important; font-size: 15px !important; flex: 1 !important; min-height: 50px !important;';
                
                proceedBtn.onclick = () => { 
                    if (window._botClickListener) document.removeEventListener('click', window._botClickListener, true);
                    window.bot_submit_action = 'proceed';
                    overlay.remove();
                };
                
                skipBtn.onclick = () => { 
                    if (window._botClickListener) document.removeEventListener('click', window._botClickListener, true);
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
                const topLayerDialog = Array.from(document.querySelectorAll('dialog[open]'))
                    .reverse()
                    .find(dialog =>
                        Array.from(dialog.querySelectorAll('button')).some(isNativeSubmitButton)
                    );
                // Native dialogs render above body-level overlays, so keep the review card in their top layer.
                (topLayerDialog || document.body).appendChild(overlay);
                
                // Trigger animation
                setTimeout(() => {
                    modal.style.transform = 'translateY(0)';
                    modal.style.opacity = '1';
                }, 50);
                
                // Fallback listener for manual LinkedIn clicks
                if (window._botClickListener) document.removeEventListener('click', window._botClickListener, true);
                window._botClickListener = (e) => {
                    const btn = e.target.closest('button');
                    if (btn && !btn.closest('#bot-submission-overlay') && isNativeSubmitButton(btn)) {
                        if (window._botClickListener) document.removeEventListener('click', window._botClickListener, true);
                        window.bot_submit_action = 'native_submitting';
                        overlay.remove();
                    }
                };
                document.addEventListener('click', window._botClickListener, true);
            }""")
            
            # Wait for user action
            start_time = time.time()
            max_wait = 1800  # 30 minutes
            
            while (time.time() - start_time) < max_wait:
                try:
                    action = self.page.evaluate("() => window.bot_submit_action")
                    self._native_submit_clicked = action == "native_submitting"
                    if action == 'native_submitting':
                        logger.info(
                            "Submit Now triggered LinkedIn's native Submit application button.",
                            job_id=jobID,
                            step="submit",
                            event="native_submit_clicked",
                        )
                        return True
                    if action == 'proceed':
                        logger.info(
                            "User selected Submit Now; Playwright will click LinkedIn's native submit control.",
                            job_id=jobID,
                            step="confirmation",
                            event="submit_approved",
                        )
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
            return False

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

    def _pick_preview_easy_apply_button(self, buttons):
        candidates = []
        viewport_width = (self.page.viewport_size or {}).get("width")
        preview_min_x = viewport_width * 0.35 if viewport_width else 0

        for button in buttons:
            try:
                if not button.is_visible():
                    continue
                text = " ".join((button.inner_text(timeout=1000) or "").split()).casefold()
                label = " ".join((button.get_attribute("aria-label") or "").split()).casefold()
                button_id = button.get_attribute("id") or ""
                class_name = button.get_attribute("class") or ""
                strong_preview_match = (
                    button_id == "jobs-apply-button-id"
                    or "jobs-apply-button" in class_name.split()
                    or "linkedin apply to" in label
                )
                text_match = (
                    text == "easy apply"
                    or "easy apply" in label
                    or "continue applying" in label
                )
                if not strong_preview_match and not text_match:
                    continue
                box = button.bounding_box()
                x_position = box["x"] if box else -1
                if strong_preview_match or x_position >= preview_min_x:
                    candidates.append((strong_preview_match, x_position, button))
            except Exception:
                continue

        if not candidates:
            return False

        _, x_position, button = max(
            candidates,
            key=lambda candidate: (candidate[0], candidate[1]),
        )
        logger.debug(
            f"Selected Easy Apply button in the job preview pane at x={x_position:.0f}",
            step="get_button",
        )
        return button

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
            time.sleep(1)  # Allow the preview panel to render before checking buttons
            
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
                self.page.wait_for_selector(button_selector, timeout=750, state="visible")
                buttons = self.page.locator(button_selector).all()
                logger.debug(f"Primary selector found {len(buttons)} buttons", step="get_button")
                button = self._pick_preview_easy_apply_button(buttons)
                if button is not False:
                    return button
            except Exception as e:
                logger.debug(f"Primary selector didn't find button: {e}", step="get_button")
            
            # Try fallback selector
            fallback_selector = get_locator("easy_apply_button", use_fallback=True)
            if fallback_selector and fallback_selector != button_selector:
                logger.debug(f"Trying fallback selector: {fallback_selector}", step="get_button")
                try:
                    self.page.wait_for_selector(fallback_selector, timeout=2000, state="visible")
                    buttons = self.page.locator(fallback_selector).all()
                    logger.debug(f"Fallback selector found {len(buttons)} buttons", step="get_button")
                    button = self._pick_preview_easy_apply_button(buttons)
                    if button is not False:
                        return button
                except Exception as e:
                    logger.debug(f"Fallback selector didn't find button: {e}", step="get_button")
            
            # The search filter and the job preview can both contain "Easy Apply".
            try:
                logger.debug("Searching for Easy Apply buttons in the job preview pane", step="get_button")
                buttons = self.page.get_by_role(
                    "button",
                    name=re.compile("Easy Apply", re.I),
                ).all()
                button = self._pick_preview_easy_apply_button(buttons)
                if button is not False:
                    return button
            except Exception as e:
                logger.debug(f"Text-based selector didn't find button: {e}", step="get_button")
            
            logger.debug("Easy Apply button not found after all attempts", step="get_button")
            return False
            
        except Exception as e:
            if self.metrics:
                self.metrics.increment("failed")
            logger.debug(f"Easy Apply button not found: {e}", step="get_button", exception=e)
            return False

    def get_elements(self, type) -> list:
        """
        Find controls using selectors and their accessible button names.
        """
        root = self._application_dialog()
        selector = get_locator(type)
        if selector:
            elements = root.locator(selector).all()
            fallback_selector = get_locator(type, use_fallback=True)
            if fallback_selector and fallback_selector != selector:
                elements.extend(root.locator(fallback_selector).all())

            accessible_names = {
                "next": re.compile(r"^(next|continue|continue to next step)$", re.IGNORECASE),
                "review": re.compile(r"^(review|review your application)$", re.IGNORECASE),
                "submit": re.compile(r"^(submit|submit application)$", re.IGNORECASE),
            }
            name_pattern = accessible_names.get(type)
            if name_pattern:
                elements.extend(root.get_by_role("button", name=name_pattern).all())

            visible_elements = []
            seen = set()
            for element in elements:
                try:
                    if element.is_visible():
                        identity = element.get_attribute("id") or element.get_attribute("aria-label") or element.inner_text()
                        if identity not in seen:
                            seen.add(identity)
                            visible_elements.append(element)
                except Exception:
                    continue
            return visible_elements
        return []

    def is_present(self, selector):
        """
        Check if element is present on page
        """
        try:
            return self.page.locator(selector).count() > 0
        except:
            return False

    def has_visible_errors(self):
        """Safely check if there are any visible form errors (prevents detach exceptions during redirects)"""
        try:
            for e in self.get_elements("error"):
                try:
                    if e.is_visible():
                        return True
                except Exception:
                    # Ignore individual detached elements
                    continue
        except Exception:
            # If nodes detach mid-check, the page shifted (usually a success state)
            pass
        return False

    def send_resume(self, jobID=None, start_time=None) -> bool:
        """
        Navigate through multi-step application form
        """
        try:
            submitted = False
            loop = 0
            form_pages = 0
            candidate_id = self.candidate_profile.get('name', 'default') if self.candidate_profile else 'default'
            
            while loop < 20:  # Increased loop limit for multi-page forms
                time.sleep(1)
                
                # Upload resume
                resume_selector = get_locator("upload_resume")
                if self.is_present(resume_selector):
                    resume = self.uploads.get("Resume")
                    if resume:
                        abs_resume = os.path.abspath(resume)
                        if os.path.isfile(abs_resume):
                            self.page.locator(resume_selector).first.set_input_files(abs_resume)
                            logger.info(f"Uploaded resume: {abs_resume}", job_id=jobID, step="upload_resume")
                        else:
                            logger.warning(
                                f"Configured local resume was not found at {abs_resume}; "
                                "leaving LinkedIn's saved resume selection unchanged.",
                                job_id=jobID,
                                step="upload_resume",
                                event="local_resume_missing",
                            )

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
                if self.get_elements("submit"):
                    if self.dry_run and not self.dry_run.validate_submit():
                        submitted = True
                        logger.info("Fake success for dry run", job_id=jobID, step="submit", event="dry_run_success")
                        break

                    if not self.wait_for_submit_confirmation(jobID):
                        logger.warning("User skipped or confirmation was unavailable.", job_id=jobID, step="user_action")
                        self.store.record_user_skip(jobID, candidate_id)
                        break

                    logger.info(
                        "User approved submission in the Submit Now prompt; attempting LinkedIn's native submit control.",
                        job_id=jobID,
                        step="submit",
                        event="user_confirmed",
                    )
                    self.store.record_user_confirmation(jobID, candidate_id)

                    if not self._native_submit_clicked and not self._click_submit_button(jobID):
                        logger.error(
                            "Could not click LinkedIn's native submit button. "
                            "Please scroll to the bottom and submit manually within 2 minutes; "
                            "the bot will wait for LinkedIn's success message.",
                            job_id=jobID,
                            step="submit",
                            event="submit_click_failed",
                        )
                        if self._wait_for_submission_confirmation(timeout_seconds=120):
                            duration = round(time.time() - start_time, 2) if start_time else None
                            logger.info(
                                f"LinkedIn confirmed manual submission (duration: {duration}s)",
                                job_id=jobID,
                                step="submit",
                                event="success",
                            )
                            self.store.record_submission_success(
                                job_id=jobID,
                                candidate_id=candidate_id,
                                duration_seconds=duration,
                                form_pages=form_pages,
                                fields_filled=0,
                            )
                            submitted = True
                            break
                        self.store.record_submission_failure(
                            jobID,
                            "Native submit control not found and no manual submission confirmation was detected",
                            candidate_id,
                        )
                        break

                    logger.info("Waiting for LinkedIn submission confirmation...", job_id=jobID, step="submit")
                    if not self._wait_for_submission_confirmation(timeout_seconds=20):
                        logger.warning(
                            "LinkedIn success confirmation was not detected; leaving the application open.",
                            job_id=jobID,
                            step="submit",
                            event="submission_unverified",
                        )
                        self.store.record_submission_failure(
                            jobID,
                            "No explicit LinkedIn submission confirmation was detected",
                            candidate_id,
                        )
                        break

                    duration = round(time.time() - start_time, 2) if start_time else None
                    logger.info(
                        f"LinkedIn confirmed submission (duration: {duration}s)",
                        job_id=jobID,
                        step="submit",
                        event="success",
                    )
                    self.store.record_submission_success(
                        job_id=jobID,
                        candidate_id=candidate_id,
                        duration_seconds=duration,
                        form_pages=form_pages,
                        fields_filled=0,
                    )
                    submitted = True
                    break

                # Check for errors
                elif self.has_visible_errors():
                    logger.warning("⚠️ Form contains errors or missing required fields.", job_id=jobID, step="form_error")
                    
                    # Fill fields again - maybe something was missed
                    logger.info("Re-attempting to fill fields...", job_id=jobID, step="retry_fill")
                    if hasattr(self.form_filler, 'fill_all_fields'):
                        self.form_filler.fill_all_fields()
                    
                    time.sleep(2)
                    
                    # AUTO-SKIP: Instead of pausing and waiting for user input, skip this job
                    # This reduces manual work and keeps the bot running.
                    if self.has_visible_errors():
                        logger.warning("🛑 Form still has errors after retry. Skipping this job to keep automation running.", 
                                   job_id=jobID, step="auto_skip")
                        
                        # Note: close_modal() is called in apply_to_job() so we just break here
                        break 
                    
                    continue  # Try the page again if errors were potentially fixed

                # Check for SUBMIT button
                elif self.is_present(get_locator("submit")) or self.is_present(get_locator("submit", use_fallback=True)):
                    # REVIEW STEP: If review mode is on, wait for user BEFORE clicking
                    if self.review_mode:
                        logger.info("⏸️ Application ready for review. Waiting for user confirmation in browser...", job_id=jobID, step="submit")
                        if not self._wait_for_submit_confirmation(jobID):
                            logger.warning("⏭️ User skipped/cancelled submission", job_id=jobID, step="submit")
                            submitted = False
                            break
                    
                    # ACTION: Click Submit
                    if self.dry_run and not self.dry_run.validate_submit():
                        submitted = True
                        logger.info("Fake success for dry run", job_id=jobID, step="submit", event="dry_run_success")
                        break
                    
                    if self._click_submit_button(jobID):
                        # CRITICAL: VERIFY SUBMISSION
                        logger.info("⏳ Verifying submission...", job_id=jobID, step="submit")
                        time.sleep(4)
                        
                        # Check for success using multiple indicators
                        if self._verify_submission(jobID):
                            logger.info("✅ Application Submitted Successfully!", job_id=jobID, step="submit", event="success")
                            submitted = True
                            if self.metrics:
                                self.metrics.increment("submitted")
                            time.sleep(2)
                            break
                        else:
                            logger.warning("⚠️ Submission could not be verified (might still be on form)", job_id=jobID, step="submit")
                            submitted = False
                    else:
                        logger.error("❌ Failed to click Submit button even after finding it", job_id=jobID, step="submit")
                        submitted = False
                    
                    if submitted:
                        break

                # Check for next button
                elif len(self.get_elements("next")) > 0:
                    elements = self.get_elements("next")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()
                        form_pages += 1  # Track page progression
                        logger.info(f"Clicked Next button (page {form_pages})", job_id=jobID, step="next")
                        break

                # Check for review button
                elif len(self.get_elements("review")) > 0:
                    elements = self.get_elements("review")
                    for element in elements:
                        element.wait_for(state="visible", timeout=5000)
                        element.click()
                        form_pages += 1  # Track page progression
                        logger.info(f"Clicked Review button (page {form_pages})", job_id=jobID, step="review")
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
                    
                    if self._has_submission_confirmation():
                        logger.info(
                            "LinkedIn displayed a submission confirmation.",
                            job_id=jobID,
                            step="complete",
                            event="success",
                        )
                        submitted = True
                    else:
                        logger.warning(
                            "No submission confirmation or recognized form action was found; "
                            "this application is not counted as submitted.",
                            job_id=jobID,
                            step="no_action",
                            event="application_incomplete",
                        )
                    break
                
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
            
        if submitted and self.metrics:
            self.metrics.increment("submitted")

        return submitted

    def _click_submit_button(self, jobID) -> bool:
        """Robustly find and click the LinkedIn 'Submit application' button"""
        try:
            self.page.wait_for_timeout(450)
            dialog = self._application_dialog()
            roots = [dialog]
            if dialog is not self.page:
                roots.append(self.page)

            try:
                dialog.evaluate("""root => {
                    const elements = [root, ...root.querySelectorAll('*')];
                    for (const element of elements) {
                        if (element.scrollHeight > element.clientHeight + 4) {
                            element.scrollTop = element.scrollHeight;
                        }
                    }
                }""")
                self.page.wait_for_timeout(300)
            except Exception as e:
                logger.debug(
                    f"Could not scroll the application dialog to its final step: {e}",
                    job_id=jobID,
                    step="submit",
                )

            accepted_names = {"submit application", "submit your application"}
            for attempt in range(10):
                for root in roots:
                    try:
                        candidates = []
                        buttons = root.locator("button").filter(visible=True)
                        for index in range(buttons.count()):
                            button = buttons.nth(index)
                            label = (button.get_attribute("aria-label") or "").strip().casefold()
                            text = " ".join((button.inner_text(timeout=1000) or "").split()).casefold()
                            if label not in accepted_names and text not in accepted_names:
                                continue
                            box = button.bounding_box()
                            if box:
                                candidates.append((box["y"], button, label or text))

                        if not candidates:
                            continue

                        _, btn, matched_name = max(candidates, key=lambda candidate: candidate[0])
                        btn.scroll_into_view_if_needed(timeout=3000)
                        try:
                            btn.click(timeout=5000)
                        except Exception as click_error:
                            logger.warning(
                                f"Normal click on LinkedIn's exact Submit application button was blocked: {click_error}. "
                                "Retrying with a real mouse click on the same verified button.",
                                job_id=jobID,
                                step="submit",
                                event="native_submit_retry",
                            )
                            if not btn.is_visible() or not btn.is_enabled():
                                raise
                            btn.scroll_into_view_if_needed(timeout=3000)
                            box = btn.bounding_box()
                            if not box:
                                raise RuntimeError("The native Submit application button has no visible position.")
                            self.page.mouse.click(
                                box["x"] + box["width"] / 2,
                                box["y"] + box["height"] / 2,
                            )
                        logger.info(
                            f"Clicked LinkedIn's Submit application control ({matched_name}).",
                            job_id=jobID,
                            step="submit",
                            event="native_submit_clicked",
                        )
                        if self.metrics:
                            self.metrics.increment("submit_clicks")
                        return True
                    except Exception as e:
                        logger.debug(
                            f"Native submit attempt failed: {e}",
                            job_id=jobID,
                            step="submit",
                        )

                if attempt < 9:
                    self.page.wait_for_timeout(500)

            try:
                visible_labels = []
                for button in self.page.locator("button").filter(visible=True).all()[:30]:
                    label = (button.get_attribute("aria-label") or "").strip()
                    text = " ".join((button.inner_text(timeout=500) or "").split())
                    if label or text:
                        visible_labels.append(label or text)
                logger.error(
                    "No visible LinkedIn Submit application control found. "
                    f"Visible button labels: {visible_labels}",
                    job_id=jobID,
                    step="submit",
                    event="submit_control_not_found",
                )
            except Exception:
                logger.error(
                    "No visible LinkedIn Submit application control found in the application dialog or page.",
                    job_id=jobID,
                    step="submit",
                    event="submit_control_not_found",
                )

            return False
        except Exception as e:
            logger.error(f"Error clicking submit: {e}", job_id=jobID)
            return False

    def _verify_submission(self, jobID) -> bool:
        """Thoroughly check if the application was actually sent"""
        try:
            try:
                return self._has_submission_confirmation()
            except Exception as e:
                logger.warning(
                    f"Could not verify submission confirmation: {e}",
                    step="submit",
                    event="confirmation_check_failed",
                )
                return False
        except:
            return False

    def _has_submission_confirmation(self) -> bool:
        """Return True only when the page contains explicit submission-success text."""
        confirmation = self.page.get_by_text(
            re.compile(
                r"(application\s+(was\s+)?(successfully\s+)?(sent|submitted|received)"
                r"|your application has been sent)",
                re.I,
            )
        )
        return confirmation.count() > 0

    def _wait_for_submission_confirmation(self, timeout_seconds=20) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                if self._has_submission_confirmation():
                    return True
                self.page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(
                    f"Could not verify submission confirmation: {e}",
                    step="submit",
                    event="confirmation_check_failed",
                )
                return False
        return self._has_submission_confirmation()

    def _wait_for_submit_confirmation(self, jobID) -> bool:
        """Display a sleek top-bar banner to review and confirm submission, matching question style."""
        try:
            self.page.evaluate("""(jobID) => { 
                // Reset flags
                window.bot_submit_confirmed = false;
                window.bot_submit_skipped = false;

                // Create Modern Floating Banner (Sleek Top Bar)
                const banner = document.createElement('div');
                banner.id = 'bot-review-banner';
                banner.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #1a1a1a; color: white; padding: 12px 25px; border-radius: 12px; z-index: 999999; box-shadow: 0 10px 30px rgba(0,0,0,0.5); font-family: -apple-system, system-ui, sans-serif; display: flex; align-items: center; gap: 20px; border: 1px solid #ff4500; min-width: 400px; animation: slideDown 0.4s ease-out;';
                
                const style = document.createElement('style');
                style.innerHTML = `@keyframes slideDown { from { transform: translate(-50%, -100%); opacity: 0; } to { transform: translate(-50%, 0); opacity: 1; } }`;
                document.head.appendChild(style);

                const text = document.createElement('div');
                text.innerHTML = `<span style="color: #ff4500; font-weight: bold; font-size: 14px; display: block;">🚀 READY TO SUBMIT?</span> <span style="font-size: 13px; color: #ccc;">Please review details for Job ${jobID}</span>`;
                text.style.flex = '1';
                
                const btnContainer = document.createElement('div');
                btnContainer.style.display = 'flex';
                btnContainer.style.gap = '10px';

                // Proceed Button
                const proceedBtn = document.createElement('button');
                proceedBtn.textContent = '✅ Proceed';
                proceedBtn.style.cssText = 'background: #ff4500; color: white; border: none; padding: 8px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 13px; transition: 0.2s;';
                proceedBtn.onclick = () => { window.bot_submit_confirmed = true; banner.style.opacity = '0.5'; banner.innerText = '⌛ Submitting...'; };

                // Skip Button
                const skipBtn = document.createElement('button');
                skipBtn.textContent = '⏭️ Skip';
                skipBtn.style.cssText = 'background: #333; color: white; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer; font-size: 12px;';
                skipBtn.onclick = () => { window.bot_submit_skipped = true; banner.remove(); };

                btnContainer.appendChild(skipBtn);
                btnContainer.appendChild(proceedBtn);
                banner.appendChild(text);
                banner.appendChild(btnContainer);
                document.body.appendChild(banner);
            }""", jobID)

            print(f"\n" + "!"*60)
            print(f"🚀 REVIEW REQUIRED for Job {jobID}")
            print(f"👉 Application is filled. Please review and click 'Proceed' in the browser.")
            print("!"*60 + "\n")

            while True: 
                is_confirmed = self.page.evaluate("() => window.bot_submit_confirmed")
                is_skipped = self.page.evaluate("() => window.bot_submit_skipped")

                if is_confirmed:
                    self.page.evaluate("() => { const b = document.getElementById('bot-review-banner'); if(b) b.remove(); }")
                    return True
                if is_skipped:
                    return False
                time.sleep(0.5)
            return False

        except Exception as e:
            logger.error(f"Error in review banner: {e}")
            return True