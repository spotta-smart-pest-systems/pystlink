from pathlib import Path
from pystlink import PyStlink

pystlink = PyStlink()

a = pystlink.ReadWord(0x08000000)
print(a)

firmware = Path("hylob_q.srec")
pystlink.program_flash(str(firmware))
