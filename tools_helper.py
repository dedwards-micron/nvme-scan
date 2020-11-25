import subprocess
from paramiko import SSHClient, AutoAddPolicy


class LinuxToolsHelper(object):

    # this class is returned by any helper routine that gathers pcie path
    # data; typically from udevadm, but NOT lspci.
    class PCIePathHelper(object):

        def __init__(self, path_str, from_name=False):
            self._path_str = path_str
            # pcie_path is an array of PCIe BDF's in the PCIe hierarchy,
            # left most is parent, right most is target device.
            if from_name:
                self._pcie_path = path_str.split('/')[2:-2]
            else:
                self._pcie_path = path_str.split('/')[2:]

        def __repr__(self):
            return "{}".format(self._pcie_path)

        def __str__(self):
            return "/".join(self._pcie_path)

        # support iteration of the pcie path in reverse for human consumption.
        def __iter__(self):
            return self._pcie_path.reverse()

        def udev_path(self):
            return self._path_str

        def length(self):
            return len(str(self))

        def count(self):
            return len(self._pcie_path)

        # return the BDF of the PCIe endpoint device
        def endpoint(self):
            return self._pcie_path[-1]

        def bdf(self):
            return self.endpoint()

        # return the BDF of the upstream PCIe device (typically for reset purposes)
        def upstream(self):
            if len(self._pcie_path) >= 2:
                return self._pcie_path[-2]
            return None

        # return the BDF of the rootport PCIe device (top of the hierarchy)
        def root(self):
            return self._pcie_path[0]

    def __init__(self, ssh_login=None):
        self.client = None
        self.remote = not (ssh_login is None)
        if self.remote:
            login_ok = True
            for item_key in ssh_login.keys():
                if not (item_key in [ 'server_ip', 'user_name', 'user_pwd' ]):
                    login_ok = False
                    break
            if login_ok:
                self._r_connect(ssh_login)
            else:
                self.log('ERROR', "incomplete SSH login credentials provided!")

    # this can be overridden to log to an actual logger
    def log(self, err_lvl, msg_text):
        print("{}: {}".format(err_lvl, msg_text))

    def _r_is_connected(self):
        return not (self.client is None)

    def _r_connect(self, ssh_login):
        # create remote shell object and setup connection
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.load_system_host_keys()
        try:
            client.connect(ssh_login['server_ip'],
                           username=ssh_login['user_name'],
                           password=ssh_login['user_pwd'])
            self.client = client
        except Exception as exc:
            err_str = "EXCEPTION: ssh connection to host {} failed; returned:\n{}".format(ssh_login['server_ip'], exc)
            self.log('ERROR', err_str)
            self.client = None

    def _r_disconnect(self):
        self.client.close()
        self.client = None

    def _r_exec(self, cmd_list, cwd_opt):
        if not self._r_is_connected():
            self.log('ERROR', "ssh connection not established!")
            return 1, ""
        # Execute remote command
        cmd_str  = " ".join(cmd_list)
        ret_code = 0
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd_str)
            stdin.close()
            ret_text = ''.join(stderr.readlines())
            if len(ret_text) > 0:
                self.log('ERROR', "failure executing ssh {}, returned:\n{}".format(cmd_str, ret_text))
                ret_code = 1
            else:
                ret_text = ''.join(stdout.readlines())
        except Exception as exc:
            ret_text = "(EXCEPTION) failure executing ssh {}, returned:\n{}".format(cmd_str, exc)
            self.log('ERROR', ret_text)
            ret_code = 2
        return ret_code, ret_text

    def _l_exec(self, cmd_list, cwd_opt=None):
        try:
            cmd_exec = subprocess.Popen(cmd_list, cwd=cwd_opt,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True)
            stdout, stderr = cmd_exec.communicate()
            ret_code = cmd_exec.poll()
            if ret_code != 0:
                self.log('ERROR', "failure executing {}, returned:\n{}".format(" ".join(cmd_list), stderr))
        except Exception as exc:
            self.log('ERROR', "(EXCEPTION) failure executing {}, returned:\n{}".format(" ".join(cmd_list), exc))
            ret_code = 2
            stdout = "{}".format(exc)
        return ret_code, stdout

    def exec_str(self, cmd_str, cwd_opt=None):
        return self.exec(cmd_str.split(' '), cwd_opt)

    def exec(self, cmd_list, cwd_opt=None):
        if self.remote:
            return self._r_exec(cmd_list, cwd_opt)
        return self._l_exec(cmd_list, cwd_opt)

    # find_dev_nodes - this will locate device nodes in the /dev hierarchy by device type
    #   type:  c - char devices (default)
    #          b - block devices
    #
    # Example:
    #   node_list = find_dev_nodes('nvme*')
    #   --or--
    #   node_list = find_dev_nodes('nvme*', 'b')
    #
    # NOTE: nvme namespace devices are 'b' for "block" device nodes
    #
    def find_dev_nodes(self, search_name, type='c'):
        find_cmd = [ 'find', '/dev', '-type', type, '-name', search_name ]
        ret_code, out_str = self.exec(find_cmd)
        if (ret_code == 0) and (out_str != ''):
            ret_list = out_str.strip().split('\n')
        else:
            ret_list = []
        return ret_list

    def find_nvme_dev_nodes(self):
        # look for any nvme "char" driver nodes, these are the driver instances
        # one per PCIe BDF.  From here you can use the udevadm_get_path() to find
        # its PCIe relationship.
        return self.find_dev_nodes('nvme*', 'c')

    def find_nvme_namespace_dev_nodes(self):
        # look for any nvme "block" driver nodes, these are the logical namespace
        # devices one per attached namespace.
        return self.find_dev_nodes('nvme*', 'b')

    # Example:
    #   $ udevadm info -q path -n /dev/nvme0
    #   /devices/pci0000:00/0000:00:1c.4/0000:04:00.0/nvme/nvme0
    #
    # take the output from udevadm and return both the string (full path)
    # and break out the PCIe components into an array for parent / root
    # relationships.
    #
    def udevadm_get_path_by_name(self, dev_node):
        udev_cmd = [ 'udevadm', 'info', '-q', 'path', '-n', "{}".format(dev_node) ]
        ret_code, path_str = self.exec(udev_cmd)
        if ret_code == 0:
            path_hlpr = self.PCIePathHelper(path_str.strip(), from_name=True)
            return path_hlpr
        return None

    # Example:
    #   $ udevadm info -q path -p /sys/bus/pci/devices/<bdf>
    #   /devices/pci0000:00/0000:00:1c.4/0000:04:00.0/<bdf>
    #
    # take the output from udevadm and return both the string (full path)
    # and break out the PCIe components into an array for parent / root
    # relationships.
    #
    def udevadm_get_path_by_bdf(self, bdf):
        udev_cmd = [ 'udevadm', 'info', '-q', 'path', '-p', "/sys/bus/pci/devices/{}".format(bdf) ]
        ret_code, path_str = self.exec(udev_cmd)
        if ret_code == 0:
            path_hlpr = self.PCIePathHelper(path_str.strip(), from_name=False)
            return path_hlpr
        return None

    def lspci_get_bdf_list(self, filter="Non-"):
        lspci_cmd = [ 'lspci', '-D' ]
        ret_code, lspci_out = self.exec(lspci_cmd)
        if ret_code == 0:
            bdf_list    = lspci_out.split('\n')
            filter_flag = not (filter is None)
            if filter_flag:
                if len(filter) == 0:
                    filter_flag = False
            if filter_flag:
                filtered_bdfs = []
                for bdf_item in bdf_list:
                    if filter in bdf_item:
                        filtered_bdfs.append(bdf_item)
                bdf_list = filtered_bdfs
            # Take the list and generate a dictionary of 'bdf': 'title'
            ret_dict = {}
            for bdf_str in bdf_list:
                if len(bdf_str.strip()) == 0:
                    continue
                tokens = bdf_str.split(' ')
                pci_id = tokens[0].strip()
                title  = bdf_str[len(pci_id)+1:]
                ret_dict.update({ pci_id: title })
            return ret_dict
        return None
