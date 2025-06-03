# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
import json, requests

class VatConfigure(models.Model):
    _name = "vat.configure"
    _description = "Vat configuration"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    district_id = fields.Many2one('vat.district',string='Invoice district')
    tax_type = fields.Selection([('VAT_ABLE','НӨАТ тооцох бүтээгдэхүүн, үйлчилгээ'),
                                ('VAT_FREE','НӨАТ-өөс чөлөөлөгдөх бүтээгдэхүүн, үйлчилгээ'),
                                ('VAT_ZERO','НӨАТ-н 0 хувь тооцох бүтээгдэхүүн, үйлчилгээ'),
                                ('NO_VAT','Монгол улсын хилийн гадна борлуулсан бүтээгдэхүүн үйлчилгээ')],
                                string='Invoice tax type', required=True, default='VAT_ABLE')
    name = fields.Char(string='Configure name', required=True)
    pos_id = fields.Char(string='Pos number')
    invoice_branch = fields.Char(string='Invoice branch', required=True)
    client_id = fields.Char(string='Client', required=True, default='vatps')
    grant_type = fields.Char(string='Grant type', required=True, default='password')
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    reg_date = fields.Date(string='Register date', required=True,
                           default=fields.Datetime.now)
    reg_user_id = fields.Many2one('res.users', string='Register user', required=True,
                                  default=lambda self: self.env.user)
    vat_district_list_url = fields.Char(string='Vat district list url', required=True)
    ebarimt_create_url = fields.Char(string='Ebarimt create url', required=True)
    ebarimt_return_url = fields.Char(string='Ebarimt return url', required=True)
    tin_code_url = fields.Char(string="Tin code url",required=True)
    name_check_url = fields.Char(string="Name check url",required=True)
    send_data_url = fields.Char(string='Send data url', required=True)
    info_check_url = fields.Char(string='Info check url', required=True)
    account_number_check_url = fields.Char(string='Account number check url', required=True)
    access_token_url = fields.Char(string='Access token url', required=True)
    customer_register_check_url = fields.Char(string='Customer register check url', required=True)
    customer_phone_number_check_url = fields.Char(string='Customer phone number check url', required=True)
    customer_qrdata_approve_url = fields.Char(string='Customer qrdata send approve url', required=True)
    customer_passport_number_check_url = fields.Char(string='Customer passport number check url', required=True)
    customer_ebarimt_number_check_url = fields.Char(string='Customer ebarimt number check url', required=True)
    info_desc = fields.Text(string='Info')
    bank_name = fields.Char(string='Bank name')
    bank_account = fields.Char(string='Bank account')
    bank_id = fields.Char(string='Bank id')
    bank = fields.Char(string='Bank')
    bank_account_name = fields.Char(string='Bank account name')
    
    @api.model
    def _auto_send_vat(self):
        vat_ids = self.search([])
        for line in vat_ids:
            line.vat_data_send()
    
    
    def get_vat_code(self):
        url = self.tin_code_url+"?regNo=%s"%self.company_id.vat
        return_data = requests.request("GET", url)
        if return_data.status_code == 200:
            json_data = return_data.json()
            self.company_id.write({'vat_code':json_data['data']})
        else:
            raise UserError(_(u'Тохиргоо зөв эсэхийг шалгана уу.'))
        
        
    
    
    
    def vat_data_send(self):
        url = self.send_data_url
        return_data = requests.request("GET", url)
        if return_data.status_code == 200:
            self.write({'info_desc':'Send done'})
        else:
            raise UserError(_(u'Тохиргоо зөв эсэхийг шалгана уу.'))
        
    
    def get_info(self):
        url = self.info_check_url
        return_data = requests.request("GET", url)
        if return_data.status_code == 200:
            json_data = return_data.json()
            self.write({'info_desc':json_data})
        else:
            raise UserError(_(u'Тохиргоо зөв эсэхийг шалгана уу.'))
        
    def get_account_number_check(self):
        url = self.account_number_check_url+"%s"%self.company_id.vat_code
        header = {
                'Content-type':'application/json',
                }
        return_data = requests.request("GET", url, headers = header)
        if return_data.status_code == 200:
            json_data = return_data.json()
            self.bank_account = json_data[0]['bankAccountNo']
            self.bank_id = json_data[0]['bankId']
            self.bank_name = json_data[0]['bankName']
            self.bank = json_data[0]['id']
            self.bank_account_name = json_data[0]['bankAccountName']
        else:
            raise UserError(_(u'Тохиргоо зөв эсэхийг шалгана уу.'))
    
    
    def get_vat_district_download(self):
        district_obj = self.env['vat.district']
        url = self.vat_district_list_url
        return_data = requests.request("GET", url)
        if return_data.status_code == 200:
            json_data = return_data.json()
            
            for data in json_data['data']:
                district_id = district_obj.search([('name','=',data['branchName']),('code','=',data['branchCode'])])
                if not district_id:
                    dist_id = district_obj.create({
                                        'name':data['branchName'],
                                        'code':data['branchCode'],
                                        })
                    branch_district_id = district_obj.search([('name','=',data['subBranchName']),('code','=',data['subBranchCode']),('parent_id','=',dist_id.id)])
                    if not branch_district_id:
                        district_obj.create({
                                            'name':data['subBranchName'],
                                            'code':data['subBranchCode'],
                                            'parent_id':dist_id.id
                                            })
                else:
                    branch_district_id = district_obj.search([('name','=',data['subBranchName']),('code','=',data['subBranchCode']),('parent_id','=',district_id.id)])
                    if not branch_district_id:
                        district_obj.create({
                                            'name':data['subBranchName'],
                                            'code':data['subBranchCode'],
                                            'parent_id':district_id.id
                                            })
        else:
            raise UserError(_(u'Алдаа гарсан тул шалгана уу.'))
    
    
    
    