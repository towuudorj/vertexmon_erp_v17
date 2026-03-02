# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class GenerateOpeningEntries(models.TransientModel):
    _name = 'generate.opening.entries'
    _description = "Generate Opening Entries"

    name = fields.Char("Name of new entries", required=True,
                       default='End of Fiscal Year Entry')
    old_fiscal_year_id = fields.Many2one(
        'account.fiscal.year', string="Fiscal Year to close", required=True)
    new_fiscal_year_id = fields.Many2one(
        'account.fiscal.year', string="New Fiscal Year", required=True)
    journal_id = fields.Many2one('account.journal', string="Opening Entries Journal",
                                 required=True, domain=[('type', '=', 'opening')])
    
    def action_year_open_create(self):
        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']
        account_obj = self.env['account.account']
        partner_obj = self.env['res.partner']
        account_liquidity_ids = account_obj.search([('deprecated','=',False),('account_type','=','asset_cash'),('company_id','=',self.journal_id.company_id.id)])
        account_asset_ids = account_obj.search([('deprecated','=',False),('account_type','=','asset_fixed'),('company_id','=',self.journal_id.company_id.id)])
        account_pay_rec_ids = account_obj.search([('deprecated','=',False),('account_type','in',('asset_receivable','liability_payable','asset_non_current','asset_prepayments','liability_credit_card','liability_current','liability_non_current')),('company_id','=',self.journal_id.company_id.id)])
        account_product_ids = account_obj.search([('deprecated','=',False),('account_type','=','asset_current'),('company_id','=',self.journal_id.company_id.id)])
        account_equity_ids = account_obj.search([('deprecated','=',False),('account_type','in',('equity','equity_unaffected')),('company_id','=',self.journal_id.company_id.id)])
        
        self.action_year_close()
        
        move_vals = {
            'ref': self.name,
            'date': self.new_fiscal_year_id.date_from or False,
            'journal_id': self.journal_id.id,
             'state':'draft',
            'line_ids':[],
        }
        in_invoice_vals_list = []
        
        total_balance = 0.0
        if account_liquidity_ids:
            for liq in account_liquidity_ids:
                debit = 0.0
                credit = 0.0
                balance = 0.0
                amount_currency = 0.0
                liquidity_ids = obj_acc_move_line.search([('company_id','=',self.journal_id.company_id.id),('move_id.state','=','posted'),('account_id','=',liq.id),('move_id.date','>=',self.old_fiscal_year_id.date_from),('move_id.date','<=',self.old_fiscal_year_id.date_to)])
                for lin in liquidity_ids:
                    if lin.debit > 0.0 and lin.credit == 0.0:
                        debit +=lin.debit
                        amount_currency += lin.amount_currency
                    else:
                        credit +=lin.credit
                        amount_currency -=lin.amount_currency
                    
                balance = round(credit - debit,2)
                if balance != 0.0:
                    if balance < 0.0:
                        total_balance += balance*(-1)
                    else:
                        total_balance -= balance
                        

                    if liq.currency_id.id == False:
                        amount_currency = 0
                        currency = self.journal_id.company_id.currency_id.id
                    else:
                        currency = liq.currency_id.id
                    liq_data_value = {
                                        'name':self.name,
                                        'debit':0.0 if balance > 0 else -balance,
                                        'credit':balance if balance > 0 else 0.0,
                                        'account_id':liq.id,
                                        'date':self.new_fiscal_year_id.date_from,
                                        'journal_id':self.journal_id.id,
                                        'amount_currency':-amount_currency if balance > 0 else amount_currency,
                                        'currency_id':currency,
                                        }
                    move_vals['line_ids'].append((0, 0, liq_data_value))
                    
        if account_asset_ids:
            for asset in account_asset_ids:
                asset_debit = 0.0
                asset_credit = 0.0
                asset_balance = 0.0
                if asset.account_type !=u'Урьдчилсан төлбөр':
                    asset_ids = obj_acc_move_line.search([('company_id','=',self.journal_id.company_id.id),('move_id.state','=','posted'),('product_id','=',False),('account_id','=',asset.id),('move_id.date','>=',self.old_fiscal_year_id.date_from),('move_id.date','<=',self.old_fiscal_year_id.date_to)])
                    for asst in asset_ids:
                        if asst.debit > 0.0 and asst.credit == 0.0:
                            asset_debit +=asst.debit
                        else:
                            asset_credit +=asst.credit
                        
                    asset_balance = round(asset_credit - asset_debit,2)
                     
                    if asset_balance != 0.0:
                        if asset_balance < 0.0:
                            total_balance += asset_balance*(-1)
                        else:
                            total_balance -= asset_balance
                        asset_data_value = {
                                            'name':self.name,
                                            'debit':0.0 if asset_balance > 0 else -asset_balance,
                                            'credit':asset_balance if asset_balance > 0 else 0.0,
                                            'account_id':asset.id,
                                            'date':self.new_fiscal_year_id.date_from,
                                            'journal_id':self.journal_id.id,
                                            }
                        move_vals['line_ids'].append((0, 0, asset_data_value))
                    
        if account_equity_ids:
            
            for eq in account_equity_ids:
                eq_debit = 0.0
                eq_credit = 0.0
                eq_balance = 0.0
                eq_ids = obj_acc_move_line.search([('company_id','=',self.journal_id.company_id.id),('move_id.state','=','posted'),('account_id','=',eq.id),('move_id.date','>=',self.old_fiscal_year_id.date_from),('move_id.date','<=',self.old_fiscal_year_id.date_to)])
                for eqt in eq_ids:
                    if eqt.debit > 0.0 and eqt.credit == 0.0:
                        eq_debit +=eqt.debit
                    else:
                        eq_credit +=eqt.credit
                    
                eq_balance = round(eq_credit - eq_debit,2)
                
                if eq_balance != 0.0:
                    if eq_balance < 0.0:
                        total_balance += eq_balance*(-1)
                    else:
                        total_balance -= eq_balance
                    eq_data_value = {
                                        'name':self.name,
                                        'debit':0.0 if eq_balance > 0 else -eq_balance,
                                        'credit':eq_balance if eq_balance > 0 else 0.0,
                                        'account_id':eq.id,
                                        'date':self.new_fiscal_year_id.date_from,
                                        'journal_id':self.journal_id.id,
                                        }
                    move_vals['line_ids'].append((0, 0, eq_data_value))
                    
        if account_product_ids:
            product_obj = self.env['product.product']
            product_ids = product_obj.search([])
            for pro in product_ids:
                if pro.categ_id.property_stock_valuation_account_id.id !=False:
                    self._cr.execute('''select ml.product_id, sum(ml.debit - ml.credit) as balance, sum(ml.quantity) as quantity
                                        from account_move as am left join
                                        account_move_line as ml on ml.move_id=am.id
                                        where ml.account_id = %s and am.state = 'posted'
                                        and am.date >= '%s' and am.date <='%s' and ml.product_id = %s
                                        and am.company_id = %s
                                        group by ml.product_id '''%(pro.categ_id.property_stock_valuation_account_id.id,self.old_fiscal_year_id.date_from,self.old_fiscal_year_id.date_to,pro.id, self.journal_id.company_id.id))                    
                    product_balance = self._cr.dictfetchall()
                    for prod in product_balance:
                        prod_balance = 0.0
                        if prod['balance'] !=0.0 and prod['balance']!=None:
                            prod_balance = round(prod['balance'],2)
                            if prod_balance > 0.0:
                                total_balance += prod_balance
                                prod_account_id = pro.categ_id.property_stock_valuation_account_id 
                                prod_data_value = {
                                                    'name':self.name,
                                                    'credit':0.0 if prod_balance > 0 else -prod_balance,
                                                    'debit':prod_balance if prod_balance > 0 else 0.0,
                                                    'account_id':prod_account_id.id,
                                                    'date':self.new_fiscal_year_id.date_from,
                                                    'journal_id':self.journal_id.id,
                                                    'product_id':pro.id,
                                                    'quantity':prod['quantity'],
                                                    }
                                move_vals['line_ids'].append((0, 0, prod_data_value))
                    
        if account_pay_rec_ids:
            self._cr.execute('''select ml.partner_id, sum(ml.debit - ml.credit) as balance, ml.account_id,
                                ml.currency_id
                                from account_move as am left join
                                account_move_line as ml on ml.move_id=am.id
                                where ml.account_id in %s and am.state = 'posted'
                                and am.date >= '%s' and am.date <='%s' and ml.product_id is null
                                and am.company_id = %s
                                group by ml.partner_id,ml.account_id, ml.currency_id'''%(tuple(account_pay_rec_ids.ids),self.old_fiscal_year_id.date_from,self.old_fiscal_year_id.date_to, self.journal_id.company_id.id))                    
            partner_balance = self._cr.dictfetchall()
            for part in partner_balance:
                account_obj = self.env['account.account']
                part_acc = account_obj.browse(part['account_id'])
                if part_acc.account_type !=u'Үндсэн хөрөнгө':
                    part_balance = 0.0
                    if part['balance'] != 0.0 and part['balance'] !=None:
                        partner = partner_obj.browse(part['partner_id'])
                        part_balance = round(part['balance'],2)
    
                        if partner.id !=False:
                            if part_balance < 0.0:
                                total_balance -= part_balance*(-1)
                                part_account_id = partner.property_account_payable_id
                            else:
                                total_balance += part_balance
                                part_account_id = partner.property_account_receivable_id
                            part_data_value = {
                                                'name':self.name,
                                                'credit':0.0 if part_balance > 0 else -part_balance,
                                                'debit':part_balance if part_balance > 0 else 0.0,
                                                'account_id':part['account_id'],
                                                'date':self.new_fiscal_year_id.date_from,
                                                'journal_id':self.journal_id.id,
                                                'partner_id':partner.id,
                                                'currency_id':part['currency_id'] or False,
                                                }
                            move_vals['line_ids'].append((0, 0, part_data_value))
        
        diff_balance = {
                        'name':self.name,
                        'debit':0.0 if total_balance > 0 else -total_balance,
                        'credit':total_balance if total_balance > 0 else 0.0,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'date':self.new_fiscal_year_id.date_from,
                        'journal_id':self.journal_id.id,
            }
        move_vals['line_ids'].append((0, 0, diff_balance))
        
        in_invoice_vals_list.append(move_vals)
        print("dddddddddddddd",diff_balance)
        #print ("dddddddddddd",in_invoice_vals_list)
        moves = self.env['account.move'].with_context().create(in_invoice_vals_list)
        return 
    
    def action_year_close(self):
        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']
        total_debit = 0.0
        total_credit = 0.0
        account_obj = self.env['account.account']
        account_income_ids = account_obj.search([('deprecated','=',False),('account_type','in',('income','income_other')),('company_id','=',self.journal_id.company_id.id)])
        account_expense_ids = account_obj.search([('deprecated','=',False),('account_type','in',('expense','expense_depreciation','expense_direct_cost')),('company_id','=',self.journal_id.company_id.id)])
        income_data = []
        expense_data = []
        total_balance = 0.0
        
        if account_income_ids:
            
            for acc_in in account_income_ids:
                in_invoice_vals_liste = []
                move_valse = {
                    'ref': self.name,
                    'date': self.old_fiscal_year_id.date_to or False,
                    'journal_id': self.journal_id.id,
                     'state':'draft',
                     'company_id':self.journal_id.company_id.id,
                    'line_ids':[],
                }
                debit = 0.0
                credit = 0.0
                balance = 0.0
                income_ids = obj_acc_move_line.search([('company_id','=',self.journal_id.company_id.id),('move_id.state','=','posted'),('account_id','=',acc_in.id),('move_id.date','>=',self.old_fiscal_year_id.date_from),('move_id.date','<=',self.old_fiscal_year_id.date_to)])
                for inc in income_ids:
                    if inc.debit >0.0 and inc.credit == 0.0:
                        debit +=inc.debit
                    else:
                        credit +=inc.credit
                balance = round(debit - credit,2)
                
                if balance != 0.0:
                    if balance < 0.0:
                        total_balance += balance*(-1)
                    else:
                        total_balance -= balance
                    income_data_value = {
                                        'name':self.name,
                                        'debit':0.0 if balance > 0 else -balance,
                                        'credit':balance if balance > 0 else 0.0,
                                        'account_id':acc_in.id,
                                        'date':self.old_fiscal_year_id.date_to,
                                        'journal_id':self.journal_id.id,
                                        
                                        }
                    move_valse['line_ids'].append((0, 0, income_data_value))
                    
                    diff_balance = {
                                    'name':self.name,
                                    'debit':0.0 if balance < 0 else balance,
                                    'credit':-balance if balance < 0 else 0.0,
                                    'account_id':self.journal_id.default_debit_account_id.id,
                                    'date':self.old_fiscal_year_id.date_to,
                                    'journal_id':self.journal_id.id,
                        }
                    move_valse['line_ids'].append((0, 0, diff_balance))
                in_invoice_vals_liste.append(move_valse)
                moves = self.env['account.move'].with_context().create(in_invoice_vals_liste)
                
        if account_expense_ids:
            for acc_exp in account_expense_ids:
                in_invoice_vals_list = []
                move_vals = {
                    'ref': self.name,
                    'date': self.old_fiscal_year_id.date_to or False,
                    'journal_id': self.journal_id.id,
                     'state':'draft',
                     'company_id':self.journal_id.company_id.id,
                    'line_ids':[],
                }
                debit_ex = 0.0
                credit_ex = 0.0
                balance_ex = 0.0
                expense_ids = obj_acc_move_line.search([('company_id','=',self.journal_id.company_id.id,),('move_id.state','=','posted'),('account_id','=',acc_exp.id),('move_id.date','>=',self.old_fiscal_year_id.date_from),('move_id.date','<=',self.old_fiscal_year_id.date_to)])
                for exp in expense_ids:
                    if exp.debit >0.0 and exp.credit == 0.0:
                        debit_ex +=exp.debit
                    else:
                        credit_ex +=exp.credit
                balance_ex = round(debit_ex - credit_ex,2)
                if balance_ex != 0.0:
                    if balance_ex < 0.0:
                        total_balance += balance_ex*(-1)
                    else:
                        total_balance -= balance_ex
                    expense_data_value = {
                                        'name':self.name,
                                        'debit':0.0 if balance_ex > 0 else -balance_ex,
                                        'credit':balance_ex if balance_ex > 0 else 0.0,
                                        'account_id':acc_exp.id,
                                        'date':self.old_fiscal_year_id.date_to,
                                        'journal_id':self.journal_id.id,
                                        }
                    move_vals['line_ids'].append((0, 0, expense_data_value))

                    diff_balance = {
                                    'name':self.name,
                                    'debit':0.0 if balance_ex < 0 else balance_ex,
                                    'credit':-balance_ex if balance_ex < 0 else 0.0,
                                    'account_id':self.journal_id.default_debit_account_id.id,
                                    'date':self.old_fiscal_year_id.date_to,
                                    'journal_id':self.journal_id.id,
                        }
                    move_vals['line_ids'].append((0, 0, diff_balance))
                in_invoice_vals_list.append(move_vals)
                moves = self.env['account.move'].with_context().create(in_invoice_vals_list)
        
        
        #----------------------------------------------------- diff_balances = {
                        #------------------------------------- 'name':self.name,
                        #-- 'debit':total_balance if total_balance > 0 else 0.0,
                        # 'credit':-total_balance if total_balance < 0 else 0.0,
                        # 'account_id':self.journal_id.default_debit_account_id.id,
                        #-------------- 'date':self.old_fiscal_year_id.date_to,
                        #---------------------- 'journal_id':self.journal_id.id,
            #----------------------------------------------------------------- }
