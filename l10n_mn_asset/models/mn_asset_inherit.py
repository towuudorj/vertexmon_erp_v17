# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.tools import float_compare, float_is_zero
from dateutil.relativedelta import relativedelta
import calendar

class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'
    _description = 'Asset depreciation line'
    
    #-------------------------------------------- def _prepare_move(self, line):
        #------------------------------- category_id = line.asset_id.category_id
        #--------------- account_analytic_id = line.asset_id.account_analytic_id
        #-------------------- #analytic_tag_ids = line.asset_id.analytic_tag_ids
        # depreciation_date = self.env.context.get('depreciation_date') or line.depreciation_date or fields.Date.context_today(self)
        #--------------- company_currency = line.asset_id.company_id.currency_id
        #-------------------------- current_currency = line.asset_id.currency_id
        #-------------------------------- prec = company_currency.decimal_places
        #----------------------------------- amount = current_currency._convert(
            # line.amount, company_currency, line.asset_id.company_id, depreciation_date)
        # asset_name = line.asset_id.name + ' (%s/%s)' % (line.sequence, len(line.asset_id.depreciation_line_ids))
        #------------------------------------------------------- move_line_1 = {
            #----------------------------------------------- 'name': asset_name,
            #------------- 'account_id': category_id.account_depreciation_id.id,
            # 'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            # 'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            #------------------------ 'partner_id': line.asset_id.partner_id.id,
            #------------------------------------- #'asset_id':line.asset_id.id,
            # #'analytic_account_id': account_analytic_id.id if category_id.type == 'sale' else False,
            # #'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'sale' else False,
            # 'currency_id': company_currency != current_currency and current_currency.id or False,
            # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
        #--------------------------------------------------------------------- }
        #------------------------------------------------------- move_line_2 = {
            #----------------------------------------------- 'name': asset_name,
            #----- 'account_id': category_id.account_depreciation_expense_id.id,
            # 'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            # 'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            #------------------------ 'partner_id': line.asset_id.partner_id.id,
           #------------- # 'dep_id':line.asset_id.category_id.department_id.id,
            # #'analytic_account_id': account_analytic_id.id if category_id.type == 'purchase' else False,
            # #'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if category_id.type == 'purchase' else False,
            # 'currency_id': company_currency != current_currency and current_currency.id or False,
            # 'amount_currency': company_currency != current_currency and line.amount or 0.0,
        #--------------------------------------------------------------------- }
        #--------------------------------------------------------- move_vals = {
            #---------------------------------------- 'ref': line.asset_id.code,
            #------------------------------- 'date': depreciation_date or False,
            #-------------------------- 'journal_id': category_id.journal_id.id,
            #----------- 'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
        #--------------------------------------------------------------------- }
        #------------------------------------------------------ return move_vals

class AccountAssetAssetCapitalization(models.Model):
    _name = 'account.asset.asset.capitalization'
    _description = 'Account asset capitalization'
    
    amount = fields.Float(string='Capital amount')
    date = fields.Datetime(string='Capital date')
    asset_id = fields.Many2one('account.asset.asset',string='Account asset')
    move_id = fields.Many2one('account.move',string='Account move')
    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
    
    
