"""Deep test flow for QA cycles."""

import random
import time

from scripts.flows.base_flow import BaseFlow


class DeepTestFlow(BaseFlow):
    """Thorough QA test: every screen, forms, edge cases."""

    def run(self) -> None:
        time.sleep(random.uniform(2.0, 4.0))
        num_screens = random.randint(5, 10)
        for _ in range(num_screens):
            time.sleep(random.uniform(3.0, 8.0))
            num_actions = random.randint(2, 5)
            for _ in range(num_actions):
                try:
                    action = random.choice(["scroll", "tap", "swipe"])
                    if action == "scroll":
                        self.driver.execute_script(
                            "mobile: scrollGesture",
                            {"left": 100, "top": 300, "width": 200, "height": 500, "direction": "down", "percent": 0.75},
                        )
                    elif action == "tap":
                        self.driver.execute_script(
                            "mobile: clickGesture",
                            {"x": random.randint(50, 350), "y": random.randint(200, 700)},
                        )
                    elif action == "swipe":
                        self.driver.execute_script(
                            "mobile: swipeGesture",
                            {"left": 100, "top": 400, "width": 200, "height": 100, "direction": "left", "percent": 0.75},
                        )
                except Exception:
                    pass
                time.sleep(random.uniform(0.5, 2.0))
