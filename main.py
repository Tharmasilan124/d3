import subprocess

# CSR bit definitions
FEN_BIT     = 1 << 0    
HALT_BIT    = 1 << 5     
IBCNT_SHIFT = 8       
IBOVF_BIT   = 1 << 16    
IBCLR_BIT   = 1 << 17

class Uad:
    def __init__(self):
        self.inst = None

    # ------------------ Low-level commands ------------------
    def run_cmd(self, *args):
        """Run a command, suppress output, return True if successful"""
        try:
            subprocess.run([self.inst] + list(args), shell=True, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def run_cmd_output(self, *args):
        """Run a command and get output, suppress errors"""
        try:
            out = subprocess.check_output([self.inst] + list(args), shell=True,
                                          stderr=subprocess.DEVNULL)
            return out.decode().strip()
        except subprocess.CalledProcessError:
            return None

    # ------------------ Low-level actions ------------------
    def reset(self):
        self.run_cmd('com', '--action', 'reset')

    def disable(self):
        self.run_cmd('com', '--action', 'disable')

    def enable(self):
        self.run_cmd('com', '--action', 'enable')

    def drive_signal(self, value):
        self.run_cmd('sig', '--data', str(value))

    # ------------------ CSR read/write ------------------
    def read_CSR(self):
        out = self.run_cmd_output('cfg', '--address', '0x0')
        if out is None:
            return None
        try:
            return int(out, 0)
        except ValueError:
            return None

    def write_CSR(self, value):
        self.run_cmd('cfg', '--address', '0x0', '--data', hex(value))

    # ------------------ Test methods ------------------
    def test_enable_disable(self):
        self.reset()
        self.enable()
        csr_enable = self.read_CSR()
        self.disable()
        csr_disable = self.read_CSR()
        return csr_enable, csr_disable

    def test_bypass(self):
        self.reset()
        self.enable()
        self.write_CSR(0x0)
        self.drive_signal(0x40)
        return "Bypass test done"

    def test_buffer_count(self):
        self.reset()
        self.enable()
        csr = self.read_CSR()
        if csr is None:
            return None
        self.write_CSR(csr | HALT_BIT)
        self.drive_signal(0x10)
        csr = self.read_CSR()
        if csr is None:
            return None
        ibcnt = (csr >> IBCNT_SHIFT) & 0xFF
        return ibcnt

    def test_overflow(self):
        self.reset()
        self.enable()
        csr = self.read_CSR()
        if csr is None:
            return None
        self.write_CSR(csr | HALT_BIT)
        for i in range(260):
            self.drive_signal(i)
        csr = self.read_CSR()
        if csr is None:
            return None
        overflow = (csr & IBOVF_BIT) >> 16
        return overflow

    def test_clear_buffer(self):
        self.write_CSR(IBCLR_BIT)
        csr = self.read_CSR()
        if csr is None:
            return None, None
        ibcnt = (csr >> IBCNT_SHIFT) & 0xFF
        overflow = (csr & IBOVF_BIT) >> 16
        return ibcnt, overflow

    # ------------------ Run all tests and return results ------------------
    def run_all_tests(self):
        results = {}
        results['Enable/Disable'] = self.test_enable_disable()
        results['Bypass'] = self.test_bypass()
        results['Buffer Count'] = self.test_buffer_count()
        results['Overflow'] = self.test_overflow()
        results['Clear Buffer'] = self.test_clear_buffer()
        return results


# ------------------ Main script ------------------
if __name__ == "__main__":
    instances = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]

    for inst_name in instances:
        uad = Uad()
        uad.inst = inst_name
        results = uad.run_all_tests()
        print(f"\n[{inst_name}] Test Results")
        print(f" Enable/Disable CSR: Enable={hex(results['Enable/Disable'][0]) if results['Enable/Disable'][0] is not None else 'ERROR'} "
              f"Disable={hex(results['Enable/Disable'][1]) if results['Enable/Disable'][1] is not None else 'ERROR'}")
        print(f" Bypass Test: {results['Bypass']}")
        print(f" Buffer Count: {results['Buffer Count'] if results['Buffer Count'] is not None else 'ERROR'}")
        print(f" Overflow Flag: {results['Overflow'] if results['Overflow'] is not None else 'ERROR'}")
        ibcnt, overflow = results['Clear Buffer']
        print(f" Clear Buffer: Count={ibcnt if ibcnt is not None else 'ERROR'}, Overflow={overflow if overflow is not None else 'ERROR'}")
