import unittest
from nvme_scan import get_args


class NvmeScanTestCase(unittest.TestCase):

    def test_01_linux_scan_all(self):
        test_args = []
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'ALL')
        self.assertIsNone(args.dev_ref)
        self.assertFalse(args.diff_scan)
        self.assertIsNone(args.data_file)

    def test_02_linux_scan_bdf(self):
        test_args = [
            "-b", "0000:0f:00.0"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'BDF')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertFalse(args.diff_scan)
        self.assertIsNone(args.data_file)

    def test_03_linux_scan_devnode(self):
        test_args = [
            "-n", "/dev/nvme0"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'NODE')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertFalse(args.diff_scan)
        self.assertIsNone(args.data_file)

    def test_04_linux_diff_all(self):
        test_args = [
            "-f", "sample_data_file.json"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'ALL')
        self.assertIsNone(args.dev_ref)
        self.assertTrue(args.diff_scan)
        self.assertEqual(args.data_file, test_args[1])

    def test_05_linux_diff_bdf(self):
        test_args = [
            "-b", "0000:0E:00.0",
            "-f", "sample_data_file.json"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'BDF')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertTrue(args.diff_scan)
        self.assertEqual(args.data_file, test_args[3])

    def test_06_linux_diff_devnode(self):
        test_args = [
            "-n", "/dev/nvme0",
            "-f", "sample_data_file.json"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'NODE')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertTrue(args.diff_scan)
        self.assertEqual(args.data_file, test_args[3])

    def test_07_linux_diff_missing_data(self):
        test_args = [
            "-n", "/dev/nvme0",
            "-f", "nonexisting_in_file.json"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'NODE')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertFalse(args.diff_scan)
        self.assertIsNone(args.data_file)

    def test_08_linux_diff_with_spdk(self):
        test_args = [
            "-n", "/dev/nvme0",
            "-f", "sample_data_file.json",
            "--spdk", "empty_spdk_dir"
        ]
        args = get_args(test_args)
        self.assertTrue(args.use_spdk)
        self.assertEqual(args.spdk_path, test_args[5])
        self.assertEqual(args.scan_type, 'NODE')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertTrue(args.diff_scan)
        self.assertEqual(args.data_file, test_args[3])

    def test_09_linux_diff_missing_spdk(self):
        test_args = [
            "-n", "/dev/nvme0",
            "-f", "sample_data_file.json",
            "--spdk", "nonexisting_spdk"
        ]
        args = get_args(test_args)
        self.assertFalse(args.use_spdk)
        self.assertIsNone(args.spdk_path)
        self.assertEqual(args.scan_type, 'NODE')
        self.assertEqual(args.dev_ref, test_args[1])
        self.assertTrue(args.diff_scan)
        self.assertEqual(args.data_file, test_args[3])


if __name__ == '__main__':
    unittest.main()
