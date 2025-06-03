# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import json, requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import base64
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"
    

    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)


    def download_statement_line(self):
        st_line_obj = self.env['account.bank.statement.line']
        currency_obj = self.env['res.currency']
        partner_obj = self.env['res.partner']
        for line in self:
            if not line.journal_id.xacbank_config_id:
                raise UserError(_(u'Банкны тохиргоо хийгдээгүй байгаа тул тохиргоог хийнэ үү.'))
            
            xacbank_config = line.journal_id.xacbank_config_id
            username = xacbank_config.username
            password = xacbank_config.password
            request_id = xacbank_config.requestId
            auth_header = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
            client_cert = ("/opt/odoo/vertexmon_v17/l10n_mn_xasbank_gateway/models/client_cert.pem", "/opt/odoo/vertexmon_v17/l10n_mn_xasbank_gateway/models/client_key.pem")
            ca_cert = "/opt/odoo/vertexmon_v17/l10n_mn_xasbank_gateway/models/vertexmon_truststore.pem"

            payload = json.dumps({
                "account": "%s"% line.journal_id.bank_account_id.acc_number,
                "startDate": "%s"% line.date,
                "endDate": "%s"% line.end_date,
            })
            headers_data = {
                "Authorization": f"Basic {auth_header}",
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'requestId': '%s'%request_id,
                'systemCode': '%s'%xacbank_config.code,
                #'KeyField': '%s'%xacbank_config.keyfield,
            }

            response = requests.request("POST", xacbank_config.statement_url, headers=headers_data, cert=client_cert, verify=False, data=payload)
            if response.status_code == 200:
                result_data = response.json()
                if result_data['code']== 100:
                    
                    for dline in result_data['data']:
                         amount_value = 0
                         if dline['CREDITAMOUNT']>0.0  and dline['DEBITAMOUNT'] == 0.0:
                            amount_value = float(dline['CREDITAMOUNT'])
                         elif dline['DEBITAMOUNT'] >0.0 and dline['CREDITAMOUNT'] == 0.0:
                            amount_value = float(dline['DEBITAMOUNT'])*(-1)

                         if line.journal_id.is_income == True and amount_value > 0:
                            line_id = st_line_obj.search([('branchId','=',dline['TRN_REF_NO']),('date','=',str(dline['VALUEDATE'])),('payment_ref','=',dline['DESCRIPTION']),('statement_id','=',line.id)])
                            currency_id = currency_obj.search([('name','=',dline['CURRENCY'])])
                            partner_id = partner_obj.search([('name','=',dline['CUSTOMERNAME'])])
                            if not line_id:
                                st_line_obj.create({
                                                    'statement_id':line.id,
                                                    'date':str(dline['VALUEDATE']),
                                                    'branchId':dline['TRN_REF_NO'],
                                                    'amount':amount_value,
                                                    'currency_id':currency_id.id,
                                                    'payment_ref':dline['DESCRIPTION'],
                                                    'partner_id':partner_id.id
                                                    })
                                xacbank_config.requestId = int(request_id) + 1 
                         elif line.journal_id.is_income == False and amount_value != 0:
                            line_id = st_line_obj.search([('branchId','=',dline['TRN_REF_NO']),('date','=',str(dline['VALUEDATE'])),('payment_ref','=',dline['DESCRIPTION']),('statement_id','=',line.id)])
                            currency_id = currency_obj.search([('name','=',dline['CURRENCY'])])
                            partner_id = partner_obj.search([('name','=',dline['CUSTOMERNAME'])])
                            if not line_id:
                                st_line_obj.create({
                                                    'statement_id':line.id,
                                                    'date':str(dline['VALUEDATE']),
                                                    'branchId':dline['TRN_REF_NO'],
                                                    'amount':amount_value,
                                                    'currency_id':currency_id.id,
                                                    'payment_ref':dline['DESCRIPTION'],
                                                    'partner_id':partner_id.id
                                                    })
                                xacbank_config.requestId = int(request_id) + 1 
                
            else:
                raise UserError(_(u'Хуулга татахад алдаа гарсан тул шалгана уу: %s' % response.text))

    



class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"


    branchId = fields.Char(string='Branch ID')
