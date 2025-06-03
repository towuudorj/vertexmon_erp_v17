# -*- coding: utf-8 -*-
import time
import math

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
from dateutil.relativedelta import relativedelta
import calendar
from odoo.http import request
import json, requests
from requests.auth import HTTPBasicAuth 
import base64


class bank_gateway_configure(models.Model):
    _name = 'bank.gateway.configure'
    _description = 'Khanbank configure'
    
    
    bank_type = fields.Selection([('khanbank','Khanbank'),
                                  ('capitron_bank','Capitron bank'),
                                  ('tdb_bank','TDB Bank')],string='Bank type')
    name = fields.Char(string='Bank gateway configure name')
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env['res.company']._company_default_get('bank.gateway.configure'))
    register_date = fields.Date(string='Register date')
    register_user_id = fields.Many2one('res.users',string='Register user',default=lambda self: self.env.user)
    user_name = fields.Char(string='User name')
    password = fields.Char('Password')
    login_name = fields.Char('Login name')
    transaction_password = fields.Char('Transaction password')
    auth_token_url = fields.Char(string='Authorize token url')
    token_session_time = fields.Integer(string='Token session time')
    token_code = fields.Char(string='Token code')
    account_list_url = fields.Char(string='Account list url')
    account_balance_check_url = fields.Char(string='Account balance check url')
    account_info_check_url = fields.Char(string='Account info check url')
    account_statement_check_url = fields.Char(string='Account statement check url')
    account_name_check_url = fields.Char(string='Account name check url')
    account_local_transfer_url = fields.Char(string='Account local transfer url')
    account_interbank_transfer_url = fields.Char(string='Account interbank transfer url')
    account_salary_transfer_url = fields.Char(string='Account salary transfer url')
    account_internationalbank_transfer_url = fields.Char(string='Account international bank transfer url')
    account_rate_check_url = fields.Char(string='Currency rate check url')
    account_list_line_id = fields.One2many('bank.gateway.account.list','bank_config_id',string="Account bank lists")
    desc = fields.Text(string='Description')
    
    request_url = fields.Char(string='Request url',required=True)
    currency_data_seq = fields.Char(string='Currency data sequence')
    cert_file_url = fields.Char('Certificate file url',required=True)
    cert_password = fields.Char('Certificate password',required=True)
    tran_download_seq = fields.Char('Transaction download sequence',required=True)
    bank_data_seq = fields.Char(string='Bank data sequence',required=True)
    balance_check_seq = fields.Char(string='Balance check sequence',required=True)
    
    role_id = fields.Integer('Role id')
    password_type_one = fields.Selection([('1','Login password'),
                                      ('2','Transaction password')],'Login Password type',default='1')
    password_type_two = fields.Selection([('1','Login password'),
                                      ('2','Transaction password')],'Transaction Password type',default='2')
    language = fields.Selection([('0','Mongolia'),
                                 ('1','Other language')],'Language',default='0')
    anybic = fields.Char('Any bic code')
                
                
                
                
    def get_capitron_token(self):
        token = '0'
        parameter = {
                    'user_no':'%s'%self.user_name,
                    'password':'%s'%self.password,
                    }
        request = requests.post(self.auth_token_url, params = parameter)
        data = request.text.encode("utf-8")
        if request.status_code == 200:
            jdata = json.loads(data)
            token = jdata['token']
            self.write({'token_code':token})
        else:
            self.write({'desc':data,})
            raise UserrError(_(u'Холболтын алдаа гарсан тул шалгана уу.'))
        
        return True
            
    
    def get_account_list(self):
        account_list_obj = self.env['bank.gateway.account.list']
        currency_obj = self.env['res.currency']
        header  = {
                    'Authorization':'Bearer %s'%self.token_code,
                    'Content-Type':'application/x-www-form-urlencoded',
                     }
        request = requests.get(self.account_list_url,headers=header)
        data = request.text.encode("utf-8")
        if request.status_code == 200:
            jdata = json.loads(data)
            for acc_line in jdata['accounts']:
                currency_id = currency_obj.search([('name','=',acc_line['currency'])])
                account_list_id = account_list_obj.search([('number','=',acc_line['number'])])
                if account_list_id.id == False:
                    account_list_obj.create( {
                                                'name':u'%s'%acc_line['name'],
                                                'status':acc_line['status'],
                                                'currency':currency_id.id,
                                                'bank_config_id':self.id,
                                                'number':acc_line['number'],
                                                'company_id':self.company_id.id,
                                                'balance':float(acc_line['balance']),
                                                'avalaible_balance':float(acc_line['avalaibleBalance']),
                                                'type':u'%s'%acc_line['type'],
                                                'hold_balance':float(acc_line['holdBalance']),
                                                })
        else:
            raise UserError(u'Холболтын алдаа гарсан тул шалгана уу.')
        
        return True

    def get_token(self):
        
        token = '0'
        token_time = 0
        
        header  = {
                    'Content-Type':'application/x-www-form-urlencoded',
                     }
        parameter = {
                'grant_type':'client_credentials',
                }
        request = requests.post(self.auth_token_url, auth=HTTPBasicAuth('%s'%self.user_name, '%s'%self.password),params = parameter,headers=header)
        data = request.text.encode("utf-8")
        
        if request.status_code == 200:
            jdata = json.loads(data)
            token = jdata['access_token']
            token_time = jdata['access_token_expires_in']
            self.write({'token_code':token,
                        'token_session_time':token_time})
        else:
            raise UserError(u'Холболтын алдаа гарсан тул шалгана уу.')

        return True
    
    
