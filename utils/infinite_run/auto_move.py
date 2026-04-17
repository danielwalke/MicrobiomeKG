import time
import warnings
from wakepy import keep

warnings.filterwarnings("ignore", module="wakepy")

with keep.running():
    while True:
        time.sleep(5)