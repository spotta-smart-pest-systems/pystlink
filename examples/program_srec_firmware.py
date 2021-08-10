from pathlib import Path
from pystlink import PyStlink

pystlink = PyStlink()

a = pystlink.read_word(0x08000000)
print(a)

firmware = Path("small.srec")
pystlink.program_flash(str(firmware))
