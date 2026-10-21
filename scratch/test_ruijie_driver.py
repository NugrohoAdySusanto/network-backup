import sys
import logging

logging.basicConfig(level=logging.DEBUG)

from app.drivers.base import DeviceConnectionContext
from app.drivers.ruijie_ap import RuijieAPDriver

ctx = DeviceConnectionContext(
    host="10.11.1.233",
    port=22345,
    username="backupadminn",
    password="Makuku&$#2021",
    connect_timeout=10,
    command_timeout=15,
    hostname="MKK-HQ_AP-04",
)

driver = RuijieAPDriver()
try:
    print("Testing connect...")
    driver.connect(ctx)
    print("Connected successfully!")
    cfg = driver.collect_config()
    print("Collected length:", len(cfg.text))
    driver.cleanup()
except Exception as e:
    print("EXCEPTION CAUGHT:", type(e), e)
    import traceback
    traceback.print_exc()
