"""Example harness script for cpip loop (examples/loop/example.py)
"""
from cpip.harness import Harness, serve
import random
import time

class MyHarness(Harness):
    def run(self, params):
        # simulate a training/eval step
        time.sleep(0.1)
        loss = random.random()
        return {"loss": loss}

if __name__ == '__main__':
    # For cpip.loop compatibility, also support running directly and printing a JSON result
    import json
    h = MyHarness()
    res = h.run({})
    print(json.dumps(res))
