from pystlink import PyStlink


def print_reg_data(address, data):
    for i in range(len(data)//2):
        print(f"0x{address + (i*8):08x}: 0x{data[i * 2]}", end=" ")
        print(f"0x{data[(i * 2) + 1]}")
    print()


pystlink = PyStlink(verbosity=1)

reg_address = 0x1fff7100
words = pystlink.read_words(reg_address, 8)
print_reg_data(reg_address, words)

pystlink.program_otp(reg_address, "AABBCCDD42426969")
# pystlink.ProgramOTP(reg_address + 0x8, "01020304050607081122334455667788")

words = pystlink.read_words(reg_address, 8)
print_reg_data(reg_address, words)

