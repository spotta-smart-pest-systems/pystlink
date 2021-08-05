import random
from pystlink import PyStlink


pystlink = PyStlink()
a = pystlink.ReadWord(0x08000000)
print(a)

val = f"{random.randrange(0, 0xffffffff):08x}"
print(val)
pystlink.write_word_to_flash(0x08000000, val)

b = pystlink.ReadWord(0x08000000)
print(b)

print()
if a != b and val == b:
    print("Pass")
else:
    print("Fail")

