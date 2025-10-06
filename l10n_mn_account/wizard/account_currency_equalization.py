# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta, datetime
import time
import xlwt
from odoo.exceptions import UserError, ValidationError

class AccountCurrencyEqualization(models.TransientModel):
    """
        Гадаад валютаар хийгдсэн журналын бичилтүүдэд ханшийн тэгшитгэл хийнэ.
    """
    _name = "account.currency.equalization"
    _description = "Currency Rate Equalization"
    

    company_id = fields.Many2one('res.company', string='Company',required=True,default=lambda self: self.env['res.company']._company_default_get('account.currency.equalization'))
    type = fields.Selection([('liquidity', 'Liquidity Accounts'),('partner', 'Partner Balances')], string='Type', required=True)
    start_date = fields.Date(string='Start date',required=True)
    end_date = fields.Date(string='End Date', required=True)
    reg_date = fields.Date(string='Register date',required=True,default=fields.Date.context_today)
    name = fields.Char(string='Reason', size=128, required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    draft = fields.Boolean(string='Draft Entry')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency')

    
    def get_accounts(self, type):
        ''' Ханшийн тэгшитгэл хийх шаардлагатай дансуудыг тодорхойлно.
            Үүнд : Авлага өглөгийн данс болон гадаад валюттай данс
        '''
        if self._context is None:
            self._context = {}
        
        query = """SELECT a.id FROM account_account a left join account_account_type as aat on a.user_type_id = aat.id WHERE company_id = %s """ % self.company_id.id
        if type == 1 :
            query += " AND (a.currency_id is not null and a.currency_id <> %s) " % self.company_id.currency_id.id
            query += " AND (aat.type in ('liquidity')) "
            if self.currency_id:
                query += " AND a.currency_id = %s " % self.currency_id.id
                
        elif type == 2 :
            query += " AND (aat.type in ('receivable','payable')) "
        
        self._cr.execute(query)
        res = self._cr.fetchall()
        return [r[0] for r in res]

    def action_equalize(self):
        ''' 1. Авлага, өглөгийн дансны бүх гүйлгээг шүүж хамгийн сүүлд тэгшитгэсэн
                ханшаас одоогийн ханшний зөрүүгээр гүйлгээг тэгшитгэнэ. Ингэхдээ
                бүх өглөг, авлага төрөлд хамрагдах дансанд гүйлгээ хийсэн account.move
                үүдийг шүүж олно.
            
            2. Компаний үндсэн валютаас ялгаатай валютаар тохируулагдсан бүх дансуудыг
                олж тайлант хугацаа буюу сүүлд тэгшитгэсэн огнооноос хойшхи 
                    эхний үлдэгдэл,
                    орлого,
                    зарлага,
                    эцсийн үлдэгдэл
                зэргийг тооцоолж эцсийн үлдэгдэл дээр ханшийн тэгшитгэл хийнэ.
        '''
        if self._context is None:
            self._context = {}
        account_obj = self.env['account.account']
        account_move_line_obj = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        
        # Тэгшитгэл хийх шаардлагатай дансууд. Мөн өглөг, авлагын дансуудыг ялгана.
        if self.type == 'liquidity':
            account_ids1 = self.get_accounts(type=1)
            account_ids2 = []
        else :
            account_ids1 = []
            account_ids2 = self.get_accounts(type=2)
        
        res = []
        
        # Мөнгөн хөрөнгийн гадаад валютын дансуудын балансыг тэгшитгэнэ.
        if account_ids1 :
            
            res += self.currency_equalize(account_ids1, self.reg_date, 
                    self.company_id, self.journal_id.id, self.name)
        
        # Өглөг авлагын үлдэгдэл бүр дээр тэгшитгэнэ.
        if account_ids2 :
            # Өглөг, авлага бүртгэсэн гүйлгээг тодорхойлохдоо тухайн санхүүгийн жилд бүртгэгдсэнийг
            # тодорхойлно. Учир нь өмнөх жилийн гүйлгээнүүд бүгд хаагдсан байх ёстой.
            # Мөн зөвхөн тухайн компаний өглөг, авлагыг тэгшитгэнэ.
            partner_where = ""
            if self.partner_id:
                partner_where += " AND l.partner_id = %s " % self.partner_id.id
            if self.currency_id:
                partner_where += " AND l.currency_id = %s " % self.currency_id.id
            self._cr.execute("SELECT l.id FROM account_move_line l "
                       "LEFT JOIN account_move m ON m.id = l.move_id "
                       "LEFT JOIN account_account a ON a.id = l.account_id "
                       "LEFT JOIN account_account_type aat on aat.id=a.user_type_id "
                       "WHERE l.account_id in %s "
                       "AND l.company_id = %s "
                       "AND m.state = 'posted' "
                       "AND a.reconcile = true "
                       "AND l.reconcile_model_id is null "
                       "AND l.amount_currency <> 0 "
                       + partner_where +
                       "AND l.currency_id <> %s AND l.currency_id is not null "
                       "and ((aat.type = 'receivable' and l.debit > 0) or (aat.type = 'payable' and l.credit > 0)) "
                       "AND l.date <= %s ",
                    (tuple(account_ids2), self.company_id.id,
                     self.company_id.currency_id.id, self.end_date))
            fetched = self._cr.fetchall()
           
            if fetched:
                for line_id, in fetched :
                    ret = account_move_line_obj.currency_equalize_on_balance(line_id, self.company_id.currency_id,self.end_date)
                    if ret:
                        res.append(ret.id)
        
        # Гүйлгээнүүдийг батлах
        if len(res) > 0 and not self.draft :
            account_move_obj.post()
        
        # Бичигдсэн журналын бичилтүүдийг дэлгэцэнд харуулах
        return {
            'name': _('Equalization Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': (len(res) > 0 and "[('id', 'in', ["+ ','.join(map(str, res)) +"])]") or "[('id','=',False)]"
        }
        
    def currency_equalize(self,ids, date, company, journal_id, narration):
        ''' Тухайн дансанд ханшийн тэгшитгэл хийж ханшийн өөрчлөлтөөс үүдэлтэй
            балансын зөрүүг ашиг алдагдлын дансанд бичиж үүссэн ажил гүйлгээнүүдийг
            ID бүхий list буцаана.
        '''
        if self._context is None:
            self._context = {}
        cur_obj = self.env['res.currency']
        amove_line_obj = self.env['account.move.line']
        amove_obj = self.env['account.move']
        account_obj = self.env['account.account']
        res = []

        
        # Тайлант хугацааны гадаад валютаарх үлдэгдлийг тооцоолох
        self._cr.execute("SELECT l.account_id, SUM(l.amount_currency) "
                   "FROM account_move_line l "
                   "LEFT JOIN account_move m ON m.id = l.move_id "
                   "WHERE m.state = 'posted' "
                   "AND l.date >= %s and l.date <= %s and l.company_id = %s "
                   "AND l.account_id in %s "
                   "GROUP BY l.account_id ",
            (self.start_date, self.end_date, company.id, tuple(ids)))
        amount_currency_dict = dict(self._cr.fetchall())
        
        
        for account in account_obj.browse(ids) :
            if not account.currency_id or account.currency_id.id == company.currency_id.id :
                continue
            balance = 0
            aml_ids = amove_line_obj.search([('account_id','=',account.id),('parent_state','=','posted'),('date','>=',self.start_date),('date','<=',self.end_date)])
            if aml_ids !=False:
                for lines in aml_ids:
                    if lines.debit >0.0 and lines.credit==0.0:
                        balance +=lines.debit
                    else:
                        balance -=lines.credit
            amount_currency = amount_currency_dict.get(account.id, 0)
            # Валютын дүнгээрх үлдэгдэл
            # Тухайн өдрийн ханшаар валютын үлдэгдлийг үржүүлэхэд дансны үлдэгдэл гарна.
            #  Үүнийг бодит үлдэгдэлтэй харьцуулж ханшийн зөрүү дүнг олно.
            
            
            converted_amount = account.currency_id._convert(amount_currency, company.currency_id, company, self.reg_date)
            if converted_amount<0:
                if balance >0:
                    balance = balance*(-1)
   
                #converted_amount = converted_amount*(-1)
            else:
                if balance < 0:
                   balance = balance
                   #converted_amount = converted_amount*(-1)
            diff_amount = converted_amount - balance
            if account.currency_id.is_zero(diff_amount): 
                # Ханшийн зөрүү үүсээгүй болно.
                continue
                
            move_id = amove_obj.create( {
                        'journal_id': journal_id,
                        'date': date,
                        'state': 'draft'
            })
            res.append(move_id.id)
            if diff_amount > 0 :
                # Ханшийн зөрүүний ашиг
                a = company.income_currency_exchange_account_id.id
                if not a :
                    raise UserError(_('There is no income currency rate account defined for this company : %s') % company.name)
            else :
                # Ханшийн зөрүүний алдагдал
                a = company.expense_currency_exchange_account_id.id
                if not a :
                    raise UserError(_('There is no expense currency rate account defined for this company : %s') % company.name)
            
            
            # Ханшийн зөрүүг журналд бичих
            am = amove_line_obj.with_context(check_move_validity=False).create({
                'name': u'%s дансны ханшийн тэгшитгэл' % account.name,
                'debit': (diff_amount < 0 and -diff_amount) or 0.0,
                'credit': (diff_amount > 0 and diff_amount) or 0.0,
                'account_id': a,
                'partner_id': False,
                'amount_currency': 0,
                'company_id': company.id,
                'currency_id': False,
                'move_id': move_id.id,
                'date': date,
                'journal_id': journal_id,
            })
            aml = amove_line_obj.with_context(check_move_validity=False).create({
                'name': u'%s дансны ханшийн тэгшитгэл' % account.name,
                'debit': (diff_amount > 0 and diff_amount) or 0.0,
                'credit': (diff_amount < 0 and -diff_amount) or 0.0,
                'account_id': account.id,
                'partner_id': False,
                'amount_currency': 0,
                'company_id': company.id,
                'currency_id': account.currency_id.id,
                'move_id': move_id.id,
                'date': date,
                'journal_id': journal_id,
            })
        return res


