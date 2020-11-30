import argparse
import os
import json
from datetime import datetime
from tools_helper import LinuxToolsHelper


class NvmeScanOptions(object):
    def __init__(self):
        self.use_spdk  = False
        self.spdk_path = None
        self.scan_type = 'ALL'
        self.dev_ref   = None
        self.diff_scan = False
        self.data_file = None

    def set_scan_bdf(self, bdf):
        self.scan_type = 'BDF'
        self.dev_ref   = bdf

    def set_scan_node(self, dev_node):
        self.scan_type = 'NODE'
        self.dev_ref   = dev_node

    def set_spdk(self, spdk_path):
        if os.path.isdir(spdk_path):
            self.use_spdk  = True
            self.spdk_path = spdk_path
            # TODO: get SPDK version, verify compatibility
        else:
            print("ERR: invalid SPDK path {}, ignoring input".format(spdk_path))
            return 1
        return 0

    def set_data_file(self, file_path):
        if os.path.isfile(file_path):
            self.diff_scan = True
            self.data_file = file_path
            # TODO: load data file into local dictionary object
        else:
            print("ERR: invalid data file {} specified, ignoring input".format(file_path))
            return 1
        return 0


def get_args(args_test=None):
    parser = argparse.ArgumentParser(prog="NVMe device scan CLI")
    parser.add_argument('--spdk', required=False, dest='spdk', default=None,
                        help='Path to spdk src code folder, use SPDK to gather information.')
    parser.add_argument('-f', '--file', required=False, dest='data_file_in', default=None,
                        help='Rescan specific devices by BDF (-b) or dev node (-n).')
    parser.add_argument('-b', '--bdf', required=False, dest='bdf', default=None,
                        help='Rescan by device DBDF e.g. -b 0000:02:00.0.')
    parser.add_argument('-n', '--node', required=False, dest='dev_node', default=None,
                        help='Rescan by dev node name e.g. -n /dev/nvme0')
    if args_test is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args_test)
    ret_args = NvmeScanOptions()
    #
    # check for scan using SPDK tools
    if not (args.spdk is None):
        ret_args.set_spdk(args.spdk)
    # check for single device, or ALL device scan
    if not (args.bdf is None):
        # we have a BDF specified, scan for a single device only
        ret_args.set_scan_bdf(args.bdf)
    if not (args.dev_node is None):
        # we have a device node specified, scan for a single device only
        ret_args.set_scan_node(args.dev_node)
    # determine if we are doing a change scan, or fresh scan
    if not (args.data_file_in is None):
        ret_args.set_data_file(args.data_file_in)
    return ret_args


class NvmeDeviceCollector(object):

    # (optional) argument full_scan:<dict> data from a previous scan
    #            can be loaded in to perform diff any time.
    #
    def __init__(self, **kwargs):
        # TODO: implement option to connect to remote server over ssh
        self.tools_hlpr = LinuxToolsHelper()
        self.full_scan  = kwargs.get('full_scan', {})

    def diff_scan(self, prev_scan):
        raise NotImplemented("ERROR: not implemented yet!")

    # Returns a dictionary object containing structured device information.
    # Elements of each dictionary item are similar and designed to allow lookup
    # of different things based on what you want.
    #
    def new_scan(self):
        timestamp = datetime.now().isoformat()
        # scan host for devices as they exist upon instantiation
        #   o node_list  tells you which pcie devices have initialized successfully
        #   o block_list tells you which namespaces are attached (not much else)
        node_list  = self.tools_hlpr.find_nvme_dev_nodes()
        temp_list  = self.tools_hlpr.find_nvme_namespace_dev_nodes()
        # NOTE: kernel 5.something changed some things about namespaces, there is a
        #       new set of block devices with 'p#' appended /dev/nvme0n1p1, I don't
        #       want these because they all map back to the same BDF but do NOT map
        #       to the drive query for namespaces.
        block_list = []
        for temp_block_dev in temp_list:
            tokens = temp_block_dev.strip().split('p')
            if len(tokens) == 1:
                # only keep block nodes without 'p' identifiers
                block_list.append(temp_block_dev)
        # TODO: add parsing of udev "driver" path for block devices to associate namespaces to char devices
        # Build SSD namespace list database
        namespace_list  = []
        ns_bdf_lookup   = {}
        block_lookup    = {}
        for block_node in block_list:
            pcie_path = self.tools_hlpr.udevadm_get_path_by_name(block_node)
            bdf       = pcie_path.bdf()
            ns_data   = {
                'type':       'id_namespace',
                'bdf':        bdf,
                'block_node': block_node,
                'udev_path':  pcie_path.udev_path(),
                # these ones must be active because they are visible to the os
                'attach':     True,
                # place holders for controller query (later)
                'nsid':       None,
                'id_ns':      None
            }
            namespace_list.append(ns_data)
            ns_bdf_lookup.update({ bdf: ns_data })
            block_lookup.update({ block_node: ns_data})

        # Build SSD device list database
        controller_list = []
        bdf_lookup      = {}
        node_lookup     = {}
        ns_lookup       = {}
        for dev_node in node_list:
            # match controller to namespaces and determine attach state
            ns_list   = self.tools_hlpr.nvme_get_ns_list(dev_node)
            pcie_path = self.tools_hlpr.udevadm_get_path_by_name(dev_node)
            bdf       = pcie_path.bdf()
            id_ctrlr  = self.tools_hlpr.nvme_get_ctrl_identify(dev_node)
            dev_data  = {
                'type':      'id_controller',
                'bdf':       bdf,
                'upstream':  pcie_path.upstream(),
                'dev_node':  dev_node,
                'cntlid':    id_ctrlr['cntlid'],
                'udev_path': pcie_path.udev_path(),
                'id_ctrl':   id_ctrlr,
                'list_ns':   ns_list
            }
            controller_list.append(dev_data)
            bdf_lookup.update({ bdf: dev_data })
            node_lookup.update({ dev_node: dev_data })
            # match block devices to reported namespaces
            for ns_data in namespace_list:
                if ns_data['bdf'] == bdf:
                    # block node will be unique so use dict for quick lookup
                    ns_lookup.update({ns_data['block_node']: dev_data})
        # save off full scan data for diff
        self.full_scan = {
            'ctrl_list':   controller_list,
            'lu_bdf':      bdf_lookup,
            'lu_dev_node': node_lookup,
            'lu_ns':       ns_lookup
        }
        return self.full_scan

    # determine supported features; of interest are:
    #  o dual port controllers, virtualization mgmt (VFs)
    #  o nvm sets, and endurance sets; from this build
    #    supported features.
    def parse_features(self, full_scan):
        # TODO: implement data parsing of identify controller data.
        feature_obj = {}
        return feature_obj

    def __str__(self):
        return json.dumps(self.full_scan)


# main execution routine IF this is run as a script
if __name__ == '__main__':
    cli_args   = get_args()
    if cli_args.diff_scan:
        # perform a DIFF scan from the input file; which means we don't scan
        # the current visible device list, we use the input file as a basis
        # for the device list, then update the information and taking note
        # where something changed, or is no longer accessible.
        print("TODO: implement diff scan")
    else:
        # scan all PCIe and NVMe devices and build a new data structure.
        print("TODO: implement new scan")

