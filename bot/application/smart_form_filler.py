"""
Smart Form Filler with Human-in-Loop for Unknown Questions
Supports profile data, answer learning, and manual intervention
"""

import time
import re
import json
import os
from playwright.sync_api import Page, Locator
from bot.utils.logger import logger
from bot.utils.selectors import LOCATORS


class SmartFormFiller:
    def __init__(self, page: Page, candidate_profile: dict):
        self.page = page
        self.candidate_profile = candidate_profile
        self.profile_data = candidate_profile.get('profile_data', {})
        # Assuming LOCATORS is defined globally or imported
        self.locator = LOCATORS 
        
        # Profile-specific learned answers file
        candidate_id = candidate_profile.get('id', 'default')
        self.learned_answers_file = f'./profiles/{candidate_id}/learned_answers.json'
        
        # Load previously learned answers for this candidate
        self.learned_answers = self._load_learned_answers()
        logger.info(f"Loaded {len(self.learned_answers)} learned answers for {candidate_id}", step="init")
        
        # GLiNER for smart question matching (optional)
        self.gliner = None
        # Uncomment to enable GLiNER (requires: pip install gliner)
        # try:
        #     from gliner import GLiNER
        #     self.gliner = GLiNER.from_pretrained("urchade/gliner_base")
        #     logger.info("GLiNER loaded successfully", step="init")
        # except:
        #     logger.warning("GLiNER not available, using keyword matching", step="init")
    
    def _load_learned_answers(self):
        """Load previously learned answers for this candidate"""
        
        if os.path.exists(self.learned_answers_file):
            try:
                with open(self.learned_answers_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load learned answers: {e}", step="init")
        return {}
    
    def _save_learned_answers(self):
        """Save learned answers for this candidate"""
        
        try:
            os.makedirs(os.path.dirname(self.learned_answers_file), exist_ok=True)
            with open(self.learned_answers_file, 'w') as f:
                json.dump(self.learned_answers, f, indent=2)
            logger.debug(f"Saved {len(self.learned_answers)} learned answers", step="save_answers")
        except Exception as e:
            logger.warning(f"Could not save learned answers: {e}", step="save_answers")
        
    def fill_all_fields(self):
        """
        Fill all form fields on the current page
        Returns True if successful, False if user cancelled
        """
        try:
            # Find all form fields
            fields = self.page.locator(".jobs-easy-apply-form-section__grouping, .fb-dash-form-element").all()
            
            if not fields:
                logger.debug("No form fields found on current page", step="fill_fields")
                return True
                
            logger.info(f"Found {len(fields)} form fields to process", step="fill_fields")
            
            human_intervention_occurred = False
            
            for i, field in enumerate(fields):
                try:
                    intervention_result = self._process_field(field, i+1)
                    if intervention_result == "human_input":
                        human_intervention_occurred = True
                except Exception as e:
                    logger.warning(f"Error processing field {i+1}: {e}", step="fill_fields")
                    continue
            
            # AUTO-PROCEED: Removed the manual "ready" prompt to reduce manual work
            if human_intervention_occurred:
                logger.info("Human intervention occurred, but proceeding automatically...", step="fill_fields")
                time.sleep(2) # Brief pause to allow user to see what happened
                
            return True
            
        except Exception as e:
            logger.error(f"Error filling fields: {e}", step="fill_fields", exception=e)
            return False
    
    def _process_field(self, field: Locator, field_num: int):
        """Process a single form field. Returns 'human_input' if human intervention was needed."""
        try:
            # Get field label/question
            question_text = self._extract_question(field)
            if not question_text:
                return None
            
            # Check if required
            is_required = self._is_required_field(field)
            required_marker = "⚠️ REQUIRED" if is_required else ""
            
            logger.debug(f"Field {field_num}: {question_text} {required_marker}", step="process_field")
            
            # Determine field type
            field_type = self._detect_field_type(field)
            
            # Get answer from profile data
            answer = self._get_answer(question_text, field_type)
            
            # If no answer found, ask human
            if answer is None:
                answer = self._ask_human(question_text, field, is_required)
                if answer is None:  # User skipped
                    if is_required:
                        logger.warning(f"⚠️ REQUIRED FIELD SKIPPED: {question_text}", step="process_field")
                        print(f"\n⚠️ WARNING: You skipped a REQUIRED field: {question_text}\n")
                    return None
                return "human_input"  # Signal that human intervention occurred
            
            # Fill the field
            self._fill_field(field, answer, field_type)
            return "auto_filled"
            
        except Exception as e:
            logger.debug(f"Field processing error: {e}", step="process_field")
            return None
    
    def _is_required_field(self, field: Locator) -> bool:
        """Check if field is marked as required"""
        try:
            # Check for required attribute
            if field.locator("[required], [aria-required='true']").count() > 0:
                return True
            
            # Check for "Required" text in label
            text = field.text_content(timeout=1000)
            if text and "required" in text.lower():
                return True
        except:
            pass
        return False
    
    def _extract_question(self, field: Locator) -> str:
        """Extract question text from field (cleanly)"""
        try:
            # Try specific label elements first for cleaner keys
            label_selectors = [
                ".fb-dash-form-element__label",
                "label",
                "legend",
                ".jobs-easy-apply-form-section__grouping h3"
            ]
            
            for selector in label_selectors:
                label_el = field.locator(selector).first
                if label_el.count() > 0:
                    text = label_el.text_content(timeout=500).strip()
                    if text:
                        # Remove "Required" and extra whitespace
                        text = re.sub(r'\s*Required\s*', '', text, flags=re.IGNORECASE)
                        text = " ".join(text.split())
                        return text[:200]

            # Fallback to full text if no specific label found
            text = field.text_content(timeout=1000)
            if text:
                text = text.strip()
                text = re.sub(r'\s*Required\s*', '', text, flags=re.IGNORECASE)
                # Cleanup: remove multi-line repeats which happen on LinkedIn
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if lines:
                    return lines[0][:200] # Usually the first line is the question
        except:
            pass
        return ""
    
    def _detect_field_type(self, field: Locator) -> str:
        """Detect the type of form field"""
        try:
            # Check for select dropdown
            if field.locator("select").count() > 0:
                return "select"
            
            # Check for radio buttons
            if field.locator("input[type='radio']").count() > 0:
                return "radio"
            
            # Check for checkbox
            if field.locator("input[type='checkbox']").count() > 0:
                return "checkbox"
            
            # Check for text input
            if field.locator("input[type='text'], input[type='email'], input[type='tel']").count() > 0:
                return "text"
            
            # Check for textarea
            if field.locator("textarea").count() > 0:
                return "textarea"
                
        except:
            pass
        
        return "unknown"
    
    def _get_answer(self, question_text: str, field_type: str):
        """
        Get answer from profile data using smart matching
        Priority: 1. Learned answers, 2. Profile data, 3. None
        """
        question_lower = question_text.lower()
        
        # 0. Check learned answers first (exact match)
        if question_text in self.learned_answers:
            return self.learned_answers[question_text]
        
        # 0.1 Check legacy Store (fallback)
        from bot.persistence.store import Store
        legacy_store = Store()
        legacy_answer = legacy_store.get_answer(question_lower)
        if legacy_answer:
            logger.debug(f"Found answer in legacy store: {legacy_answer}", step="get_answer")
            return legacy_answer
        
        # 1. Smart keyword matching for common questions
        answer = self._match_keywords(question_lower)
        if answer:
            return answer
        
        return None
    
    def _match_keywords(self, question_lower: str):
        """Match question to profile data using keywords"""
        
        # 1. Identity
        if 'first name' in question_lower or 'first_name' in question_lower:
            full_name = self.profile_data.get('full_name', '')
            return full_name.split()[0] if full_name.split() else ''
        
        if 'last name' in question_lower or 'last_name' in question_lower:
            full_name = self.profile_data.get('full_name', '')
            parts = full_name.split()
            return parts[-1] if len(parts) > 1 else ''
        
        if 'full name' in question_lower or ('name' in question_lower and 'first' not in question_lower and 'last' not in question_lower):
            return self.profile_data.get('full_name')
        
        # 2. Contact
        if 'email' in question_lower:
            return self.profile_data.get('email')
        
        if 'phone' in question_lower or 'mobile' in question_lower:
            if 'country' in question_lower or 'code' in question_lower:
                return self.profile_data.get('country_code', 'India (+91)')
            return self.profile_data.get('phone')
        
        # 3. Experience & Skills
        if 'years' in question_lower:
            if 'python' in question_lower:
                return self.profile_data.get('years_python', '1')
            if 'javascript' in question_lower or 'js' in question_lower:
                return self.profile_data.get('years_javascript', '0')
            if 'react' in question_lower:
                return self.profile_data.get('years_react', '0')
            if 'ml' in question_lower or 'machine learning' in question_lower:
                return self.profile_data.get('years_ml', '1')
            return self.profile_data.get('years_experience', '1')
        
        # 4. Work Auth & Sponsorship (CRITICAL)
        if 'sponsor' in question_lower or 'visa' in question_lower:
            return self.profile_data.get('sponsorship_required', 'No')
        
        if 'authorized' in question_lower and 'work' in question_lower:
            return self.profile_data.get('authorized_to_work', 'Yes')
            
        if 'legally' in question_lower and 'eligible' in question_lower:
            return self.profile_data.get('authorized_to_work', 'Yes')

        # 5. Preferences
        if 'relocate' in question_lower:
            return self.profile_data.get('willing_to_relocate', 'Yes')
        
        if 'remote' in question_lower:
            return 'Yes'
        
        # 6. Salary
        if 'salary' in question_lower or 'compensation' in question_lower:
            if 'current' in question_lower:
                return self.profile_data.get('current_salary', '80000')
            return self.profile_data.get('expected_salary', '100000')
        
        # 7. Broad "Yes/No" Patterns
        # REMOVED: No more blind "Yes" defaults to avoid "wrong answers".
        # We now rely on the 4-6s wait window for unknown questions.
            
        # 8. Demographic Defaults (often grouped at end)
        if 'gender' in question_lower:
            return "Male"
        if 'race' in question_lower or 'ethnicity' in question_lower:
            return "Wish not to answer"
        if 'lgbtq' in question_lower or 'disability' in question_lower or 'veteran' in question_lower:
            return "No"

        return None
    
    def _ask_human(self, question_text: str, field: Locator, is_required: bool = False):
        """
        Ask human to answer unknown question
        Highlights field and waits for input
        """
        try:
            # Highlight the field in browser
            highlight_color = 'red' if is_required else 'orange'
            field.evaluate(f"el => el.style.border = '4px solid {highlight_color}'")
            field.evaluate("el => el.scrollIntoView({block: 'center'})")
            
            # HYBRID AUTOMATION: 10s wait for input, then 4s post-detection review
            logger.warning(f"🤔 UNKNOWN QUESTION: {question_text}", step="human_input")
            print(f"\n🤔 Question: {question_text}")
            print("⏳ Waiting for your input in the browser...")
            
            # Phase 1: Poll for any input (up to 10s wait for user to start)
            detected = False
            for _ in range(20):  # 10s total
                time.sleep(0.5)
                answer = self._extract_filled_value(field)
                if answer:
                    detected = True
                    print(f"✅ Detected: '{answer}'. Keeping focus for 4 more seconds so you can finish/review...")
                    break
            
            if detected:
                # Phase 2: The 4-second "Review" delay requested by user
                time.sleep(4)
                
                # Re-extract the final value after review period
                final_answer = self._extract_filled_value(field)
                self.learned_answers[question_text] = final_answer
                self._save_learned_answers()
                logger.info(f"✅ Learned answer (post-review): {final_answer}", step="human_input")
                
                try:
                    field.evaluate("el => el.style.border = ''")
                except:
                    pass
                return final_answer
            
            # No input detected after 10s
            try:
                field.evaluate("el => el.style.border = ''")
            except:
                pass
            logger.debug("No input detected, proceeding...", step="human_input")
            return None
                
        except Exception as e:
            logger.error(f"Error in human input: {e}", step="human_input")
            return None
    
    def _extract_filled_value(self, field: Locator) -> str:
        """Extract the value that was filled in the field"""
        try:
            # Try input field
            input_elem = field.locator("input[type='text'], input[type='email'], input[type='tel']").first
            if input_elem.count() > 0:
                return input_elem.input_value()
            
            # Try textarea
            textarea = field.locator("textarea").first
            if textarea.count() > 0:
                return textarea.input_value()
            
            # Try select
            select = field.locator("select").first
            if select.count() > 0:
                return select.input_value()
            
            # Try radio (get checked)
            radios = field.locator("input[type='radio']:checked").all()
            if radios:
                return radios[0].get_attribute("value")
                
        except:
            pass
        
        return None
    
    def _fill_field(self, field: Locator, answer: str, field_type: str):
        """Fill the field with the answer"""
        try:
            if field_type == "select":
                select = field.locator("select").first
                # Try by value, then by label
                try:
                    select.select_option(value=answer)
                except:
                    select.select_option(label=answer)
                logger.debug(f"Selected: {answer}", step="fill_field")
                
            elif field_type == "radio":
                # Find radio with matching value
                radio = field.locator(f"input[type='radio'][value='{answer}']").first
                if radio.count() > 0:
                    radio.click()
                    logger.debug(f"Radio selected: {answer}", step="fill_field")
                    
            elif field_type == "checkbox":
                checkbox = field.locator("input[type='checkbox']").first
                if answer.lower() in ['yes', 'true', '1']:
                    checkbox.check()
                else:
                    checkbox.uncheck()
                logger.debug(f"Checkbox: {answer}", step="fill_field")
                
            elif field_type in ["text", "textarea"]:
                input_elem = field.locator("input, textarea").first
                input_elem.fill("")  # Clear first
                input_elem.fill(str(answer))
                logger.debug(f"Filled: {answer}", step="fill_field")
                
        except Exception as e:
            logger.debug(f"Error filling field: {e}", step="fill_field")