#------------------------------------------------------------------------------ 
        #------------------- move_vals['line_ids'].append((0, 0, diff_balances))
        #---------------------------------------------------- diff_balancess = {
                        #------------------------------------- 'name':self.name,
                        #- 'credit':total_balance if total_balance > 0 else 0.0,
                        #- 'debit':-total_balance if total_balance < 0 else 0.0,
                        # 'account_id':self.journal_id.default_credit_account_id.id,
                        #-------------- 'date':self.old_fiscal_year_id.date_to,
                        #---------------------- 'journal_id':self.journal_id.id,
            #----------------------------------------------------------------- }
#------------------------------------------------------------------------------ 
        #------------------ move_vals['line_ids'].append((0, 0, diff_balancess))
#------------------------------------------------------------------------------ 
        #-------------------------------- in_invoice_vals_list.append(move_vals)
        # moves = self.env['account.move'].with_context().create(in_invoice_vals_list)

    def data_save(self):
        """
        This function close account fiscalyear and create entries in new fiscalyear
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Account fiscalyear close state’s IDs

        """
        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']
        total_debit = 0.0
        total_credit = 0.0

        

        new_fyear = self.new_fiscal_year_id
        old_fyear = self.old_fiscal_year_id

        new_journal = self.journal_id
        company_id = self.journal_id.company_id.id

        if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
            raise UserError(
                'The journal must have default credit and debit account.')

        #delete existing move and move lines if any
        move_ids = obj_acc_move.search(
            [('journal_id', '=', new_journal.id),('company_id','=',company_id)])

        if move_ids:
            move_line_ids = obj_acc_move_line.search(
                [('move_id', 'in', move_ids.ids)])
