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
from requests.auth import HTTPBasicAuth 
import base64
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import date
import time
from datetime import datetime
from datetime import timedelta
import ssl
from dateutil import parser

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

    
    
class account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'
    
    end_date = fields.Date(string='End date',default=fields.Date.context_today)
    
    def get_send_statement(self):
        obj = self.env['account.bank.statement.line']
        if self.journal_id.bank_config_id:
            self.journal_id.bank_config_id.get_token()
            for line in self.line_ids:
                line.get_name_check()
                line.get_send_statement_line()
        else:
            raise UserError(_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
        return True
    
    def _action_auto_bank_statement_download(self):
        statement_ids = self.search([('state','=','open'),('journal_id.is_khanbank_connect','=',True)])
        if not self.id:
            data_ids = statement_ids
        else:
            data_ids = self.browse(self.id)
            
        for line in data_ids:
            line.get_download_statement()
    
    
    def get_action_tdb_bank_statement(self):
        statement_line = self.env['account.bank.statement.line']
        partner_obj = self.env['res.partner']
        account_obj = self.env['res.partner.bank']
        url = self.journal_id.bank_config_id.request_url
        if self.journal_id.bank_config_id.bank_type == 'tdb_bank':
            header = {
                    'Connection': 'keep-alive',
                    'Content-Type':'application/xml; charset=utf-8',
                }
            tran_seq = self.journal_id.bank_config_id.tran_download_seq
            st_obj = self.pool.get('account.bank.statement.line')
            to_time = datetime.now()
            datas = datetime.strptime(str(to_time), '%Y-%m-%d %H:%M:%S.%f')
            atten = datas + timedelta(hours=8)
            send_date = (atten.strftime('%Y-%m-%dT%H:%M:%S'))
            anybic = self.journal_id.bank_config_id.anybic
            language = self.journal_id.bank_config_id.language
            login = self.journal_id.bank_config_id.user_name
            role = self.journal_id.bank_config_id.role_id
            one_pass_type = self.journal_id.bank_config_id.password_type_one
            one_pass = self.journal_id.bank_config_id.password
            account = self.journal_id.number
            currency = self.company_id.currency_id.name
            from_date = self.date
            to_date = self.end_date
            cert_url = self.journal_id.bank_config_id.cert_file_url
            journal = self.journal_id.id
            send_data_xml = """ 
                            <Document>
                            <GrpHdr>
                                <MsgId>TRD%s</MsgId>
                                    <CreDtTm>%s</CreDtTm>
                                    <TxsCd>5004</TxsCd>
                                    <InitgPty>
                                    <Id>
                                    <OrgId>
                                        <AnyBIC>%s</AnyBIC>
                                    </OrgId>
                                    </Id>
                                    </InitgPty>
                                    <Crdtl>
                                    <Lang>%s</Lang>
                                    <LoginID>%s</LoginID>
                                    <RoleID>%s</RoleID>
                                    <Pwds>
                                        <PwdType>%s</PwdType>
                                        <Pwd>%s</Pwd>
                                    </Pwds>
                                    </Crdtl>
                            </GrpHdr>
                        <EnqInf>
                            <IBAN>%s</IBAN>
                            <Ccy>%s</Ccy>
                                <FrDt>%s</FrDt>
                                <ToDt>%s</ToDt>
                                <JrNo>722600157378</JrNo>
                        </EnqInf>
                        </Document>"""%(tran_seq,send_date,anybic,language,login,role,one_pass_type,one_pass,account,currency,from_date, to_date)
            
            cert = ('opt/odoo13/abico_erp/l10n_mn_khanbank_gateway/models/cgww.pem', 'opt/odoo13/abico_erp/l10n_mn_khanbank_gateway/models/private.key')
            request = requests.post(url, headers=header,data=send_data_xml,cert=cert,verify=False)
            if request.status_code==200:
                result_xml = request.text
                datas = result_xml.encode("utf-8")
                root = ET.fromstring(datas)
                sequence = int(self.journal_id.bank_config_id.tran_download_seq)+1
                self.journal_id.bank_config_id.write({'tran_download_seq':sequence})
                for rtl in root.iter('GrpHdr'):
                    true_data=rtl.find('RspCd').text
                    if int(true_data)==10:
                        for line in root.iter('Ntry'):
                            amount = line.find('Amt').text
                            date = line.find('TxDt').text
                            bank_desc = line.find('TxAddInf').text
                            account_number = line.find('CtAcct').text
                            acc_name = line.find('CtActnName').text
                            bank_code = line.find('CtBankNo').text
                            other_bank = line.find('CtAcntOrg').text
                            tran_id = statement_line.search([('name','=',u'%s'%bank_desc),('is_transaction','=',True),('date','=',date)])
                            if tran_id == [] or tran_id.id == False:
                                partner_id = False
                                account_id = False
                                partner_ids = partner_obj.search([('name','=',u'%s'%acc_name)],limit=1)
                                if int(bank_code) == 4:
                                    account = account_obj.search([('acc_number','=',account_number)],limit=1)
                                    if account.id!=False:
                                        account_id = account.id
                                        partner_id = account.partner_id.id
    
                                else:
                                    account = account_obj.search([('acc_number','=',other_bank)],limit=1)
                                    if account.id !=False:
                                        account_id = account.id
                                        partner_id = account.partner_id.id
                                        
                                if partner_ids!=False:
                                    partner_id = partner_ids.id
                                
                                    
                                statement_line.create({
                                                      'date':date,
                                                      'name':u'%s'%bank_desc,
                                                      'partner_id':partner_id,
                                                      'amount':amount,
                                                      'is_transaction':True,
                                                      'bank_account_id':account_id,
                                                      'statement_id':self.id,
                                                 })
                                
                    else:
                         false_data=rtl.find('RspDesc').text
                         raise UserError(u'%s байгаа тул шалгана уу.'%false_data)
        
    
    
    def get_capitron_statement(self):
        statement_line = self.env['account.bank.statement.line']
        partner_obj = self.env['res.partner']
        bank_obj = self.env['res.partner.bank']
        if self.journal_id.bank_config_id:
            self.journal_id.bank_config_id.get_capitron_token()
            new_date = str(self.date)
            end_date = str(self.end_date)
            n_date = parser.parse(new_date).strftime('%Y-%m-%d')
            e_date = parser.parse(end_date).strftime('%Y-%m-%d')
            account_number = self.journal_id.number
            
            page = 1
            header  = {
                        'token':'%s'%self.journal_id.bank_config_id.token_code,
                        'account_no':'%s'%account_number,
                        'begin_date':'%s'%n_date,
                        'end_date':'%s'%e_date,
                        'page':'%s'%page,
                        }
            acc_statement_url = '%s'%self.journal_id.bank_config_id.account_statement_check_url
            request = requests.post(acc_statement_url,data=header)
            datas = request.text.encode("utf-8")
            jdata = json.loads(datas)
            data_append = []
            
            if jdata['status'] == 'success':
                pages = jdata['response']['account_statement']['paging']['total_pages']
                if int(pages)>=1:
                    for pr in range(0,int(pages)):
                        pjdatas = []
                        pr +=1
                        headers  = {
                                    'token':'%s'%self.journal_id.bank_config_id.token_code,
                                    'account_no':'%s'%account_number,
                                    'begin_date':'%s'%n_date,
                                    'end_date':'%s'%e_date,
                                    'page':'%s'%pr,
                                    }
                        acc_page_statement_url = '%s'%self.journal_id.bank_config_id.account_statement_check_url
                        request_data = requests.post(acc_page_statement_url,data=headers)
                        pdatas = request_data.text.encode("utf-8")
                        pjdata = json.loads(pdatas)
                    
                        #if type(pjdata['response']['account_statement']['statement'])==list:
                        #    pjdatas.append(pjdata['response']['account_statement']['statement'])
                        #else:
                        pjdatas.append(pjdata['response']['account_statement']['statement'])

                        if pjdatas != []:
                            for bdata in pjdatas[0]:
                                partner = False
                                bnk_account = False        
                                if bdata['trntype'] == u'Орлого':
                                    amount = float(bdata['txnamount'])
                                else:
                                    amount = float(bdata['txnamount'])*(-1)
                                st_line_id = statement_line.search([('amount','=',str(amount)),('name','=',str(bdata['txndesc'])),('bank_record','=',str(bdata['jrno']))])
                                if st_line_id.id == False:
                                    dt_utc = datetime.datetime.strptime(str(bdata['postdate'][:-6]), "%Y-%m-%dT%H:%M:%S")
                                    now_date = dt_utc - timedelta(hours=8)
        
                                    statement_line.create({
                                                           'statement_id':self.id,
                                                           'partner_id':partner,
                                                           'amount':amount,
                                                           'name':bdata['txndesc'],
                                                           'date':now_date,
                                                           'bank_record':bdata['jrno'],
                                                           'bank_account_id':bnk_account,
                                                           })

                        
                else:
                    raise UserError(_(u'Холболтын алдаа гарсан тул шалгана уу.'))
            else:
                raise UserError(_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
        return True

    
    
    def get_download_statement(self):
        statement_line = self.env['account.bank.statement.line']
        partner_obj = self.env['res.partner']
        bank_obj = self.env['res.partner.bank']
        if self.journal_id.bank_config_id:
            self.journal_id.bank_config_id.get_token()
            header  = {
                        'Authorization':'Bearer %s'%self.journal_id.bank_config_id.token_code,
                         }
            new_date = str(self.date)
            end_date = str(self.end_date)
            n_date = parser.parse(new_date).strftime('%Y%m%d')
            e_date = parser.parse(end_date).strftime('%Y%m%d')
            if e_date:
                acc_statement_url  = self.journal_id.bank_config_id.account_statement_check_url+self.journal_id.number+"?from="+n_date+"&to="+e_date+"&"
            else:
                acc_statement_url  = self.journal_id.bank_config_id.account_statement_check_url+self.journal_id.number+"?from="+n_date+"&to="+n_date+"&"
            request = requests.get(acc_statement_url,headers=header)
            data = request.text.encode("utf-8")
            if request.status_code == 200:
                jdata = json.loads(data)
                for bdata in jdata['transactions']:
                    partner = False
                    bnk_account = False
                    try:
                        bnk_account_id = bank_obj.search([('acc_number','=',bdata['relatedAccount'])])
                        
                        if bnk_account_id !=False:
                            bnk_account =bnk_account_id.id
                            if bnk_account_id.partner_id.id:
                                partner = bnk_account_id.partner_id.id
                    except:
                        print ("log")
                    try:
                        st_line_id = statement_line.search([('amount','=',bdata['amount']),('name','=',bdata['description']),('bank_record','=',bdata['record'])])
                        if st_line_id.id == False:
                            statement_line.create({
                                                   'statement_id':self.id,
                                                   'partner_id':partner,
                                                   'amount':bdata['amount'],
                                                   'name':bdata['description'],
                                                   'date':bdata['postDate'],
                                                   'bank_record':bdata['record'],
                                                   'bank_account_id':bnk_account,
                                                   })
                    except:
                        st_line_id = statement_line.search([('amount','=',bdata['amount']),('bank_record','=',bdata['record'])])
                        if st_line_id.id == False:
                            statement_line.create({
                                                   'statement_id':self.id,
                                                   'partner_id':partner,
                                                   'amount':bdata['amount'],
                                                   'date':bdata['postDate'],
                                                   'name':" ",
                                                   'bank_record':bdata['record'],
                                                   'bank_account_id':bnk_account,
                                                   })
                    
            else:
                raise UserError(_(u'Холболтын алдаа гарсан тул шалгана уу.'))
        else:
            raise UserError(_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
        return True
    
    
class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'
    
    is_salary = fields.Boolean(string=u'Цалин гүйлгээ эсэх')
    is_bank_send = fields.Boolean(string='Is bank send')
    is_intertransfer = fields.Boolean(string='Is international transfer')
    bank_record = fields.Char('bank record')
    is_transaction = fields.Boolean('Is transaction')
    
    
    
    def get_name_check(self):
        if self.journal_id.bank_config_id:
            header  = {
                        'Authorization':'Bearer %s'%self.statement_id.journal_id.bank_config_id.token_code,
                         }
            name_check_url  = self.journal_id.bank_config_id.account_name_check_url+self.bank_account_id.acc_number+"/name?bank=050000"
            request = requests.get(name_check_url,headers=header)
            data = request.text.encode("utf-8")
            if request.status_code == 200:
                jdata = json.loads(data)
            else:
                jdata = json.loads(data)
                raise UserError(_(u'%s Холболтын алдаа гарсан тул шалгана уу.'%jdata['message']))
        else:
            raise UserError(_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
        return True


    
    def get_send_statement_confirm_line(self,password):
        if self.statement_id.journal_id.bank_config_id:
            header  = {
                        'Authorization':'Bearer %s'%self.statement_id.journal_id.bank_config_id.token_code,
                        'Content-Type':'application/json',
                         }
            
            if self.is_bank_send==False and self.journal_entry_ids.id==False:
                datas = {}
                if self.bank_account_id.id != False:
                    if int(self.bank_account_id.bank_id.bic) == 5:
                        acc_info_url  = self.statement_id.journal_id.bank_config_id.account_local_transfer_url
                        if self.bank_account_id:
                            partner_acc = self.bank_account_id.acc_number
                        else:
                            raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                        passwd = password
                        passwords = base64.b64encode(passwd.encode("utf-8"))
                        encodedStr = str(passwords)
                        amount = (self.amount)*(-1)
                        if self.amount < 0.0:
                            if self.is_salary == False:
                                datas = {
                                        "fromAccount":"%s"%self.statement_id.journal_id.number,
                                        "toAccount":"%s"%partner_acc,
                                        "amount":"%s"%amount,
                                        "description":"%s"%self.name,
                                        "currency":"%s"%self.company_id.currency_id.name,
                                        "transferId":"%s"%self.id,
                                        "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                        "tranPassword":"%s"%encodedStr,
                                    }
                            else:
                                datas = {
                                        "fromAccount":"%s"%self.statement_id.journal_id.number,
                                        "toAccount":"%s"%partner_acc,
                                        "amount":"%s"%amount,
                                        "description":"%s"%self.name,
                                        "currency":"%s"%self.company_id.currency_id.name,
                                        "transferId":"%s"%self.id,
                                        "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                        "tranPassword":"%s"%encodedStr,
                                        'purpose':"salary",
                                    }
                        
                    else:
                        if self.is_intertransfer == False:
                            acc_info_url = self.statement_id.journal_id.bank_config_id.account_interbank_transfer_url
                            if self.bank_account_id.id!=False:
                                partner_acc = self.bank_account_id.acc_number
                                acc_code = self.bank_account_id.bank_id.bic
                                
                                if len(str(acc_code))==1:
                                    acc_code = "0%s"%acc_code
                            else:
                                raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                            passwd = password
                            passwords = base64.b64encode(passwd.encode("utf-8"))
                            encodedStr = str(passwords)
                            amount = (self.amount)*(-1)
                            tocurrency = ''
                            if self.bank_account_id.currency_id.name == False:
                                tocurrency = 'MNT'
                            else:
                                tocurrency = self.bank_account_id.currency_id.name
                            if self.amount < 0.0:
                                datas = {
                                        "fromAccount":"%s"%self.statement_id.journal_id.number,
                                        "toAccount":"%s"%partner_acc,
                                        "amount":"%s"%amount,
                                        "description":"%s"%self.name,
                                        "toCurrency":"%s"%tocurrency,
                                        "toAccountName":"%s"%self.partner_id.name,
                                        "toBank":"%s0000"%acc_code,
                                        "currency":"%s"%self.company_id.currency_id.name,
                                        "transferId":"%s"%self.id,
                                        "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                        "tranPassword":"%s"%encodedStr,
                                    }
                        else:
                            acc_info_url  = self.statement_id.journal_id.bank_config_id.account_internationalbank_transfer_url
                            if self.bank_account_id.id!=False:
                                partner_acc = self.bank_account_id.acc_number
                                acc_code = self.bank_account_id.bank_id.bic
                                if len(str(acc_code))==1:
                                    acc_code = "0%s"%acc_code
                            else:
                                raise UserError(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.')
                            passwd = password
                            passwords = base64.b64encode(passwd.encode("utf-8"))
                            encodedStr = str(passwords)
                            amount = (self.amount)*(-1)
                            tocurrency = ''
                            if self.bank_account_id.currency_id.name== False:
                                tocurrency = 'MNT'
                            else:
                                tocurrency = self.bank_account_id.currency_id.name
                            if self.amount < 0.0:
                                datas = {
                                        "fromAccount":"%s"%self.statement_id.journal_id.number,
                                        "toAccount":"%s"%partner_acc,
                                        "amount":"%s"%amount,
                                        "description":"%s"%self.name,
                                        "toCurrency":"%s"%tocurrency,
                                        "toAccountName":"%s"%self.partner_id.name,
                                        "toBank":"%s0000"%acc_code,
                                        "currency":"%s"%self.company_id.currency_id.name,
                                        "transferId":"%s"%self.id,
                                        "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                        "tranPassword":"%s"%encodedStr,
                                    }
                    jdats = json.dumps(datas)
                    request = requests.post(acc_info_url,data=jdats,headers=header)
                    data = request.text.encode("utf-8")
                    if request.status_code == 200:
                        jdata = json.loads(data)
                        self.write({'is_bank_send':True})
                    else:
                        jdata = json.loads(data)
                        raise UserError(u'%s алдаа гарсан тул шалгана уу.'%jdata['message'])
                else:
                    raise UserError(u'Гүйлгээн дээр банкны дансаа оруулана уу.')
        else:
            raise UserError(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.')
        
        return True
    
    
    def get_rate_downloads(self, currency_ids, date):
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
                        return dat['sellRate']
            else:
                raise UserError(_(u'Холболтын алдаа гарсан тул шалгана уу.'))
        else:
            raise UserError(_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
            
    
   
    def get_send_statement_line(self):
        if self.statement_id.journal_id.bank_config_id:
            header  = {
                        'Authorization':'Bearer %s'%self.statement_id.journal_id.bank_config_id.token_code,
                        'Content-Type':'application/json',
                         }
            
            
            if self.is_bank_send==False and self.journal_entry_id==False:
                datas = {}
                if int(self.bank_account_id.bank_code) == 5:
                    acc_info_url  = self.statement_id.journal_id.bank_config_id.account_local_transfer_url
                    if self.bank_account_id.id!=False:
                        partner_acc = self.bank_account_id.acc_number
                    else:
                        raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                    passwd = self.statement_id.journal_id.bank_config_id.transaction_password
                    passwords = base64.b64encode(passwd.encode("utf-8"))
                    encodedStr = str(passwords)
                    amount = (self.amount)*(-1)
                    if self.amount < 0.0:
                        if self.is_salary == False:
                            datas = {
                                    "fromAccount":"%s"%self.statement_id.journal_id.number,
                                    "toAccount":"%s"%partner_acc,
                                    "amount":"%s"%amount,
                                    "description":"%s"%self.name,
                                    "currency":"%s"%self.company_id.currency_id.name,
                                    "transferId":"%s"%self.id,
                                    "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                    "tranPassword":"%s"%encodedStr,
                                }
                        else:
                            datas = {
                                    "fromAccount":"%s"%self.statement_id.journal_id.number,
                                    "toAccount":"%s"%partner_acc,
                                    "amount":"%s"%amount,
                                    "description":"%s"%self.name,
                                    "currency":"%s"%self.company_id.currency_id.name,
                                    "transferId":"%s"%self.id,
                                    "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                    "tranPassword":"%s"%encodedStr,
                                    'purpose':"salary",
                                }
                    
                else:
                    if self.is_intertransfer == False:
                        acc_info_url  = self.statement_id.journal_id.bank_config_id.account_interbank_transfer_url
                        if self.bank_account_id.id!=False:
                            partner_acc = self.bank_account_id.acc_number
                            acc_code = self.bank_account_id.bank_code
                            if len(acc_code)==1:
                                acc_code = "0%s"%acc_code
                        else:
                            raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                        passwd = self.statement_id.journal_id.bank_config_id.transaction_password
                        passwords = base64.b64encode(passwd.encode("utf-8"))
                        encodedStr = str(passwords)
                        amount = (self.amount)*(-1)
                        tocurrency = ''
                        if self.bank_account_id.currency_id.name== False:
                            tocurrency = 'MNT'
                        else:
                            tocurrency = self.bank_account_id.currency_id.name
                        if self.amount < 0.0:
                            datas = {
                                    "fromAccount":"%s"%self.statement_id.journal_id.number,
                                    "toAccount":"%s"%partner_acc,
                                    "amount":"%s"%amount,
                                    "description":"%s"%self.name,
                                    "toCurrency":"%s"%tocurrency,
                                    "toAccountName":"%s"%self.partner_id.name,
                                    "toBank":"%s0000"%acc_code,
                                    "currency":"%s"%self.company_id.currency_id.name,
                                    "transferId":"%s"%self.id,
                                    "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                    "tranPassword":"%s"%encodedStr,
                                }
                    else:
                        acc_info_url  = self.statement_id.journal_id.bank_config_id.account_internationalbank_transfer_url
                        if self.bank_account_id.id!=False:
                            partner_acc = self.bank_account_id.acc_number
                            acc_code = self.bank_account_id.bank_code
                            if len(acc_code)==1:
                                acc_code = "0%s"%acc_code
                        else:
                            raise except_orm(_(u'Анхааруулга!'),_(u'Харилцагчийн банк сонгоогүй байгаа тул шалгана уу.'))
                        passwd = self.statement_id.journal_id.bank_config_id.transaction_password
                        passwords = base64.b64encode(passwd.encode("utf-8"))
                        encodedStr = str(passwords)
                        amount = (self.amount)*(-1)
                        tocurrency = ''
                        if self.bank_account_id.currency_id.name== False:
                            tocurrency = 'MNT'
                        else:
                            tocurrency = self.bank_account_id.currency_id.name
                        if self.amount < 0.0:
                            datas = {
                                    "fromAccount":"%s"%self.statement_id.journal_id.number,
                                    "toAccount":"%s"%partner_acc,
                                    "amount":"%s"%amount,
                                    "description":"%s"%self.name,
                                    "toCurrency":"%s"%tocurrency,
                                    "toAccountName":"%s"%self.partner_id.name,
                                    "toBank":"%s0000"%acc_code,
                                    "currency":"%s"%self.company_id.currency_id.name,
                                    "transferId":"%s"%self.id,
                                    "loginName":"%s"%self.statement_id.journal_id.bank_config_id.login_name,
                                    "tranPassword":"%s"%encodedStr,
                                }
                jdats = json.dumps(datas)
                request = requests.post(acc_info_url,data=jdats,headers=header)
                data = request.text.encode("utf-8")
                if request.status_code == 200:
                    jdata = json.loads(data)
                    self.write({'is_bank_send':True})
                else:
                    jdata = json.loads(data)
                    raise UserError(_(u'%s алдаа гарсан тул шалгана уу.'%jdata['message']))
        else:
            raise UserError(_(u'Журнал дээр банкны тохиргоо хийгээгүй байгаа тул шалгана уу.'))
        
        return True
    
    

