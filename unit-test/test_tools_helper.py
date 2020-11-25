import os
import unittest
from tools_helper import LinuxToolsHelper
from paramiko import SSHClient


class ToolsHelperTestCase(unittest.TestCase):
    # DO NOT PUT ACTUAL USER NAME AND PWD HERE - USE IDE ENV VARS IN RUN CONFIG
    local_user = os.getenv('LOCAL_USER')
    local_pwd  = os.getenv('LOCAL_PWD')

    def print_bdf_list(self, bdf_list):
        # example of how to use the return data
        for bdf in bdf_list.keys():
            print(" -> found SSD device: {}".format(bdf))

    def test_01_local_get_bdf_list(self):
        tools        = LinuxToolsHelper()
        # when we pass None for a filter, we should get every device
        all_devs     = tools.lspci_get_bdf_list(filter=None)
        # when we specify "Non-Volatile" we should get a list of nvme devices
        ssd_devs     = tools.lspci_get_bdf_list(filter="Non-Volatile")
        self.assertTrue(len(all_devs) > len(ssd_devs))
        # when we don't set any filter, the default is to search for "Non-" which
        # will also give us all SSDs (they should return the same list
        default_devs = tools.lspci_get_bdf_list()
        self.assertEqual(len(ssd_devs), len(default_devs))
        print("test_01_local_get_bdf_list: local ssd devices")
        self.print_bdf_list(ssd_devs)

    def test_02_remote_invalid_host(self):
        # make sure we raise an exception with invalid credentials
        invalid_login = {'server_ip': 'noserver.no.where',
                         'user_name':  self.local_user,
                         'user_pwd':   self.local_pwd
                         }
        remote_tools = LinuxToolsHelper(invalid_login)
        # client must None when connections fail
        self.assertIsNone(remote_tools.client)
        # remote must be True when credentials are supplied
        self.assertTrue(remote_tools.remote)

    def test_03_remote_invalid_user(self):
        # make sure we raise an exception with invalid credentials
        invalid_login = {'server_ip':  'localhost',
                         'user_name':  'joseph_blow',
                         'user_pwd':   'blowawayjoe'
                         }
        remote_tools = LinuxToolsHelper(invalid_login)
        # client must None when connections fail
        self.assertIsNone(remote_tools.client)
        # remote must be True when credentials are supplied
        self.assertTrue(remote_tools.remote)

    def test_04_remote_invalid_pwd(self):
        # make sure we raise an exception with invalid credentials
        invalid_login = {'server_ip': 'localhost',
                         'user_name': self.local_user,
                         'user_pwd':  'bad password here'
                         }
        remote_tools = LinuxToolsHelper(invalid_login)
        # client must None when connections fail
        self.assertIsNone(remote_tools.client)
        # remote must be True when credentials are supplied
        self.assertTrue(remote_tools.remote)

    def test_05_remote_get_bdf_list(self):
        local_tools  = LinuxToolsHelper()
        local_devs   = local_tools.lspci_get_bdf_list(filter=None)
        # make sure we do NOT fail local login
        valid_login = {'server_ip': 'localhost',
                       'user_name': self.local_user,
                       'user_pwd':  self.local_pwd
                       }
        remote_tools = LinuxToolsHelper(valid_login)
        # client must be an SSHClient object when connection is successful
        self.assertTrue(isinstance(remote_tools.client, SSHClient))
        # remote must be True when credentials are supplied
        self.assertTrue(remote_tools.remote)
        # grab the same list of devices as a local run, and compare
        remote_devs  = remote_tools.lspci_get_bdf_list(filter=None)
        for pci_id in local_devs.keys():
            self.assertTrue(pci_id in remote_devs.keys())

    def test_06_local_find_nvme_dev_nodes(self):
        local_tools = LinuxToolsHelper()
        dev_list    = local_tools.find_nvme_dev_nodes()
        self.assertTrue(len(dev_list) > 0)
        # verify that the string 'nvme' is within every dev node
        print("test_06_local_find_nvme_dev_nodes: local NVMe dev nodes")
        for dev_node in dev_list:
            print(" -> found NVMe dev node: {}".format(dev_node))
            self.assertTrue('nvme' in dev_node)

    def test_07_local_udevadm_get_nvme_by_name(self):
        local_tools = LinuxToolsHelper()
        # client must be an SSHClient object when connection is successful
        self.assertIsNone(local_tools.client)
        # remote must be True when credentials are supplied
        self.assertFalse(local_tools.remote)
        # get ssd PCIe device list
        bdf_list = local_tools.lspci_get_bdf_list()
        self.assertTrue(len(bdf_list) > 0)
        # get nvme device nodes
        dev_list = local_tools.find_nvme_dev_nodes()
        # we expect to find the same number of NVMe dev nodes, as SSD BDFs
        self.assertTrue(len(dev_list) == len(bdf_list))
        # gather udevadm information on the nvme devices found
        print("test_07_remote_udevadm_get_nvme_paths: local NVMe udevadm info")
        for dev_node in dev_list:
            pcie_path = local_tools.udevadm_get_path_by_name(dev_node)
            self.assertTrue(pcie_path.length() > 0)
            # there should be at least a root and an endpoint
            self.assertTrue(pcie_path.count() > 1)
            # verify the BDF in the nvme dev node path is in the bdf list
            bdf_from_devnode = pcie_path.bdf()
            self.assertTrue(bdf_from_devnode in bdf_list.keys())
            print(" -> NVMe dev node: {} - bdf={}, path={}".format(dev_node, bdf_from_devnode, pcie_path))

# TODO: add test of udevadm_get_by_bdf, and trace path of BDF back to devnode path!
# TODO: test helper functions of PCIePathHelper

if __name__ == '__main__':
    unittest.main()