class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'
    
    department_id = fields.Many2one('hr.department',string='Department')

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    
    def _write_amount(self):        
        for record in self:
            self._cr.execute('select sum(amount) from account_asset_asset_capitalization where asset_id = '+str(record.id))
            sum_caps = self._cr.fetchone()
            if sum_caps and sum_caps[0] !=None:
                record.write_up = sum_caps[0]
            else:
                record.write_up = 0.0
            

    owner_id = fields.Many2one('hr.employee', string='Asset owner')
    is_closed = fields.Boolean(string='Asset account remove')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    asset_qty = fields.Float(string='Asset qty', default=1.0)
    capitalization_id = fields.One2many('account.asset.asset.capitalization','asset_id',string='Asset capitalization')
    write_up = fields.Float(string='Write Up', readonly=True, compute='_write_amount')
    scrap_date = fields.Date(string='Scrap date')
    scrap_id = fields.Many2one('account.move', string='Scrap move')
    asset_location_id = fields.Many2one('asset.location', string='Asset location')
    
    
    def action_asset_scrap(self):
        account_move_line_obj = self.env['account.move.line']
        for line in self:
            in_invoice_vals_list = []
            if not line.scrap_date:
                raise ValidationError(_(
                    "Хөрөнгө актлах огноог оруулж өгнө үү."
                ))
            else:
                move_id = {
                            'journal_id':line.category_id.journal_id.id,
                            'date':line.scrap_date,
                            'ref':line.name,
                            'company_id':line.company_id.id,
                            'currency_id':line.company_id.currency_id.id,
                            'amount_total':line.value,
                            'state':'draft',
                            'line_ids': [],
                            }
                debit_line = {
                            'account_id':line.category_id.account_depreciation_id.id,
                            'debit':line.value,
                            'journal_id':line.category_id.journal_id.id,
                            'date':line.scrap_date,
                            'credit':0,
                            'company_id':line.company_id.id,
                            'name':line.name,
                            'amount_currency':0,
                            }
                credit_line ={
                            'account_id':line.category_id.account_asset_id.id,
                            'credit':line.value,
                            'journal_id':line.category_id.journal_id.id,
                            'date':line.scrap_date,
                            #'asset_id':line.id,
                            'debit':0,
                            'company_id':line.company_id.id,
                            'name':line.name,
                            'amount_currency':0,
                            }
                
                move_id['line_ids'].append((0, 0, debit_line))
                move_id['line_ids'].append((0, 0, credit_line))
                in_invoice_vals_list.append(move_id)
                moves = self.env['account.move'].with_context().create(in_invoice_vals_list)
                line.scrap_id = moves.id
                line.scrap_date =  fields.Datetime.now()
    
    @api.depends('value', 'salvage_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.amount','write_up')
    def _amount_residual(self):
        for rec in self:
            total_amount = 0.0
            write_off = 0.0
            for line in rec.depreciation_line_ids:
                if line.move_check:
                    total_amount += line.amount
            rec.value_residual = rec.value+ rec.write_up - total_amount - rec.salvage_value + write_off

    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date):
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if self.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if self.prorata:
                    amount = amount_to_depr / self.method_number
                    if sequence == 1:
                        date = self.date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (amount_to_depr / self.method_number) / month_days * days
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                            amount = (amount_to_depr / self.method_number) / total_days * days
            elif self.method == 'degressive':
                amount = residual_amount * self.method_progress_factor
                if self.prorata:
                    if sequence == 1:
                        date = self.date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (residual_amount * self.method_progress_factor) / month_days * days
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                            amount = (residual_amount * self.method_progress_factor) / total_days * days
        return amount

    
    def compute_depreciation_board(self):
        self.ensure_one()

        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: not x.move_check)

        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual

            # if we already have some previous validated entries, starting date is last entry + method period
            if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
                last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
                depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
            else:
                # depreciation_date computed from the purchase date
                depreciation_date = self.date
                if self.date_first_depreciation == 'last_day_period':
                    # depreciation_date = the last day of the month
                    depreciation_date = depreciation_date + relativedelta(day=31)
                    # ... or fiscalyear depending the number of period
                    if self.method_period == 12:
                        depreciation_date = depreciation_date + relativedelta(month=self.company_id.fiscalyear_last_month)
                        depreciation_date = depreciation_date + relativedelta(day=self.company_id.fiscalyear_last_day)
                        if depreciation_date < self.date:
                            depreciation_date = depreciation_date + relativedelta(years=1)
                elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                    # depreciation_date set manually from the 'first_depreciation_manual_date' field
                    depreciation_date = self.first_depreciation_manual_date

            total_days = (depreciation_date.year % 4) and 365 or 366
            month_day = depreciation_date.day
            undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)

            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount(sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date)
                amount = self.currency_id.round(amount)
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue
                residual_amount -= amount
                vals = {
                    'amount': amount,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': (self.code or '') + '/' + str(sequence),
                    'remaining_value': residual_amount,
                    'depreciated_value': self.value - (self.salvage_value + residual_amount),
                    'depreciation_date': depreciation_date,
                }
                commands.append((0, False, vals))

                depreciation_date = depreciation_date + relativedelta(months=+self.method_period)

                if month_day > 28 and self.date_first_depreciation == 'manual':
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=min(max_day_in_month, month_day))

                # datetime doesn't take into account that the number of days is not the same for each month
                if not self.prorata and self.method_period % 12 != 0 and self.date_first_depreciation == 'last_day_period':
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)

        self.write({'depreciation_line_ids': commands})
        return True
    
    def asset_capitalization(self,asset_id,wizobj):
        capital_obj = self.env['account.asset.asset.capitalization']
        asset = self.browse(asset_id)
        move_line_1 = {
                    'name':asset.name,
                    'debit':wizobj.capital_amount,
                    'credit':0.0,
                    'account_id': asset.category_id.account_asset_id.id,
                    'date':fields.Date.context_today(self),
                    'partner_id':wizobj.partner_id.id,
                    'amount_currency':0.0,
                    }
        
    
        move_line_2 = {
                        'name':asset.name,
                        'credit':wizobj.capital_amount,
                        'debit':0.0,
                        'account_id': asset.category_id.account_asset_id.id,
                        'date':fields.Date.context_today(self),
                        'partner_id':wizobj.partner_id.id,
                        'amount_currency':0.0,
                        }
        move_vals = {
                    'journal_id':asset.category_id.journal_id.id,
                    'date':fields.Date.context_today(self),
                    'ref':asset.name,
                    'partner_id':wizobj.partner_id.id,
                    'state':'draft',
                    'company_id':asset.company_id.id,
                    'narration':wizobj.note,
                    'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    }
        move = self.env['account.move'].create(move_vals)
        
        
        capital_obj.create({
                            'amount':wizobj.capital_amount,
                            'date':fields.Date.context_today(self),
                            'asset_id':asset.id,
                            'move_id':move.id,
                            'company_id':asset.company_id.id,
                            })
        self.write({'write_up':wizobj.capital_amount})
        return move
    
    
    
