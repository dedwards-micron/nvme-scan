import argparse
import os


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


# main execution routine IF this is run as a script
if __name__ == '__main__':
    cli_args = get_args()
    if cli_args.diff_scan:
        # perform a DIFF scan from the input file; which means we don't scan
        # the current visible device list, we use the input file as a basis
        # for the device list, then update the information and taking note
        # where something changed, or is no longer accessible.
        print("TODO: implement diff scan")
    else:
        # scan all PCIe and NVMe devices and build a new data structure.
        print("TODO: implement new scan")

