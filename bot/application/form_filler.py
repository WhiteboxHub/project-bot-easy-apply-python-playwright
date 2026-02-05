import time
import logging
from playwright.sync_api import Page
from bot.persistence.store import Store
from bot.utils.selectors import LOCATORS, get_locator
from bot.utils.logger import logger


class FormFiller:
    def __init__(self, page: Page, salary="100000"):
        self.page = page
        self.salary = salary
        self.store = Store()
        self.locator = LOCATORS

    def fill_out_fields(self, phone_number):
        """
        Fill out phone number field if present
        """
        try:
            fields = self.page.locator(".jobs-easy-apply-form-section__grouping").all()
            for field in fields:
                field_text = field.text_content()
                if "Mobile phone number" in field_text:
                    field_input = field.locator("input").first
                    field_input.fill("")  # Clear first
                    field_input.fill(phone_number)
        except Exception as e:
            logger.debug(f"Error filling phone field: {e}", step="fill_fields")

    def process_questions(self):
        """
        Process and answer form questions automatically
        """
        time.sleep(1)
        form_selector = get_locator("fields")
        form = self.page.locator(form_selector).all()
        
        for field in form:
            try:
                question = field.text_content()
                answer = self.ans_question(question.lower())

                # Radio button
                if self.is_present_in_field(field, get_locator("radio_select")):
                    try:
                        radio = field.locator(f"input[type='radio'][value='{answer}']").first
                        radio.click()
                    except Exception as e:
                        pass

                # Multi-select
                elif self.is_present_in_field(field, get_locator("multi_select")):
                    try:
                        input_field = field.locator("[id*='text-entity-list-form-component']").first
                        input_field.fill(answer)
                    except Exception as e:
                        pass

                # Text input
                elif self.is_present_in_field(field, get_locator("text_select")):
                    try:
                        input_field = field.locator(".artdeco-text-input--input").first
                        input_field.fill(answer)
                    except Exception as e:
                        pass

                # Fallback for Yes/No radio
                if "Yes" in str(answer) or "No" in str(answer):
                    try:
                        radio = field.locator(f"input[type='radio'][value='{answer}']").first
                        radio.click()
                    except:
                        pass
                else:
                    try:
                        input_field = field.locator(".artdeco-text-input--input").first
                        input_field.fill(answer)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Error processing question: {e}", step="process_questions")
    
    def ans_question(self, question):
        """
        Generate answer for a question based on keywords
        """
        # Check store first
        stored_answer = self.store.get_answer(question)
        if stored_answer:
            return stored_answer

        answer = None
        if "salary" in question:
            answer = self.salary
        elif "are you legally" in question:
            answer = "Yes"
        else:
            logger.info("Not able to answer question automatically. Please provide answer", 
                       step="ans_question", event="manual_required")
            answer = "user provided"
        
        logger.info("Answering question: " + question + " with answer: " + answer, 
                   step="ans_question", event="answered")
        self.store.save_answer(question, answer)
        return answer

    def is_present_in_field(self, field, selector):
        """
        Check if selector is present within a specific field
        """
        try:
            return field.locator(selector).count() > 0
        except:
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
