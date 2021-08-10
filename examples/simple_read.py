from pystlink import PyStlink

pystlink = PyStlink()

a = pystlink.read_word(0x08000000)
print(a)

b = pystlink.read_words(0x08000000, 4)
print(b)
