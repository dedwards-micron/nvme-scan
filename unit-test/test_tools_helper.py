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

    def _get_nvme_dev_nodes(self, tool_hlpr):
        # get nvme device nodes
        dev_list = tool_hlpr.find_nvme_dev_nodes()
        # we expect to find at least one ssd
        self.assertTrue(len(dev_list) > 0)
        return dev_list

    def _get_ssd_bdf_list(self, tool_hlpr):
        # get ssd PCIe device list
        bdf_list = tool_hlpr.lspci_get_bdf_list()
        self.assertTrue(len(bdf_list) > 0)
        return bdf_list

    def _get_path_by_dev_node(self, tool_hlpr, dev_node):
        pcie_path = tool_hlpr.udevadm_get_path_by_name(dev_node)
        self.assertIsNotNone(pcie_path)
        # there should be at least a root and an endpoint
        self.assertTrue(pcie_path.length() > 0)
        self.assertTrue(pcie_path.count() > 1)
        return pcie_path

    def _get_path_by_bdf(self, tool_hlpr, bdf):
        pcie_path = tool_hlpr.udevadm_get_path_by_bdf(bdf)
        self.assertIsNotNone(pcie_path)
        # there should be at least a root and an endpoint
        self.assertTrue(pcie_path.length() > 1)
        self.assertTrue(pcie_path.count() > 1)
        return pcie_path

    def _dev_list_to_pcie_path_dict(self, tools_hlpr, dev_list):
        ret_list = {}
        # create a dictionary of bdf to dev_node lookup to get pcie_path objs,
        # as well as a lookup by dev_node to get same obj.
        for dev_node in dev_list:
            pcie_path = self._get_path_by_dev_node(tools_hlpr, dev_node)
            self.assertIsNotNone(pcie_path)
            dev_bdf  = pcie_path.bdf()
            ret_item = { dev_bdf:  { 'dev_node': dev_node, 'pcie_path': pcie_path },
                         dev_node: { 'dev_bdf':  dev_bdf,  'pcie_path': pcie_path }
                       }
            ret_list.update(ret_item)
        return ret_list

    def test_07_local_udevadm_get_nvme_by_name(self):
        local_tools = LinuxToolsHelper()
        # client must be an SSHClient object when connection is successful
        self.assertIsNone(local_tools.client)
        # remote must be True when credentials are supplied
        self.assertFalse(local_tools.remote)
        bdf_list = self._get_ssd_bdf_list(local_tools)
        dev_list = self._get_nvme_dev_nodes(local_tools)
        # we expect to find the same number of NVMe dev nodes, as SSD BDFs
        self.assertTrue(len(dev_list) == len(bdf_list))
        # gather udevadm information on the nvme devices found
        print("test_07_remote_udevadm_get_nvme_paths: local NVMe udevadm info")
        for dev_node in dev_list:
            pcie_path = self._get_path_by_dev_node(local_tools, dev_node)
            # verify the BDF in the nvme dev node path is in the bdf list
            bdf_from_devnode = pcie_path.bdf()
            self.assertTrue(bdf_from_devnode in bdf_list.keys())
            print(" -> NVMe dev node: {} - bdf={}, path={}".format(dev_node, bdf_from_devnode, pcie_path))

    # test of udevadm_get_by_bdf, and trace path of BDF back to devnode path!
    def test_08_local_udevadm_get_by_bdf(self):
        local_tools = LinuxToolsHelper()
        bdf_list = self._get_ssd_bdf_list(local_tools)
        dev_list = self._get_nvme_dev_nodes(local_tools)
        path_lookup = self._dev_list_to_pcie_path_dict(local_tools, dev_list)
        print("test_08_local_udevadm_get_by_bdf: local bdf path via udevadm")
        for dev_bdf in bdf_list:
            # This is actually the method we are trying to test; lots of setup
            # to correlate with other findings.
            bdf_path = self._get_path_by_bdf(local_tools, dev_bdf)
            # Trace path of items found in the bdf list back to the dev node
            path_lu  = path_lookup.get(dev_bdf, None)
            self.assertIsNotNone(path_lu)
            bdf_lu   = path_lu.get('pcie_path', None)
            self.assertIsNotNone(bdf_lu)
            self.assertEqual(bdf_path.__str__(), bdf_lu.__str__())
            print(" -> matched: {}".format(bdf_path))

    # test helper functions of PCIePathHelper
    def test_09_pcie_path_helpers(self):
        # negative test cases for bad path string
        with self.assertRaises(ValueError):
            LinuxToolsHelper.PCIePathHelper('')
        with self.assertRaises(IndexError):
            LinuxToolsHelper.PCIePathHelper('/onenode')
        with self.assertRaises(IndexError):
            LinuxToolsHelper.PCIePathHelper('/twonodes')
        # these should pass even though they aren't real PCIe bdfs
        from_bdf_path = LinuxToolsHelper.PCIePathHelper('/devices/pcieRootComplex/myNvmeDevice')
        self.assertEqual(from_bdf_path.bdf(), 'myNvmeDevice')
        self.assertEqual(from_bdf_path.root(), 'pcieRootComplex')
        # here the upstream (parent) is the same as the root complex
        self.assertEqual(from_bdf_path.upstream(), 'pcieRootComplex')
        # make this one have an upstream, non-root complex parent
        name_path_str = "/devices/pcieRootComplex/upstreamBDF/myNvmeDevice/nvme/nvmeXYZ"
        from_name_path = LinuxToolsHelper.PCIePathHelper(name_path_str, from_name=True)
        self.assertEqual(from_name_path.bdf(), 'myNvmeDevice')
        self.assertEqual(from_name_path.root(), 'pcieRootComplex')
        self.assertEqual(from_name_path.upstream(), 'upstreamBDF')

    # TODO: add negative tests for items that return None
    def test_10_negative_test_returns_none(self):
        local_tools = LinuxToolsHelper()
        self.assertIsNone(local_tools.udevadm_get_path_by_bdf('i:cant:drive.55'))
        self.assertIsNone(local_tools.udevadm_get_path_by_name('/dev/nosuchdev'))
        empty_dict = local_tools.lspci_get_bdf_list(filter="no-such-dev_filter")
        self.assertIsNone(empty_dict)

    def test_11_nvme_get_ns_list(self):
        local_tools = LinuxToolsHelper()
        dev_nodes   = local_tools.find_nvme_dev_nodes()
        for dev_node in dev_nodes:
            ns_list = local_tools.nvme_get_ns_list(dev_node)
            self.assertTrue(len(ns_list) > 0)
            print(" -> NS List:\n{}".format(ns_list))

    def _get_ctrl_identify(self, tools_hlpr, dev_node):
        id_ctrl = tools_hlpr.nvme_get_ctrl_identify(dev_node)
        self.assertIsNotNone(id_ctrl)
        self.assertIsNotNone(id_ctrl.get('cntlid', None))
        self.assertIsNotNone(id_ctrl.get('sn', None))
        self.assertIsNotNone(id_ctrl.get('mn', None))
        print(" -> dev node: {}, ctrl_id: {}, sn: {}, model: {}".format(dev_node,
                                                                        id_ctrl['cntlid'],
                                                                        id_ctrl['sn'].strip(),
                                                                        id_ctrl['mn'].strip()))
        return id_ctrl

    def test_12_nvme_get_ctrl_identify(self):
        local_tools = LinuxToolsHelper()
        dev_nodes   = local_tools.find_nvme_dev_nodes()
        self.assertIsNotNone(dev_nodes)
        self._get_ctrl_identify(local_tools, dev_nodes[0])

    def test_13_nvme_get_ctrl_identify_by_id(self):
        local_tools = LinuxToolsHelper()
        dev_nodes   = local_tools.find_nvme_dev_nodes()
        self.assertIsNotNone(dev_nodes)
        dev_node    = dev_nodes[0]
        print("test_13_nvme_get_ctrl_identify_by_id: chose dev node={}".format(dev_node))
        id_ctrl     = self._get_ctrl_identify(local_tools, dev_node)
        ctrl_id     = id_ctrl['cntlid']
        alt_id_ctrl = local_tools.nvme_get_ctrl_identify_by_id(dev_node, ctrl_id)
        if not (alt_id_ctrl is None):
            # results from this query should be identical in both methods
            self.assertEqual(alt_id_ctrl.get('cntlid', None), id_ctrl['cntlid'])
            self.assertEqual(alt_id_ctrl.get('sn', None),     id_ctrl['sn'])
            self.assertEqual(alt_id_ctrl.get('mn', None),     id_ctrl['mn'])
            print(" -> id_ctrl (by id) confirmed for: {}".format(dev_node))


if __name__ == '__main__':
    unittest.main()
