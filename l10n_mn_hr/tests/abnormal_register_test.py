import unittest 
from odoo.tests.common import TransactionCase

class TestAbnormalRegister(TransactionCase):

    def setUp(self):
        super(TestAbnormalRegister, self).setUp()
        self.AbnormalRegister = self.env['abnormal.register']
        self.Company = self.env['res.company']

        # Create a company
        self.company = self.Company.create({
            'name': 'Test Company',
        })

    def test_create_abnormal_register(self):
        # Test the creation of an abnormal register
        abnormal_register = self.AbnormalRegister.create({
            'name': 'Test Abnormal Register',
            'company_id': self.company.id,
        })
        self.assertTrue(abnormal_register, "Abnormal Register should be created")
        self.assertEqual(abnormal_register.name, 'Test Abnormal Register', "Abnormal Register name should be 'Test Abnormal Register'")
        self.assertEqual(abnormal_register.company_id, self.company, "Abnormal Register should be linked to the correct company")

if __name__ == '__main__':
    unittest.main()