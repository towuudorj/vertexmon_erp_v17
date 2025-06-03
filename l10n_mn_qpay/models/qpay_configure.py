# -*- coding: utf-8 -*-
##############################################################################
#
#    Tengersoft, Enterprise Management Solution    
#    Copyright (C) 2016-2020 Tengersoft Co.,ltd (<http://www.tengersoft.mn>). All Rights Reserved
#
#    Address : Suhkbaatar District, National ITPark, Tengersoft LLC
#    Email : info@tengersoft.mn
#    Phone : 976 + 75753060
#
##############################################################################

from odoo import models, fields, api, _

class qpay_configure(models.Model):
    _name = 'qpay.configure'
    _description = 'Qpay configure'
    
    operator_code = fields.Char(string='Operator code', required=True)
    name = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    url = fields.Char(string='Qpay url', required=True)
    token_url = fields.Char(string='Token url', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    config_date = fields.Date(string='Configure date')
    merchant_code = fields.Char(string='Merchant code', required=True)
    invoice_code = fields.Char(string='Invoice code')
    product_code = fields.Char(string='Product btuk code', required=True)
    phone = fields.Char(string='Phone', required=True)
    merchant_customer_code = fields.Char(string='Merchant user number', required=True)
    merchant_verification_code = fields.Char(string='Merchant key', required=True)
    note = fields.Char(string='Note')
    data_id = fields.Char(string='Data id')
    payment_check_url = fields.Char(string='Payment check url')
    vat_flag = fields.Selection([('0','None vat'),
                                 ('1','Vat')],string='Vat flag', required=True)
    type = fields.Selection([('1','QR picture'),
                             ('2','QR text')],string='Type', required=True)
                
