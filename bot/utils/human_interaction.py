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

    async def scroll_page(self):
        """
        Scrolls the window with natural stutter.
        """
        total_height = await self.page.evaluate("() => document.body.scrollHeight")
        current_pos = await self.page.evaluate("() => window.pageYOffset")
        
        while current_pos < total_height:
            step = random.randint(300, 700)
            current_pos += step
            
            # Occasional scroll up (jitter)
            if random.random() < 0.1:
                current_pos -= random.randint(50, 150)
            
            await self.page.evaluate(f"window.scrollTo(0, {current_pos})")
            await self.page.wait_for_timeout(random.randint(100, 400))
            
            # Check if we hit bottom
            new_height = await self.page.evaluate("() => document.body.scrollHeight")
            if current_pos >= new_height:
                break
            total_height = new_height

    async def scroll_element(self, element):
        """
        Scrolls a specific element (like a job list container) with stutter.
        """
        try:
            total_height = await element.evaluate("el => el.scrollHeight")
            current_pos = await element.evaluate("el => el.scrollTop")
            
            target = current_pos + random.randint(300, 600)
            
            # Jitter
            if random.random() < 0.1:
                target -= random.randint(20, 100)
                
            await element.evaluate(f"el => el.scrollTo(0, {target})")
            await self.page.wait_for_timeout(random.randint(200, 500))
            
            return target
        except Exception as e:
            logger.warning(f"Human scroll failed: {e}", step="human_scroll")

    async def click(self, locator):
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
                box = await element.bounding_box()
                if box:
                    # Move to a random point within the element
                    target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                    target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                    
                    # Get current mouse position (approximate)
                    current_pos = await self.page.evaluate("""
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
                        await self.page.mouse.move(x, y)
                        await self.page.wait_for_timeout(random.randint(5, 15))
                    
                    # Small delay before click
                    await self.page.wait_for_timeout(random.randint(50, 150))
            except:
                pass  # If we can't get bounding box, just click normally
            
            # Click the element
            await element.click()
            
        except Exception as e:
            logger.warning(f"Click failed: {e}", step="click_error")
            raise

    async def type_text(self, locator, text):
        """
        Types text with random delays between keystrokes.
        """
        try:
            if isinstance(locator, str):
                element = self.page.locator(locator)
            else:
                element = locator
            
            await element.click()
            
            for char in text:
                await element.press_sequentially(char, delay=random.randint(50, 200))
                
        except Exception as e:
            logger.warning(f"Typing failed: {e}", step="type_error")
            raise
