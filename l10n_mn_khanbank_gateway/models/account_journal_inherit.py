# -*- coding: # -*- coding: utf-8 -*-
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

class account_journal(models.Model):
    _inherit = 'account.journal'
    
    is_khanbank_connect = fields.Boolean(string='Khanbank corporate gateway account journal')
    bank_config_id = fields.Many2one('bank.gateway.configure',string='Khanbank configure')
    number = fields.Char(string='Account number')
    ds_date = fields.Date(string='Start date')
    de_date = fields.Date(string='End date')
    bank_type = fields.Selection([('L','Loan'),
                             ('D','Debit')],string='Bank type',default='D')
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
    
    
    def get_rate_downloads(self):
        if self.bank_config_id:
            self.bank_config_id.get_token()
            header  = {
                        'Authorization':'Bearer %s'%self.bank_config_id.token_code,
                         }
            currency_obj = self.env['res.currency']
            rate_obj = self.env['res.currency.rate']
            rate_url = self.bank_config_id.account_rate_check_url
            request = requests.get(rate_url,headers=header)
            if request.status_code==200:
                data = request.text.encode("utf-8")
                jdata = json.loads(data)
                for dat in jdata:
                    currency_id = currency_obj.search([('name','=',dat['currency'])])
                    if currency_id:
                        rate_obj.create({'name':now_date,
                                         'rate':dat['midRate'],
                                         'currency_id':currency_id.id})
            else:
                raise except_orm(_(u'Анхааруулга!'),_(u'Холболтын алдаа гарсан тул шалгана уу.'))
        else:
            raise except_orm(_(u'Анхааруулга!'),_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
            
        return True
    
    def get_account_statement(self):
        bank_statement_obj = self.env['account.bank.statement']
        if self.bank_config_id:
            self.bank_config_id.get_token()
            header  = {
                        'Authorization':'Bearer %s'%self.bank_config_id.token_code,
                        'Content-Type':'application/x-www-form-urlencoded',
                         }
            
            account_statement_url = self.bank_config_id.account_statement_check_url
            request = requests.get(account_statement_url,headers=header)
            if request.status_code==200:
                data = request.text.encode("utf-8")
                jdata = json.loads(data)
                
                self.write({
                            'business_phone':jdata['account']['businessPhone'],
                            'in_method':jdata['account']['intMethod'],
                            'in_rate':jdata['account']['intRate'],
                            'home_phone':jdata['account']['homePhone'],
                            'open_date':jdata['account']['openDate'],
                            'customer_name':jdata['account']['customerName'],
                            'last_maintence_date':jdata['account']['lastMaintenanceDate'],
                            'last_financial_tran_date':jdata['account']['lastFinancialTranDate'],
                            })
                
            else:
                raise except_orm(_(u'Анхааруулга!'),_(u'Холболтын алдаа гарсан тул шалгана уу.'))
        else:
            raise except_orm(_(u'Анхааруулга!'),_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))

        return True

    