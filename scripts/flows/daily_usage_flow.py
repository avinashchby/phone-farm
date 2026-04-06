"""Daily usage flow for tester-gate cycles."""

import random
import time

from scripts.flows.base_flow import BaseFlow


class DailyUsageFlow(BaseFlow):
    """Simulate daily app usage: open, browse, interact, close."""

    def run(self) -> None:
        time.sleep(random.uniform(2.0, 4.0))
        num_screens = random.randint(3, 5)
        for _ in range(num_screens):
            time.sleep(random.uniform(5.0, 15.0))
            try:
                if random.random() > 0.5:
                    self.driver.execute_script(
                        "mobile: scrollGesture",
                        {"left": 100, "top": 300, "width": 200, "height": 500, "direction": "down", "percent": 0.75},
                    )
                else:
                    self.driver.execute_script(
                        "mobile: clickGesture",
                        {"x": random.randint(100, 300), "y": random.randint(400, 600)},
                    )
            except Exception:
                pass
            time.sleep(random.uniform(0.5, 2.5))
