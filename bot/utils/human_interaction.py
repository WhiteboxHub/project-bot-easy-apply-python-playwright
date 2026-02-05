import time
import random
import math
from bot.utils.logger import logger

class HumanInteraction:
    def __init__(self, page):
        """
        Initialize with Playwright page object
        """
        self.page = page
    
    def _bezier_curve(self, start, end, control1, control2, steps=20):
        """
        Generate points along a cubic Bezier curve for natural mouse movement
        """
        points = []
        for i in range(steps + 1):
            t = i / steps
            # Cubic Bezier formula
            x = (1-t)**3 * start[0] + 3*(1-t)**2*t * control1[0] + 3*(1-t)*t**2 * control2[0] + t**3 * end[0]
            y = (1-t)**3 * start[1] + 3*(1-t)**2*t * control1[1] + 3*(1-t)*t**2 * control2[1] + t**3 * end[1]
            points.append((x, y))
        return points

    def scroll_page(self):
        """
        Scrolls the window with natural stutter.
        """
        total_height = self.page.evaluate("() => document.body.scrollHeight")
        current_pos = self.page.evaluate("() => window.pageYOffset")
        
        while current_pos < total_height:
            step = random.randint(300, 700)
            current_pos += step
            
            # Occasional scroll up (jitter)
            if random.random() < 0.1:
                current_pos -= random.randint(50, 150)
            
            self.page.evaluate(f"window.scrollTo(0, {current_pos})")
            time.sleep(random.uniform(0.1, 0.4))
            
            # Check if we hit bottom
            new_height = self.page.evaluate("() => document.body.scrollHeight")
            if current_pos >= new_height:
                break
            total_height = new_height

    def scroll_element(self, element):
        """
        Scrolls a specific element (like a job list container) with stutter.
        """
        try:
            total_height = element.evaluate("el => el.scrollHeight")
            current_pos = element.evaluate("el => el.scrollTop")
            
            target = current_pos + random.randint(300, 600)
            
            # Jitter
            if random.random() < 0.1:
                target -= random.randint(20, 100)
                
            element.evaluate(f"el => el.scrollTo(0, {target})")
            time.sleep(random.uniform(0.2, 0.5))
            
            return target
        except Exception as e:
            logger.warning(f"Human scroll failed: {e}", step="human_scroll")

    def click(self, locator):
        """
        Clicks with optional natural mouse movement.
        Playwright locator can be a string or Locator object.
        """
        try:
            # If locator is a string, get the locator object
            if isinstance(locator, str):
                element = self.page.locator(locator)
            else:
                element = locator
            
            # Get element bounding box for natural movement
            try:
                box = element.bounding_box()
                if box:
                    # Move to a random point within the element
                    target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                    target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                    
                    # Get current mouse position (approximate)
                    current_pos = self.page.evaluate("""
                        () => {
                            return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
                        }
                    """)
                    
                    # Generate Bezier curve points
                    control1 = (
                        current_pos['x'] + random.randint(-100, 100),
                        current_pos['y'] + random.randint(-100, 100)
                    )
                    control2 = (
                        target_x + random.randint(-50, 50),
                        target_y + random.randint(-50, 50)
                    )
                    
                    points = self._bezier_curve(
                        (current_pos['x'], current_pos['y']),
                        (target_x, target_y),
                        control1,
                        control2,
                        steps=random.randint(10, 20)
                    )
                    
                    # Move mouse along curve
                    for x, y in points:
                        self.page.mouse.move(x, y)
                        time.sleep(random.uniform(0.005, 0.015))
                    
                    # Small delay before click
                    time.sleep(random.uniform(0.05, 0.15))
            except:
                pass  # If we can't get bounding box, just click normally
            
            # Click the element
            element.click()
            
        except Exception as e:
            # Handle potential stale element by waiting and retrying once
            if "stale" in str(e).lower() or "detached" in str(e).lower():
                logger.warning("Detected detached element, retrying locator...", step="human_click")
                time.sleep(1)
                element.click()
                return

            logger.warning(f"Click failed: {e}", step="click_error")
            raise

    def move_mouse_randomly(self):
        """Perform a natural micro-movement elsewhere to mimic real users"""
        try:
            viewport = self.page.viewport_size
            if viewport:
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                self.page.mouse.move(x, y, steps=random.randint(5, 15))
        except:
            pass

    def type_text(self, locator, text):
        """
        Types text with random delays between keystrokes.
        """
        try:
            if isinstance(locator, str):
                element = self.page.locator(locator)
            else:
                element = locator
            
            element.click()
            
            for char in text:
                element.press_sequentially(char, delay=random.randint(50, 200))
                
        except Exception as e:
            logger.warning(f"Typing failed: {e}", step="type_error")
            raise

