from pystlink import PyStlink

pystlink = PyStlink()

a = pystlink.ReadWord(0x08000000)
print(a)

b = pystlink.ReadWords(0x08000000, 4)
print(b)