#             obj_acc_move_line._remove_move_reconcile(cr, uid, move_line_ids, opening_reconciliation=True, context=context)
            move_line_ids.unlink()
            move_ids.unlink()

        self._cr.execute(
            "SELECT id FROM sh_fiscal_year WHERE date_end < %s", (str(new_fyear.date_from),))
        result = self._cr.dictfetchall()
        fy_ids = [x['id'] for x in result]
        query_line = '''account_move_line.parent_state = 'posted')''' 

#
        #create the opening move
        vals = {
            'name': '/',
            'ref': 'Opening Balance Entry',
            'date': new_fyear.date_from,
            'journal_id': new_journal.id,
        }
        move_id = obj_acc_move.create(vals)

        #1. report of the accounts with defferal method == 'unreconciled'
        self._cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE a.company_id = %s
              AND a.reconcile = %s''', (company_id, True))
        account_ids = [res[0] for res in self._cr.fetchall()]

        if account_ids:
            try:
                move_line = self.env['account.move.line'].search(
                    [('account_id', 'in', account_ids),('company_id','=',company_id)])
                self._cr.execute('''
                    INSERT INTO account_move_line (
                         name, create_uid, create_date, write_uid, write_date,
                          journal_id, currency_id, date_maturity,
                         partner_id, blocked,credit,  debit,
                         ref, account_id, date, move_id, amount_currency,
                         quantity, product_id, company_id)
                      (SELECT name, create_uid, create_date, write_uid, write_date,
                         %s,currency_id, date_maturity, partner_id, blocked,
                         credit, debit, ref, account_id,
                         %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id
                       FROM account_move_line
                       WHERE account_id IN %s AND reconciled IS False 
                         AND ''' + query_line + ''')''', (new_journal.id, old_fyear.date_from, move_id.id, tuple(account_ids),))

            except:
                import traceback
                traceback.print_exc()
                return

        self._cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE a.company_id = %s
              AND t.internal_group IN ('liability','asset')
              AND a.reconcile = %s''', (company_id, False))
        account_ids = map(lambda x: x[0], self._cr.fetchall())

        query_1st_part = """
                INSERT INTO account_move_line (
                     debit, credit, name, date, move_id, journal_id,
                     account_id, currency_id, amount_currency, company_id) VALUES
        """
        query_2nd_part = ""
        query_2nd_part_args = []

        for account in account_ids:
            account_balance = 0.0
            move_lines = obj_acc_move_line.sudo().search(
                [('account_id', '=', account), ('company_id','=',self.journal_id.company_id.id)])
            if move_lines:
                for line in move_lines:
                    if line.debit > 0.0:
                        account_balance += line.debit
                    if line.credit > 0.0:
                        account_balance -= line.credit

            account = self.env['account.account'].browse(account)
            if account_balance != 0.0:
                if query_2nd_part:
                    query_2nd_part += ','
                query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                query_2nd_part_args += (account_balance > 0 and account_balance or 0.0,
                                        account_balance < 0 and -account_balance or 0.0,
                                        self.name,
                                        new_fyear.date_from,
                                        move_id.id,
                                        new_journal.id,
                                        account.id,
                                        account.currency_id and account.currency_id.id or None,
                                        0.0,
                                        account.company_id.id)

        if query_2nd_part:
            self._cr.execute(query_1st_part + query_2nd_part,
                             tuple(query_2nd_part_args))

        # Add centralized line to reconcile it
        query_1st_part = """
                INSERT INTO account_move_line (
                     debit, credit, name, date, move_id, journal_id,
                     account_id, currency_id, amount_currency, company_id) VALUES
        """
        # find all lines with this move
        move_lines = obj_acc_move_line.sudo().search(
            [('move_id', '=', move_id.id)])
        for line in move_lines:
            total_credit += line.credit
            total_debit += line.debit
            line._compute_balance()

        if total_credit < 0.0:
            total_credit = - total_credit
        if total_debit < 0.0:
            total_debit = - total_debit
        # Credit Line
        query_credit_part = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        account = new_journal.default_debit_account_id
        query_credit_part_args = (total_credit,
                                  0.0,
                                  'Credit Centralisation',
                                  new_fyear.date_from,
                                  move_id.id,
                                  new_journal.id,
                                  account.id,
                                  account.currency_id and account.currency_id.id or None,
                                  0.0,
                                  account.company_id.id)
        self._cr.execute(query_1st_part + query_credit_part,
                         tuple(query_credit_part_args))

        # Debit Line
        query_credit_part = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        account = new_journal.default_credit_account_id
        query_credit_part_args = (0.0,
                                  total_debit,
                                  'Debit Centralisation',
                                  new_fyear.date_from,
                                  move_id.id,
                                  new_journal.id,
                                  account.id,
                                  account.currency_id and account.currency_id.id or None,
                                  0.0,
                                  account.company_id.id)
        self._cr.execute(query_1st_part + query_credit_part,
                         tuple(query_credit_part_args))

        last_move_lines = obj_acc_move_line.sudo().search(
            [('move_id', '=', move_id.id)], limit=2, order='id desc')
        for line in last_move_lines:
            line._compute_balance()

        move_id._compute_amount()
        move_id.write({'amount_total_signed': total_credit+total_debit})
        old_fyear.write({'move_id': move_id.id})
        return {'type': 'ir.actions.act_window_close'}
