# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.mail.wizard.mail_compose_message import _reopen
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
import json, requests
from datetime import datetime, timedelta



class ActionCreateInvoice(models.TransientModel):
    _name = "action.create.invoice"
    _description = "Action to create invoice"
    
    is_pre_month = fields.Boolean(string=u'Өмнөх сарын баримт эсэх')
    
    
    def action_create_invoice_send_payment(self):
        vat_config_obj = self.env['vat.configure']
        vat_data_obj = self.env['invoice.vat.data']
        vat_data_line_obj = self.env['invoice.vat.data.line']
        active_ids = self.env.context.get('active_ids')
        active_records = self.env['account.move'].browse(active_ids)
        payment_data = {}
        for move in active_records:
            if move.invoice_vat_id.id != False:
                
                    
                vat_config_id = vat_config_obj.search([('company_id','=',move.company_id.id)],limit=1)
                inactive_id = ''
                invoice_id = ''
                pos_no = vat_config_id.pos_id
                customer_tin = move.partner_id.tin_code
                bank_account_no = ''
                merchant_tin = move.company_id.vat_code
                branch_no = vat_config_id.invoice_branch
                customer_no = ''
                tax_type = ''
                report_month = ''
                account_no = ''
                bank_name = ''
                bank_id = ''
                if vat_config_id.bank_account:
                    account_no = vat_config_id.bank_account
                    bank_name = vat_config_id.bank_name
                    bank_id = vat_config_id.bank_id
                vat_data_create = {}
                district_code = vat_config_id.district_id.parent_id.code+""+vat_config_id.district_id.code
                total_city_tax = 0.0
                list_items = []
                for lines in move.invoice_line_ids:
                    total_vat = (lines.price_unit*lines.quantity)-lines.price_subtotal
                    total_amount = (lines.price_unit*lines.quantity)
                    city_tax = 0.0
                    
                    item_data = {
                                "name":lines.product_id.name,
                                "barCode":lines.product_id.tax_product_code or "",
                                "barCodeType":lines.product_id.barcode_type,
                                "classificationCode":lines.product_id.tax_product_code or "",
                                "taxProductCode":"",
                                "measureUnit":u"%s"%lines.product_id.uom_id.name,
                                "qty":lines.quantity,
                                "unitPrice":lines.price_unit,
                                "totalBonus":0.0,
                                "totalVAT":total_vat,
                                "totalCityTax":city_tax,
                                "totalAmount":total_amount,
                        }
                    list_items.append(item_data)
                if account_no !='' and bank_name!='':
                    receipt_data = {
                                    "totalAmount":move.amount_total,
                                    "totalVAT":move.amount_tax,
                                    "totalCityTax":total_city_tax,
                                    "taxType":vat_config_id.tax_type,
                                    "merchantTin":merchant_tin,
                                    "bankAccountNo":account_no,
                                    "invoiceId":move.invoice_vat_id.vat_id,
                                    "data":{
                                        "bankName":u"%s"%bank_name,
                                        },
                                    "items":list_items
                        }
                else:
                    receipt_data = {
                                    "totalAmount":move.amount_total,
                                    "totalVAT":move.amount_tax,
                                    "totalCityTax":total_city_tax,
                                    "taxType":vat_config_id.tax_type,
                                    "merchantTin":merchant_tin,
                                    "items":list_items
                        }
                #for pay in move.partner_bank_id:
                
                payment_data = {
                                    'code':'PAYMENT_CARD',
                                    'exchangeCode':"",
                                    'status':'PAY',
                                    'paidAmount':move.amount_total,
                                    }
                

                current_dateTime = datetime.now()+timedelta(hours=8)
                if self.is_pre_month == True:
                    pre_month = str(move.invoice_date)
                    vat_datas = {
                                'totalAmount':move.amount_total,
                                'totalVAT':move.amount_tax,
                                'totalCityTax':total_city_tax,
                                'districtCode':"%s"%district_code,
                                'merchantTin':merchant_tin,
                                'posNo':pos_no,
                                "reportMonth":"%s"%pre_month,
                                'branchNo':branch_no,
                                'customerTin':customer_tin,
                                'consumerNo':customer_no,
                                'type':move.vat_type,
                                'date':str(str(current_dateTime)[:19]),
                                'receipts':[
                                    receipt_data
                                    ],
                                'payments':[
                                    payment_data
                                    ]
                                }
                else:
                    vat_datas = {
                                'totalAmount':move.amount_total,
                                'totalVAT':move.amount_tax,
                                'totalCityTax':total_city_tax,
                                'districtCode':"%s"%district_code,
                                'merchantTin':merchant_tin,
                                'posNo':pos_no,
                                'branchNo':branch_no,
                                'customerTin':customer_tin,
                                'consumerNo':customer_no,
                                'type':move.vat_type,
                                'date':str(str(current_dateTime)[:19]),
                                'receipts':[
                                    receipt_data
                                    ],
                                'payments':[
                                    payment_data
                                    ]
                                }
                
                header = {
                     'Accept': 'application/json',
                     'Content-Type': 'application/json'              
                    }
                
                send_data = json.dumps(vat_datas)
                
                url = vat_config_id.ebarimt_create_url
                
                return_datas = requests.request("POST", url, headers = header, data = send_data)
                if return_datas.status_code == 200:
                    json_data = return_datas.json()
                else:
                    raise UserError(_("Татварын тохиргоо зөв эсэхийг шалгана уу!!!"))
                
                    
            else:
                raise UserError(_("Татварын мэдээлэл үүссэн байгаа тул шалгана уу!!!"))
    
    
    def action_create_invoice_send(self):
        vat_config_obj = self.env['vat.configure']
        vat_data_obj = self.env['invoice.vat.data']
        vat_data_line_obj = self.env['invoice.vat.data.line']
        active_ids = self.env.context.get('active_ids')
        active_records = self.env['account.move'].browse(active_ids)
        payment_data = {}
        for move in active_records:
            if move.invoice_vat_id.id == False:
                vat_config_id = vat_config_obj.search([('company_id','=',move.company_id.id)],limit=1)
                inactive_id = ''
                invoice_id = ''
                pos_no = vat_config_id.pos_id
                customer_tin = move.partner_id.tin_code
                bank_account_no = ''
                merchant_tin = move.company_id.vat_code
                branch_no = vat_config_id.invoice_branch
                customer_no = ''
                tax_type = ''
                report_month = ''
                account_no = ''
                bank_name = ''
                bank_id = ''
                if vat_config_id.bank_account:
                    account_no = {
                                'id':'%s'%vat_config_id.bank,
                                'tin':'%s'%move.company_id.vat_code,
                                'bankAccountNo':'%s'%vat_config_id.bank_account,
                                'bankAccountName':'%s'%vat_config_id.bank_account_name,
                                'bankId':'%s'%vat_config_id.bank_id,
                                'bankName':'%s'%vat_config_id.bank_name
                                }
                    bank_name = vat_config_id.bank_name
                    bank_id = vat_config_id.bank_id
                vat_data_create = {}
                district_code = vat_config_id.district_id.parent_id.code+""+vat_config_id.district_id.code
                total_city_tax = 0.0
                list_items = []
                total_vat = 0
                for lines in move.invoice_line_ids:
                    subtotal_vat = 0
                    if lines.discount > 0.0:
                        price_unit =  lines.price_unit - ((lines.price_unit/100.0)*lines.discount)
                        price = lines.price_unit/100.0*lines.discount
                        subtotal_vat=((lines.price_unit-price)*lines.quantity)/1.1*0.10
                        total_amount = (price_unit*lines.quantity)
                    else:
                        subtotal_vat = ((lines.price_unit)*lines.quantity)/1.1*0.10
                        total_amount = (lines.price_unit*lines.quantity)
                    city_tax = 0.0
                    
                    item_data = {
                                "name":lines.product_id.name,
                                "barCode":lines.product_id.tax_product_code or "",
                                "barCodeType":lines.product_id.barcode_type,
                                "classificationCode":lines.product_id.tax_product_code or "",
                                "taxProductCode":"",
                                "measureUnit":u"%s"%lines.product_id.uom_id.name,
                                "qty":lines.quantity,
                                "unitPrice":lines.price_unit,
                                "totalBonus":0.0,
                                "totalVAT":subtotal_vat,
                                "totalCityTax":city_tax,
                                "totalAmount":total_amount,
                        }
                    total_vat +=subtotal_vat
                    list_items.append(item_data)
                if account_no !='' and bank_name!='':
                    if move.vat_type == 'B2C_RECEIPT' or  move.vat_type=='B2B_RECEIPT':
                        receipt_data = {
                                        "totalAmount":move.amount_total,
                                        "totalVAT":total_vat,
                                        "totalCityTax":total_city_tax,
                                        "taxType":vat_config_id.tax_type,
                                        "merchantTin":merchant_tin,
                                        #"bankAccountNo":"%s"%vat_config_id.bank_account,
                                        #"Гэрээний дугаар":"%s"%move.ref,
                                        #'phone':"%s"%move.ref,
                                       # 'bankId':vat_config_id.bank_id,
                                       # 'bankName':vat_config_id.bank_name
                                        "data":{
                                           #"bankName":u"%s"%bank_name,
                                         #  "Гэрээний дугаар":"%s"%move.ref,
                                            },
                                        "items":list_items
                            }
                    else:
                        receipt_data = {
                                        "totalAmount":move.amount_total,
                                        "totalVAT":total_vat,
                                        "totalCityTax":total_city_tax,
                                        "taxType":vat_config_id.tax_type,
                                        "merchantTin":merchant_tin,
                                        "bankAccountNo":"%s"%vat_config_id.bank_account,
                                      #  "Гэрээний дугаар":"%s"%move.ref,
                                       # 'phone':"%s"%move.ref,
                                       # 'bankId':vat_config_id.bank_id,
                                       # 'bankName':vat_config_id.bank_name
                                        "data":{
                                           #"bankName":u"%s"%bank_name,
                                           #"Гэрээний дугаар":"%s"%move.ref,
                                            },
                                        "items":list_items
                            }
                else:
                    receipt_data = {
                                    "totalAmount":move.amount_total,
                                    "totalVAT":total_vat,
                                    "totalCityTax":total_city_tax,
                                    "taxType":vat_config_id.tax_type,
                                    "merchantTin":merchant_tin,
                                    "items":list_items
                        }
                #for pay in move.partner_bank_id:
                if move.vat_type == 'B2C_RECEIPT' or  move.vat_type=='B2B_RECEIPT':
                    payment_data = {
                                        'code':'CASH',
                                        'exchangeCode':"",
                                        'status':'PAID',
                                        'paidAmount':move.amount_total,
                                        }
                else:
                    payment_data = {
                                        'code':'BANK_TRANSFER',
                                        'exchangeCode':"",
                                        'status':'PAY',
                                        'paidAmount':move.amount_total,
                                        }
                

                current_dateTime = datetime.now()+timedelta(hours=8)
                if self.is_pre_month == True:
                    pre_month = str(move.invoice_date)
                    vat_datas = {
                                'totalAmount':move.amount_total,
                                'totalVAT':total_vat,
                                'totalCityTax':total_city_tax,
                                'districtCode':"%s"%district_code,
                                'merchantTin':merchant_tin,
                                'posNo':pos_no,
                                "reportMonth":"%s"%pre_month,
                                'branchNo':branch_no,
                                'customerTin':customer_tin,
                                'consumerNo':customer_no,
                                'type':move.vat_type,
                                'date':str(str(current_dateTime)[:19]),
                                'receipts':[
                                    receipt_data
                                    ],
                                'payments':[
                                    payment_data
                                    ]
                                }
                else:
                    vat_datas = {
                                'totalAmount':move.amount_total,
                                'totalVAT':total_vat,
                                'totalCityTax':total_city_tax,
                                'districtCode':"%s"%district_code,
                                'merchantTin':merchant_tin,
                                'posNo':pos_no,
                                'branchNo':branch_no,
                                'customerTin':customer_tin,
                                'consumerNo':customer_no,
                                'type':move.vat_type,
                                'date':str(str(current_dateTime)[:19]),
                                "Гэрээний дугаар":"%s"%move.ref,
                                'phone':"%s"%move.ref,
                                "data":{
                                       "Гэрээний дугаар":"%s"%move.ref,
                                        },
                                'receipts':[
                                    receipt_data
                                    ],
                                'payments':[
                                    payment_data
                                    ]
                                }
                
                header = {
                     'Accept': 'application/json',
                     'Content-Type': 'application/json'              
                    }
                
                send_data = json.dumps(vat_datas)
                
                url = vat_config_id.ebarimt_create_url
                
                return_datas = requests.request("POST", url, headers = header, data = send_data)
                if return_datas.status_code == 200:
                    json_data = return_datas.json()
                    vat_data_create = {
                                    'vat_id':json_data['id'],
                                    'pos_id':json_data['posId'],
                                    'company_id':move.company_id.id,
                                    'total_amount':json_data['totalAmount'],
                                    'total_vat':json_data['totalVAT'],
                                    'total_city_tax':json_data['totalCityTax'],
                                    'district_code':json_data['districtCode'],
                                    'branch_no':json_data['branchNo'],
                                    'merchant_tin':json_data['merchantTin'],
                                    'pos_no':json_data['posNo'],
                                    'customer_tin':json_data['customerTin'],
                                    'customer_no':json_data['consumerNo'],
                                    'type':json_data['type'],
                                    'reg_date':json_data['date'],
                                    }
                    vat_data_id = vat_data_obj.create(vat_data_create)
                    for line in json_data['receipts'][0]['items']:
                        vat_data_line_create = {
                                                'name':line['name'],
                                                'barcode':line['barCode'],
                                                'barcode_type':line['barCodeType'],
                                                'classification_code':line['classificationCode'],   
                                                'tax_product_code':line['taxProductCode'],
                                                'measure_unit':line['measureUnit'],
                                                'qty':line['qty'],
                                                'unit_price':line['unitPrice'],
                                                'total_vat':line['totalVAT'],
                                                'total_city_tax':line['totalCityTax'],
                                                'total_amount':line['totalAmount']
                            }
                    
                        vat_data_line_create.update({'vat_id':vat_data_id.id})
                        vat_data_line_obj.create(vat_data_line_create)
                    move.invoice_vat_id = vat_data_id.id
                    move.vat_qr_data = json_data['qrData']
                else:
                    json_data = return_datas.json()
                    raise UserError(_(u"Татварын тохиргоо зөв эсэхийг шалгана уу!!!\n %s"%json_data))
                
                    
            else:
                raise UserError(_("Татварын мэдээлэл үүссэн байгаа тул шалгана уу!!!"))
            
            
        
    
    