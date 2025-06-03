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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import json,requests
from requests.auth import HTTPBasicAuth 
import base64
from openerp.osv import fields, osv

class payment_order(osv.osv):
    _inherit = 'payment.order'
    
    
    
    def set_done(self, cr, uid, ids, *args):
        obj = self.browse(cr, uid, ids)
        obj.journal.bank_config_id.get_token()
        header  = {
                    'Authorization':'Bearer %s'%obj.mode.journal.bank_config_id.token_code,
                    'Content-Type':'application/json',
                     }
        datas = {}
        for lines in obj.line_ids:
            if lines.partner_id.id:
                if lines.bank_id.id:
                    if int(obj.mode.bank_id.bank_code) == 5:
                        acc_info_url  = obj.mode.journal.bank_config_id.account_local_transfer_url
                        if lines.bank_id:
                            partner_acc = lines.bank_id.acc_number
                        else:
                            raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                        passwd = obj.mode.journal.bank_config_id.transaction_password
                        passwords = base64.b64encode(passwd.encode("utf-8"))
                        encodedStr = str(passwords)
                        datas = {
                                "fromAccount":"%s"%obj.mode.journal.number,
                                "toAccount":"%s"%partner_acc,
                                "amount":"%s"%lines.amount_currency,
                                "description":"%s"%lines.communication,
                                "currency":"%s"%lines.currency.name,
                                "transferId":"%s"%lines.id,
                                "loginName":"%s"%obj.mode.journal.bank_config_id.login_name,
                                "tranPassword":"%s"%encodedStr,
                            }

                    else:
                        acc_info_url  = obj.mode.journal.bank_config_id.account_local_transfer_url
                        if lines.bank_id:
                            partner_acc = lines.bank_id.acc_number
                            acc_code =  lines.bank_id.bank_code
                        else:
                            raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                        passwd = self.mode.journal.bank_config_id.transaction_password
                        passwords = base64.b64encode(passwd.encode("utf-8"))
                        encodedStr = str(passwords)
                        datas = {
                                "fromAccount":"%s"%obj.mode.journal.number,
                                "toAccount":"%s"%partner_acc,
                                "amount":"%s"%lines.amount,
                                "description":"%s"%lines.communication,
                                "toCurrency":"%s"%tocurrency,
                                "toAccountName":"%s"%lines.partner_id.name,
                                "toBank":"%s0000"%acc_code,
                                "currency":"%s"%obj.company_id.currency_id.name,
                                "transferId":"%s"%obj.id,
                                "loginName":"%s"%obj.mode.journal.bank_config_id.login_name,
                                "tranPassword":"%s"%encodedStr,
                            }
                        
            jdats = json.dumps(datas)
            request = requests.post(acc_info_url,data=jdats,headers=header)
            data = request.text.encode("utf-8")
            if request.status_code == 200:
                jdata = json.loads(data)
                self.write({'is_bank_send':True})
            else:
                raise except_orm(_(u'Анхааруулга!'),_(u'Холболтын алдаа гарсан тул шалгана уу.'))
        self.write(cr, uid, ids, {'date_done': time.strftime('%Y-%m-%d')})
        self.signal_workflow(cr, uid, ids, 'done')
        return True