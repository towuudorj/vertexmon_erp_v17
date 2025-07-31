# -*- coding: utf-8 -*-
# Code of Margad-Erdene.S outsourcing developer

import re
import urllib.request
import logging

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from datetime import date
from odoo.exceptions import UserError
import json, requests
from requests.auth import HTTPBasicAuth 

class ResCurrency(models.Model):
    _inherit = "res.currency"


    def download_currency(self):
        rate_obj = self.env['res.currency.rate']
        currency_obj = self.env['res.currency']
        token = '0'
        token_time = 0
        
        header  = {
                    'Content-Type':'application/x-www-form-urlencoded',
                     }
        parameter = {
                'grant_type':'client_credentials',
                }
        token_url = 'https://api.khanbank.com/v1/auth/token?'
        username = '9RoFEXlolDmTWGXL9rgIZSOjL4RsfETI'
        password = 'vruz1MfJnJ7n8NvV'
        request = requests.post(token_url, auth=HTTPBasicAuth('%s'%username, '%s'%password),params = parameter,headers=header)
        data = request.text.encode("utf-8")
        
        if request.status_code == 200:
            jdata = json.loads(data)
            token = jdata['access_token']
            
        header  = {
                    'Authorization':'Bearer %s'%token,
                     }
        
        rate_url = 'https://api.khanbank.com/v1/rates'
        request = requests.get(rate_url,headers=header)
        if request.status_code==200:
            data = request.text.encode("utf-8")
            jdata = json.loads(data)
            now_date = date.today()
            all_company = self.env['res.company'].search([])
            for dat in jdata:
                currency_id = currency_obj.search([('active','=',True),('name','=',dat['currency'])])
                if currency_id:
                    for all_co in all_company:
                      rate_id = rate_obj.search([('name','=',now_date),('company_id','=',all_co.id),('currency_id','=',currency_id.id)])
                      if not rate_id:
                        rate_obj.create({'name':now_date,
		                                 'rate':1/dat['midRate'],
		                                 'company_rate':1/dat['midRate'],
		                                 'inverse_company_rate':dat['midRate'],
		                                 'company_id':all_co.id,
		                                 'currency_id':currency_id.id})


    @api.model
    def _download_currency_rate(self):
        active_currs = self.search([('active', '=', True),('name','!=','MNT')])
        for curr in active_currs:
            curr.download_currency()
