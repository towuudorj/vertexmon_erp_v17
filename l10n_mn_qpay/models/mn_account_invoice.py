# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json,requests
from datetime import datetime

class account_move(models.Model):
    _inherit = 'account.move'
    
    
    qpay_qrcode = fields.Char('Qpay qrcode')
    qpay_image = fields.Binary('Qpay image')
    qpay_is_create = fields.Boolean(u'Qpay үүссэн эсэх')
    invoice_id = fields.Char('Invoice id')

    
    def action_create_qpay(self):
        qpay_config_obj = self.env['qpay.configure']
        obj = self.browse(self.id)
        qpay_config_id = qpay_config_obj.search([('company_id','=',obj.company_id.id)])
        if qpay_config_id !=[]:
            qpay_id = qpay_config_obj.browse(qpay_config_id.id)
            
            token_url = "%s"%qpay_id.token_url

            headers_data = {
              'Content-Type': 'application/json'
            }
            payload_data = {
                    "client_id": "%s"%qpay_id.name,
                    "client_secret": "%s"%qpay_id.password,
                    "grant_type":"client",
                    "refresh_token":""
                }
            token_code = ''
            json_datas = json.dumps(payload_data)
            token_request = requests.post(token_url, data=json_datas,headers=headers_data)
            if token_request.status_code == 200:
                datas = token_request.content
                loads = json.loads(datas)
                token_code = loads['access_token']
            
            
            now_date = str(obj.invoice_date)+' 01:00:00.01'
            now_dates = datetime.strptime(now_date, '%Y-%m-%d %H:%M:%S.%f')
            if obj.invoice_partner_bank_id ==[] and obj.invoice_partner_bank_id ==False:
                raise UserError((u'Данс сонгоогүй байгаа тул дансаа сонгоно уу!'))
                
 
            header  = {
                    'Connection': 'keep-alive',
                    'Content-Type':'application/json; charset=utf-8',
                    'Authorization': 'Bearer %s'%token_code,
                     }
            send_data = {
                      "template_id": "%s"%qpay_id.invoice_code,
                      "merchant_id": "%s"%qpay_id.merchant_code,
                      "branch_id": "1",
                      "pos_id": "1",
                      "receiver": {
                        "id": "%s"%qpay_id.data_id,
                        "register_no": "%s"%obj.company_id.vat,
                        "name": u"%s"%obj.company_id.name,
                        "email": "%s"%obj.company_id.email,
                        "phone_number":"%s"%qpay_id.phone,
                        "note" : "%s"%qpay_id.note
                      },
                      "bill_no": "%s"%obj.name+u" %s"%obj.company_id.name,
                      "date":"%s"%str(now_dates)[:16],
                      "description":u"Нэхэмжлэхийн төлбөр",
                      "amount":"%s"%obj.amount_total,
                      "btuk_code":"%s"%qpay_id.product_code,
                      "vat_flag": "%s"%qpay_id.vat_flag
                    }



            json_datas = json.dumps(send_data)
            request = requests.post(qpay_id.url, data=json_datas,headers=header)
            if request.status_code == 200:
                datas = request.content
                loads = json.loads(datas)
                self.write({
                            'qpay_qrcode':loads['qPay_QRcode'],
                            'qpay_is_create':True,
                            'invoice_id':loads['payment_id'],
                            'qpay_image':loads['qPay_QRimage'],
                            })
                    
            else:
                
                 raise UserError(_(u'Алдаа гарсан тул та дахин оролдно уу'))
        
        return True
    

