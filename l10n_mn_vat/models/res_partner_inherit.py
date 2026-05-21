# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
import json, requests

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    tin_code = fields.Char(string='Tin code', default=0)
    vat_type = fields.Selection([('B2C_RECEIPT','Бизнес эрхлэгчээс хувь хүнд борлуулсан бүтээгдэхүүн, үйлчилгээний төлбөрийн баримт'),
                             ('B2B_RECEIPT','Бизнес эрхлэгч хооронд борлуулсан бүтээгдэхүүн, үйлчилгээний төлбөрийн баримт'),
                             ('B2C_INVOICE','Бизнес эрхлэгчээс хувь хүнд борлуулсан бүтээгдэхүүн, үйлчилгээний нэхэмжлэх'),
                             ('B2B_INVOICE','Бизнес эрхлэгч хооронд борлуулсан бүтээгдэхүүн, үйлчилгээний нэхэмжлэх')],
                             string='Vat type', required=True, 
                             default='B2B_INVOICE'
                             )
    _sql_constraints = [
        ('unique_tin_code', 'unique(tin_code)', 'This tin code is already assigned to another contact. Please make sure you assign a unique tin code to this contact.'),
    ]
    
    def get_name_check(self):
        vat_config_obj  = self.env['vat.configure']
        vat_config_id = vat_config_obj.search([],limit=1)
        if self.tin_code:
            url = vat_config_id.name_check_url + "?tin="+self.tin_code
            header = {
                    "Content-Type":"Application/json",                
                    }
            return_data = requests.request("get", url, headers = header)
            if return_data.status_code == 200 and return_data.json()['data'] != None:
                json_data = return_data.json()
                self.name = json_data['data']['name']
            else:
                raise UserError(_(u'Татвар төлөгчийн дугаар зөв оруулсан эсэхээ  шалгана уу.'))
        else:
            raise UserError(_(u'Татвар төлөгчийн дугаар зөв оруулсан эсэхээ  шалгана уу.'))
    
    def get_tin_code(self):
        vat_config_obj  = self.env['vat.configure']
        vat_config_id = vat_config_obj.search([],limit=1)
        if self.vat:
            url = vat_config_id.tin_code_url + "?regNo="+self.vat
            header = {
                    "Content-Type":"Application/json",                
                    }
            return_data = requests.request("get", url, headers = header)
            if return_data.status_code == 200:
                json_data = return_data.json()
                tin_value_ids = self.search([('tin_code', '=', json_data['data'])])
                if json_data['data'] == None:
                    raise UserError(_(u'Татвар төлөгчийн дугаар буруу байгаа тул шалгана уу.'))
                else:
                    self.tin_code = json_data['data']
            else:
                raise UserError(_(u'Татвар төлөгчийн дугаар зөв оруулсан эсэхээ  шалгана уу.'))
        else:
            raise UserError(_(u'Татвар төлөгчийн дугаар зөв оруулсан эсэхээ  шалгана уу.'))
        
        
        