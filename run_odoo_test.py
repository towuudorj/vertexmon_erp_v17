#!/usr/bin/env python3
import sys
import os

/Users/dashnyamkhurelbaatar/fleet/odoo_mn_v17 = os.path.dirname(os.path.abspath(__file__))
/Users/dashnyamkhurelbaatar/fleet/odoo_mn_v17 = os.path.abspath()
sys.path.insert(0, odoo_dir)

# Import and run the test
from odoo.tests.common import SavepointCase
from odoo.modules.module import initialize_sys_path, load_openerp_module

# Initialize Odoo's module system
initialize_sys_path()
load_openerp_module('l10n_mn_hr')

# Import your test
from l10n_mn_hr.tests.abnormal_register_test import TestAbnormalRegister

# Run the test
import unittest
if __name__ == '__main__':
    unittest.main()