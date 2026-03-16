# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class GenerateOpeningEntries(models.TransientModel):
    _name = 'generate.opening.entries'
    _description = "Generate Opening Entries"

    name = fields.Char("Нээлтийн гүйлгээний утга", required=True,
                       default='End of Fiscal Year Entry')
    old_fiscal_year_id = fields.Many2one(
        'account.fiscal.year', string="Хаах санхүүгийн жил", required=True)
    new_fiscal_year_id = fields.Many2one(
        'account.fiscal.year', string="Шинэ санхүүгийн жил", required=True)
    journal_id = fields.Many2one('account.journal', string="Нээлтийн журнал",
                                 required=True, domain=[('type', '=', 'opening')])

    close_journal_id = fields.Many2one('account.journal', string="Хаалтын журнал",
                                 required=True, domain=[('type', '=', 'closing')])
    
    


    def action_year_open_create(self):

        Move = self.env['account.move']
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
    
        company_id = self.journal_id.company_id.id
    
        if not self.journal_id.default_debit_account_id or not self.journal_id.default_credit_account_id:
            raise UserError("Opening journal must have default debit and credit accounts.")
    
        self.action_year_close()
    
        move_vals = {
            "date": self.new_fiscal_year_id.date_from,
            "ref": self.name,
            "journal_id": self.journal_id.id,
            "line_ids": [],
        }
    
        total_debit = 0
        total_credit = 0
    
        accounts = Account.search([
            ('company_id', '=', company_id),
            ('deprecated', '=', False),
            ('account_type', 'in', [
                'asset_receivable',
                'asset_cash',
                'asset_current',
                'asset_non_current',
                'liability_payable',
                'liability_current',
                'liability_non_current',
                'equity',
                'asset_prepayments',
                'asset_fixed'
            ])
        ])
    
        for account in accounts:
    
            # PARTNER REQUIRED ACCOUNTS
            if account.account_type in ('asset_receivable','liability_payable', 'asset_prepayments'):

                self.env.cr.execute("""
                    SELECT partner_id,
                           SUM(debit) as debit,
                           SUM(credit) as credit
                    FROM account_move_line
                    WHERE account_id = %s
                    AND company_id = %s
                    AND parent_state = 'posted'
                    AND date >= %s
                    AND date < %s
                    GROUP BY partner_id
                """, (
                    account.id,
                    company_id,
                    self.old_fiscal_year_id.date_from,
                    self.new_fiscal_year_id.date_from
                ))
    
                results = self.env.cr.dictfetchall()
    
                for row in results:
                    balance = 0
                    opening_move_line = MoveLine.search(
                        [('company_id', '=', self.journal_id.company_id.id), ('move_id.state', '=', 'posted'),
                         ('account_id', '=', account.id), ('move_id.date', '<', self.old_fiscal_year_id.date_from),
                         ('journal_id.type', '=', 'opening'), ('partner_id', '=', row['partner_id'] or False)])
                    if opening_move_line:
                        opening_date = max(opening_move_line.mapped('date'))
                        opening_move_line = opening_move_line.filtered(lambda x: x.date == opening_date)
                        balance += sum(opening_move_line.mapped('balance'))
                        opening_line_ids =  MoveLine.search([
                            ('company_id', '=', self.journal_id.company_id.id),
                            ('move_id.state', '=', 'posted'),
                            ('account_id', '=', account.id), ('move_id.date', '>', opening_date),
                            ('move_id.date', '<', self.old_fiscal_year_id.date_from),
                            ('partner_id', '=', row['partner_id'] or False)])
                        if opening_line_ids:
                            balance += sum(opening_line_ids.mapped('balance'))
                    else:
                        opening_line_ids = MoveLine.search([
                            ('company_id', '=', self.journal_id.company_id.id),
                            ('move_id.state', '=', 'posted'),
                            ('account_id', '=', account.id),
                            ('move_id.date', '<', self.old_fiscal_year_id.date_from),
                            ('partner_id', '=', row['partner_id'] or False)])
                        if opening_line_ids:
                            balance += sum(opening_line_ids.mapped('balance'))

                    balance += (row['debit'] or 0) - (row['credit'] or 0)
    
                    if float_is_zero(balance, precision_digits=2):
                        continue
    
                    debit = balance if balance > 0 else 0
                    credit = -balance if balance < 0 else 0
    
                    line_vals = {
                        "name": self.name,
                        "account_id": account.id,
                        "partner_id": row['partner_id'],
                        "debit": debit,
                        "credit": credit,
                        "date": self.new_fiscal_year_id.date_from,
                        "company_id": company_id,
                    }

                    if account.currency_id:
                        currency_rate = 1.0
                        if account.currency_id != self.journal_id.company_id.currency_id:
                            currency_rate = self.env['res.currency']._get_conversion_rate(
                                from_currency=self.journal_id.company_id.currency_id,
                                to_currency=account.currency_id,
                                company=self.journal_id.company_id,
                                date=self.new_fiscal_year_id.date_from,
                            )

                        line_vals.update({
                            "currency_id": account.currency_id.id,
                            "amount_currency": balance * currency_rate
                        })
    
                    move_vals["line_ids"].append((0, 0, line_vals))
    
                    total_debit += debit
                    total_credit += credit
    
            else:
                # NORMAL ACCOUNT BALANCE
    
                self.env.cr.execute("""
                    SELECT SUM(debit) as debit, SUM(credit) as credit
                    FROM account_move_line
                    WHERE account_id=%s
                    AND company_id=%s
                    AND parent_state='posted'
                    AND date >= %s
                    AND date < %s
                """, (
                    account.id,
                    company_id,
                    self.old_fiscal_year_id.date_from,
                    self.new_fiscal_year_id.date_from
                ))
    
                result = self.env.cr.fetchone()

                balance = 0
                opening_move_line = MoveLine.search(
                    [('company_id', '=', self.journal_id.company_id.id), ('move_id.state', '=', 'posted'),
                     ('account_id', '=', account.id), ('move_id.date', '<', self.old_fiscal_year_id.date_from),
                     ('journal_id.type', '=', 'opening')])
                if opening_move_line:
                    opening_date = max(opening_move_line.mapped('date'))
                    opening_move_line = opening_move_line.filtered(lambda x: x.date == opening_date)
                    balance += sum(opening_move_line.mapped('balance'))
                    opening_line_ids = MoveLine.search([
                        ('company_id', '=', self.journal_id.company_id.id),
                        ('move_id.state', '=', 'posted'),
                        ('account_id', '=', account.id), ('move_id.date', '>', opening_date),
                        ('move_id.date', '<', self.old_fiscal_year_id.date_from)])
                    if opening_line_ids:
                        balance += sum(opening_line_ids.mapped('balance'))
                else:
                    opening_line_ids = MoveLine.search([
                        ('company_id', '=', self.journal_id.company_id.id),
                        ('move_id.state', '=', 'posted'),
                        ('account_id', '=', account.id),
                        ('move_id.date', '<', self.old_fiscal_year_id.date_from)])
                    if opening_line_ids:
                        balance += sum(opening_line_ids.mapped('balance'))

                balance += (result[0] or 0) - (result[1] or 0)
    
                if float_is_zero(balance, precision_digits=2):
                    continue
    
                debit = balance if balance > 0 else 0
                credit = -balance if balance < 0 else 0
    
                line_vals = {
                    "name": self.name,
                    "account_id": account.id,
                    "debit": debit,
                    "credit": credit,
                    "date": self.new_fiscal_year_id.date_from,
                    "company_id": company_id,
                }
    
                if account.currency_id:
                    currency_rate = 1.0
                    if account.currency_id != self.journal_id.company_id.currency_id:
                        currency_rate = self.env['res.currency']._get_conversion_rate(
                            from_currency=self.journal_id.company_id.currency_id,
                            to_currency=account.currency_id,
                            company=self.journal_id.company_id,
                            date=self.new_fiscal_year_id.date_from,
                        )

                    line_vals.update({
                        "currency_id": account.currency_id.id,
                        "amount_currency": balance * currency_rate
                    })

                move_vals["line_ids"].append((0, 0, line_vals))
    
                total_debit += debit
                total_credit += credit
    
        difference = total_debit - total_credit
    
        if not float_is_zero(difference, precision_digits=2):
            acc = self.journal_id.default_credit_account_id if difference > 0 else self.journal_id.default_debit_account_id
            vals = {
                "name": "Opening Balance Adjustment",
                "account_id": acc.id,
                "credit": difference if difference > 0 else 0,
                "debit": -difference if difference < 0 else 0,
                "date": self.new_fiscal_year_id.date_from,
                "company_id": company_id,
            }

            if acc.currency_id:
                currency_rate = 1.0
                if acc.currency_id != self.journal_id.company_id.currency_id:
                    currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=self.journal_id.company_id.currency_id,
                        to_currency=acc.currency_id,
                        company=self.journal_id.company_id,
                        date=self.new_fiscal_year_id.date_from,
                    )

                vals.update({
                    "currency_id": acc.currency_id.id,
                    "amount_currency": -difference * currency_rate
                })
            move_vals["line_ids"].append((0, 0, vals))
    
        move = Move.create(move_vals)
    
        return {
            "type": "ir.actions.act_window",
            "name": "Opening Entry",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
        }


    

        
    
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
                    'journal_id': self.close_journal_id.id,
                     'state':'draft',
                     'company_id':self.journal_id.company_id.id,
                    'line_ids':[],
                }
                debit = 0.0
                credit = 0.0
                balance = 0.0
                opening_move_line = obj_acc_move_line.search([('company_id','=',self.journal_id.company_id.id),('move_id.state','=','posted'),('account_id','=',acc_in.id),('move_id.date','<=',self.old_fiscal_year_id.date_from), ('journal_id.type', '=', 'opening')], order='date desc')
                if opening_move_line:
                    opening_date = max(opening_move_line.mapped('date'))
                    opening_move_line = opening_move_line.filtered(lambda x: x.date == opening_date)
                    income_ids = obj_acc_move_line.search(
                        [('company_id', '=', self.journal_id.company_id.id), ('move_id.state', '=', 'posted'),
                         ('account_id', '=', acc_in.id), ('move_id.date', '>', opening_date)
                         ('move_id.date', '<=', self.old_fiscal_year_id.date_to)])
                    debit += sum(opening_move_line.mapped('debit'))
                    credit += sum(opening_move_line.mapped('credit'))
                else:
                    income_ids = obj_acc_move_line.search(
                        [('company_id', '=', self.journal_id.company_id.id),
                         ('move_id.state', '=', 'posted'),
                         ('account_id', '=', acc_in.id),
                         ('move_id.date', '<=', self.old_fiscal_year_id.date_to)])

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
                                        'journal_id':self.close_journal_id.id,
                                        }

                    if acc_in.currency_id:
                        currency_rate = 1.0
                        if account.currency_id != self.journal_id.company_id.currency_id:
                            currency_rate = self.env['res.currency']._get_conversion_rate(
                                from_currency=self.journal_id.company_id.currency_id,
                                to_currency=acc_in.currency_id,
                                company=self.journal_id.company_id,
                                date=self.old_fiscal_year_id.date_to,
                            )

                        income_data_value.update({
                            "currency_id": acc_in.currency_id.id,
                            "amount_currency": -balance * currency_rate
                        })

                    move_valse['line_ids'].append((0, 0, income_data_value))
                    
                    diff_balance = {
                                    'name':self.name,
                                    'debit':0.0 if balance < 0 else balance,
                                    'credit':-balance if balance < 0 else 0.0,
                                    'account_id':self.close_journal_id.default_debit_account_id.id,
                                    'date':self.old_fiscal_year_id.date_to,
                                    'journal_id':self.close_journal_id.id,
                        }

                    if self.close_journal_id.default_debit_account_id.currency_id:
                        currency_rate = 1.0
                        if account.currency_id != self.journal_id.company_id.currency_id:
                            currency_rate = self.env['res.currency']._get_conversion_rate(
                                from_currency=self.journal_id.company_id.currency_id,
                                to_currency=self.close_journal_id.default_debit_account_id.currency_id,
                                company=self.journal_id.company_id,
                                date=self.old_fiscal_year_id.date_to,
                            )

                        diff_balance.update({
                            "currency_id": self.close_journal_id.default_debit_account_id.currency_id.id,
                            "amount_currency": balance * currency_rate
                        })

                    move_valse['line_ids'].append((0, 0, diff_balance))
                in_invoice_vals_liste.append(move_valse)
                moves = self.env['account.move'].with_context().create(in_invoice_vals_liste)
                
        if account_expense_ids:
            for acc_exp in account_expense_ids:
                in_invoice_vals_list = []
                move_vals = {
                    'ref': self.name,
                    'date': self.old_fiscal_year_id.date_to or False,
                    'journal_id': self.close_journal_id.id,
                     'state':'draft',
                     'company_id':self.journal_id.company_id.id,
                    'line_ids':[],
                }
                debit_ex = 0.0
                credit_ex = 0.0
                balance_ex = 0.0

                opening_move_line = obj_acc_move_line.search(
                    [('company_id', '=', self.journal_id.company_id.id), ('move_id.state', '=', 'posted'),
                     ('account_id', '=', acc_exp.id), ('move_id.date', '<=', self.old_fiscal_year_id.date_from),
                     ('journal_id.type', '=', 'opening')])
                if opening_move_line:
                    opening_date = max(opening_move_line.mapped('date'))
                    opening_move_line = opening_move_line.filtered(lambda x: x.date == opening_date)
                    expense_ids = obj_acc_move_line.search(
                        [('company_id', '=', self.journal_id.company_id.id,), ('move_id.state', '=', 'posted'),
                         ('account_id', '=', acc_exp.id), ('move_id.date', '>', opening_date),
                         ('move_id.date', '<=', self.old_fiscal_year_id.date_to)])
                    debit_ex += sum(opening_move_line.mapped('debit'))
                    credit_ex += sum(opening_move_line.mapped('credit'))

                else:
                    expense_ids = obj_acc_move_line.search(
                        [('company_id', '=', self.journal_id.company_id.id,), ('move_id.state', '=', 'posted'),
                         ('account_id', '=', acc_exp.id), ('move_id.date', '<=', self.old_fiscal_year_id.date_to)])

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
                                        'journal_id':self.close_journal_id.id,
                                        }

                    if acc_exp.currency_id:
                        currency_rate = 1.0
                        if account.currency_id != self.journal_id.company_id.currency_id:
                            currency_rate = self.env['res.currency']._get_conversion_rate(
                                from_currency=self.journal_id.company_id.currency_id,
                                to_currency=acc_exp.currency_id,
                                company=self.journal_id.company_id,
                                date=self.old_fiscal_year_id.date_to,
                            )

                        expense_data_value.update({
                            "currency_id": acc_exp.currency_id.id,
                            "amount_currency": -balance_ex * currency_rate
                        })

                    move_vals['line_ids'].append((0, 0, expense_data_value))

                    diff_balance = {
                                    'name':self.name,
                                    'debit':0.0 if balance_ex < 0 else balance_ex,
                                    'credit':-balance_ex if balance_ex < 0 else 0.0,
                                    'account_id':self.close_journal_id.default_debit_account_id.id,
                                    'date':self.old_fiscal_year_id.date_to,
                                    'journal_id':self.close_journal_id.id,
                        }

                    if self.close_journal_id.default_debit_account_id.currency_id:
                        currency_rate = 1.0
                        if account.currency_id != self.journal_id.company_id.currency_id:
                            currency_rate = self.env['res.currency']._get_conversion_rate(
                                from_currency=self.journal_id.company_id.currency_id,
                                to_currency=self.close_journal_id.default_debit_account_id.currency_id,
                                company=self.journal_id.company_id,
                                date=self.old_fiscal_year_id.date_to,
                            )

                        diff_balance.update({
                            "currency_id": self.close_journal_id.default_debit_account_id.currency_id.id,
                            "amount_currency": balance_ex * currency_rate
                        })
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
