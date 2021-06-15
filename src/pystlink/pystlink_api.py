import time
from textwrap import wrap
import lib
import lib.stlinkv2
import lib.stm32
import lib.stm32fp
import lib.stm32fs
import lib.stm32l0
import lib.stm32l4
import lib.stm32h7
import lib.stm32devices
import lib.stlinkex
import lib.dbg
import lib.srec



class PyStlink():
    CPUID_REG = 0xe000ed00

    def __init__(self, verbosity=0):
        self._connector = None
        self._stlink = None
        self.driver = None

        self._dbg = src.pystlink.lib.dbg.Dbg(verbosity)
        self._serial = None
        self._index = 0
        self._hard = False
        self.detect_cpu(None)
        self.stlink = self._stlink

    def find_mcus_by_core(self):
        if (self._hard):
            self._core.core_hard_reset_halt()
        else:
            self._core.core_halt()
        cpuid = self._stlink.get_debugreg32(PyStlink.CPUID_REG)
        if cpuid == 0:
            raise src.pystlink.lib.stlinkex.StlinkException('Not connected to CPU')
        self._dbg.verbose("CPUID:  %08x" % cpuid)
        partno = 0xfff & (cpuid >> 4)
        for mcu_core in src.pystlink.lib.stm32devices.DEVICES:
            if mcu_core['part_no'] == partno:
                self._mcus_by_core = mcu_core
                return
        raise src.pystlink.lib.stlinkex.StlinkException('PART_NO: 0x%03x is not supported' % partno)

    def find_mcus_by_devid(self):
        # STM32H7 hack: this MCU has ID-CODE on different address than STM32F7
        devid = 0x000
        idcode_regs = self._mcus_by_core['idcode_reg']
        if isinstance(self._mcus_by_core['idcode_reg'], int):
            idcode_regs = [idcode_regs]
        for idcode_reg in idcode_regs:
            idcode = self._stlink.get_debugreg32(idcode_reg)
            self._dbg.verbose("IDCODE: %08x" % idcode)
            devid = 0xfff & idcode
            for mcu_devid in self._mcus_by_core['devices']:
                if mcu_devid['dev_id'] == devid:
                    self._mcus_by_devid = mcu_devid
                    return
        raise src.pystlink.lib.stlinkex.StlinkException('DEV_ID: 0x%03x is not supported' % devid)

    def find_mcus_by_flash_size(self):
        self._flash_size = self._stlink.get_debugreg16(self._mcus_by_devid['flash_size_reg'])
        self._mcus = []
        for mcu in self._mcus_by_devid['devices']:
            if mcu['flash_size'] == self._flash_size:
                self._mcus.append(mcu)
        if not self._mcus:
            raise src.pystlink.lib.stlinkex.StlinkException('Connected CPU with DEV_ID: 0x%03x and FLASH size: %dKB is not supported. Check Protection' % (
                self._mcus_by_devid['dev_id'], self._flash_size
            ))

    def fix_cpu_type(self, cpu_type):
        cpu_type = cpu_type.upper()
        # now support only STM32
        if cpu_type.startswith('STM32'):
            # change character on 10 position to 'x' where is package size code
            if len(cpu_type) > 9:
                cpu_type = list(cpu_type)
                cpu_type[9] = 'x'
                cpu_type = ''.join(cpu_type)
            return cpu_type
        raise src.pystlink.lib.stlinkex.StlinkException('"%s" is not STM32 family' % cpu_type)

    def filter_detected_cpu(self, expected_cpus):
        cpus = []
        for detected_cpu in self._mcus:
            for expected_cpu in expected_cpus:
                expected_cpu = self.fix_cpu_type(expected_cpu)
                if detected_cpu['type'].startswith(expected_cpu):
                    cpus.append(detected_cpu)
                    break
        if not cpus:
            raise src.pystlink.lib.stlinkex.StlinkException('Connected CPU is not %s but detected is %s %s' % (
                ','.join(expected_cpus),
                'one of' if len(self._mcus) > 1 else '',
                ','.join([cpu['type'] for cpu in self._mcus]),
            ))
        self._mcus = cpus


    def load_driver(self):
        flash_driver = self._mcus_by_devid['flash_driver']
        if flash_driver == 'STM32FP':
            self.driver = src.pystlink.lib.stm32fp.Stm32FP(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32FPXL':
            self.driver = src.pystlink.lib.stm32fp.Stm32FPXL(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32FS':
            self.driver = src.pystlink.lib.stm32fs.Stm32FS(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32L0':
            self.driver = src.pystlink.lib.stm32l0.Stm32L0(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32L4':
            self.driver = src.pystlink.lib.stm32l4.Stm32L4(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32H7':
            self.driver = src.pystlink.lib.stm32h7.Stm32H7(self._stlink, dbg=self._dbg)
        else:
            self.driver = self._core

    def detect_cpu(self, expected_cpus, unmount=False):
        self._connector = src.pystlink.lib.stlinkusb.StlinkUsbConnector(dbg=self._dbg, serial=self._serial, index = self._index)
        if unmount:
            self._connector.unmount_discovery()
        self._stlink = src.pystlink.lib.stlinkv2.Stlink(self._connector, dbg=self._dbg)
        self._dbg.info("DEVICE: ST-Link/%s" % self._stlink.ver_str)
        self._dbg.info("SUPPLY: %.2fV" % self._stlink.target_voltage)
        self._dbg.verbose("COREID: %08x" % self._stlink.coreid)
        if self._stlink.coreid == 0:
            raise src.pystlink.lib.stlinkex.StlinkException('Not connected to CPU')
        self._core = src.pystlink.lib.stm32.Stm32(self._stlink, dbg=self._dbg)
        self.find_mcus_by_core()
        self._dbg.info("CORE:   %s" % self._mcus_by_core['core'])
        self.find_mcus_by_devid()
        self.find_mcus_by_flash_size()
        if expected_cpus:
            # filter detected MCUs by selected MCU type
            self.filter_detected_cpu(expected_cpus)
        self._dbg.info("MCU:    %s" % '/'.join([mcu['type'] for mcu in self._mcus]))
        self._dbg.info("FLASH:  %dKB" % self._flash_size)
        # self.find_sram_eeprom_size()
        self.load_driver()


    def ReadWord(self, address):
        data = self.driver.get_mem(address, 4)
        return f"{data[3]:02x}{data[2]:02x}{data[1]:02x}{data[0]:02x}"

    def ReadWords(self, address, num_words):
        num_bytes = num_words*4
        data = self.driver.get_mem(address, num_bytes)
        if len(data) != num_bytes:
            raise Exception("Error with data length when reading words")
        words = [""] * num_words
        for i in range(num_words):
            words[i] = f"{data[3+(i*4)]:02X}{data[2+(i*4)]:02X}{data[1+(i*4)]:02X}{data[0+(i*4)]:02X}"
        return words

    def WriteWord(self, address, value):
        print("Warning: WriteWord() isn't as simple to use as the -w32 function from ST-LINK_CLI.exe")
        print("         The memory location being written to may need to be unlocked\n")
        if len(value) != 8:
            raise Exception("Error with WriteWord(): value is invalid")
        self.WriteWords(address, value)

    def WriteWords(self, address, values):
        if type(values) != str:
            raise Exception("Error with WriteWords(): values must be a string")
        if len(values) % 8 != 0:
            raise Exception("Error with WriteWords(): values is invalid")
        data = []
        words = wrap(values, 8)
        for word in words:
            hex_bytes = wrap(word, 2)
            hex_bytes.reverse()
            hex_bytes = list(map(lambda x: int(x, 16), hex_bytes))
            data.extend(hex_bytes)
        print(data)
        self.driver.set_mem(address, data)


    def ProgramOTP(self, address, hex_data):
        if len(hex_data) == 0:
            raise Exception("OTP data can't be zero in length")
        if len(hex_data) % 8 != 0:
            raise Exception("OTP data is an invalid length")
        num_words = int(len(hex_data) / 8)
        blank_value = "FFFFFFFF" * num_words

        # Read OTP before attempting to write
        words = self.ReadWords(address, num_words)
        hex_data_read = "".join(words)

        if hex_data_read != hex_data:
            if hex_data_read == blank_value:

                # Unlock Flash
                self.driver.flash.enable_flash_programming()

                # Write to OTP
                self.WriteWords(address, hex_data)

                # Lock Flash
                self.driver.flash.disable_flash_programming()

                # Check what was witten to the OTP
                words = self.ReadWords(address, num_words)
                hex_data_read = "".join(words)
                if hex_data_read != hex_data:
                    if hex_data_read == blank_value:
                        print("Unable to write to OTP")
                        return 1
                    else:
                        print("Data not written correctly to OTP")
                        return 1
            else:
                print("Unable to write to OTP as OTP isn't blank")
                return 1
        return 0

    def read_file(self, filename):
        if filename.endswith('.srec'):
            srec = src.pystlink.lib.srec.Srec()
            srec.encode_file(filename)
            size = sum([len(i[1]) for i in srec.buffers])
            self._dbg.info("Loaded %d Bytes from %s file" % (size, filename))
            return srec.buffers
        with open(filename, 'rb') as f:
            data = list(f.read())
            self._dbg.info("Loaded %d Bytes from %s file" % (len(data), filename))
            return [(None, data)]

    def program_flash(self, firmware, erase=True, verify=True):
        mem = self.read_file(str(firmware))
        start_addr = src.pystlink.lib.stm32.Stm32.FLASH_START
        for addr, data in mem:
            if addr is None:
                addr = start_addr
            a = self._mcus_by_devid['erase_sizes']
            self.driver.flash_write(addr, data, erase=erase, erase_sizes=self._mcus_by_devid['erase_sizes'])
            self.driver.core_reset_halt()
            time.sleep(0.1)
            if verify:
                self.driver.core_halt()
                self.driver.flash_verify(addr, data)
        self.driver.core_run()


if __name__ == "__main__":
    pystlink = PyStlink()