class bank_gateway_account_list(models.Model):
    _name = 'bank.gateway.account.list'
    _description = 'Khanbank account list'
    
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env['res.company']._company_default_get('bank.gateway.account.list'))
    number = fields.Char(string='Account number')
    type = fields.Selection([('L','Loan'),
                             ('D','Debit')],string='Type',default='D')
    currency = fields.Many2one('res.currency','Currency')
    open_date = fields.Date(string='Open date')
    in_method = fields.Char(string='In method')
    in_rate = fields.Char(string='In rate')
    customer_name = fields.Char(string='Customer name')
    business_phone = fields.Char(string='Business Phone')
    last_maintence_date = fields.Date(string='Last Maintence Date')
    last_financial_tran_date = fields.Date(string='Last financial transaction date')
    home_phone = fields.Char(string='Home Phone')
    status = fields.Char(string='Status')
    balance = fields.Float(string='Balance')
    name = fields.Char(string='Account name')
    hold_balance = fields.Float(string='Hold balance')
    avalaible_balance = fields.Float(string='Avalaible balance')
    bank_config_id = fields.Many2one('bank.gateway.configure',string='KhanBank configure')  
    
    
    
    def get_account_info(self):
        account_list_obj = self.env['bank.gateway.account.list']
        header  = {
                    'Authorization':'Bearer %s'%self.bank_config_id.token_code,
                    'Content-Type':'application/x-www-form-urlencoded',
                     }
        
        acc_info_url  = self.bank_config_id.account_info_check_url+self.number+"/"
        request = requests.get(acc_info_url,headers=header)
        data = request.text.encode("utf-8")
        if request.status_code == 200:
            jdata = json.loads(data)
            self.write({
                        'business_phone':jdata['account']['businessPhone'],
                        'in_method':jdata['account']['intMethod'],
                        'in_rate':jdata['account']['intRate'],
                      #  'home_phone':jdata['account']['homePhone'],
                      #  'open_date':jdata['account']['openDate'],
                        'customer_name':jdata['account']['customerName'],
                    #    'last_maintence_date':jdata['account']['lastMaintenanceDate'],
                    #    'last_financial_tran_date':jdata['account']['lastFinancialTranDate'],
                        })
        else:
            raise UserError(u'Холболтын алдаа гарсан тул шалгана уу.')
        return True
    
    
    

             
    
    def get_create_account(self):
        account_obj = self.env['account.account']
        header  = {
                    'Content-Type':'application/x-www-form-urlencoded',
                     }
        parameter = {
                'grant_type':'client_credentials',
                }
        request = requests.post(self.auth_token_url, auth=HTTPBasicAuth('%s'%self.user_name, '%s'%self.password),params = parameter,headers=header)
        if request.status_code == 200:
            account_obj.create({})
        else:
            
            raise UserError(u'Холболтын алдаа гарсан тул шалгана уу.')
        return True
    