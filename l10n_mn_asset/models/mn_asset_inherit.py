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

    is_scrap_line = fields.Boolean(string='Scrap line')

    def post_lines_and_close_asset(self):
        asset = self.asset_id
        if asset.depreciation_line_ids.filtered(lambda x: x.is_scrap_line):
            return None
        return super(AccountAssetDepreciationLine, self).post_lines_and_close_asset()
    
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
    account_asset_gain_id = fields.Many2one('account.account', string='Үндсэн хөрөнгө данснаас хассаны олзын данс')
    account_asset_loss_id = fields.Many2one('account.account', string='Үндсэн хөрөнгө данснаас хассаны гарзын данс')

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
            

    owner_id = fields.Many2one('hr.employee', string='Asset owner', tracking=True)
    is_closed = fields.Boolean(string='Asset account remove')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    asset_qty = fields.Float(string='Asset qty', default=1.0)
    product_id = fields.Many2one('product.product', string='Гарал үүслийн бараа', copy=False)
    stock_move_id = fields.Many2one('stock.move', string='Барааны хөдөлгөөн', copy=False, readonly=True)
    capitalization_id = fields.One2many('account.asset.asset.capitalization','asset_id',string='Asset capitalization')
    write_up = fields.Float(string='Write Up', readonly=True, compute='_write_amount')
    scrap_date = fields.Date(string='Scrap date')
    scrap_id = fields.Many2one('account.move', string='Scrap move')
    asset_location_id = fields.Many2one('asset.location', string='Asset location')
    state = fields.Selection(selection_add=[('scrap', 'Scrap')], ondelete={'scrap': 'cascade'},)
    
    
    def action_asset_scrap(self):
        account_move_obj = self.env['account.move']
        depreciation_line_obj = self.env['account.asset.depreciation.line']

        for asset in self:
            if not asset.scrap_date:
                raise ValidationError(_(
                    "Хөрөнгө актлах огноог оруулж өгнө үү."
                ))

            unposted_depreciation_lines = asset.depreciation_line_ids.filtered(lambda dep_line: not dep_line.move_check)
            old_values = {
                'method_end': asset.method_end,
                'method_number': asset.method_number,
            }

            if asset.salvage_value:
                raise UserError(_(
                    "Энэ хөрөнгөд Хаягдлын үнэ (Salvage value) тохируулагдсан байна. "
                    "Хаягдал/сэлбэгийн орлогын дансыг тодорхойлж, засварыг өргөтгөх хэрэгтэй тул "
                    "одоогоор зөвхөн Хаягдлын үнэгүй хөрөнгийг устгах боломжтой."
                ))

            accumulated_depreciation = asset.value - asset.salvage_value - asset.value_residual
            gain_loss_amount = asset.value_residual

            move_lines = [(0, 0, {
                'name': asset.name,
                'account_id': asset.category_id.account_depreciation_id.id,
                'debit': accumulated_depreciation,
                'credit': 0.0,
            })]

            if gain_loss_amount > 0:
                if not asset.category_id.account_asset_loss_id:
                    raise UserError(_(
                        "'%s' ангилалд Үндсэн хөрөнгө данснаас хассаны Гарзын данс тохируулагдаагүй байна."
                    ) % asset.category_id.name)
                move_lines.append((0, 0, {
                    'name': asset.name,
                    'account_id': asset.category_id.account_asset_loss_id.id,
                    'debit': gain_loss_amount,
                    'credit': 0.0,
                }))
            elif gain_loss_amount < 0:
                if not asset.category_id.account_asset_gain_id:
                    raise UserError(_(
                        "'%s' ангилалд Үндсэн хөрөнгө данснаас хассаны Олзын данс тохируулагдаагүй байна."
                    ) % asset.category_id.name)
                move_lines.append((0, 0, {
                    'name': asset.name,
                    'account_id': asset.category_id.account_asset_gain_id.id,
                    'debit': 0.0,
                    'credit': -gain_loss_amount,
                }))

            move_lines.append((0, 0, {
                'name': asset.name,
                'account_id': asset.category_id.account_asset_id.id,
                'debit': 0.0,
                'credit': asset.value,
            }))

            move_vals = {
                'journal_id': asset.category_id.journal_id.id,
                'date': asset.scrap_date,
                'ref': asset.name,
                'move_type': 'entry',
                'line_ids': move_lines,
            }

            move = account_move_obj.create(move_vals)

            sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_lines) + 1
            residual_value = asset.value_residual
            asset_value = asset.value
            salvage_value = asset.salvage_value
            asset_code = asset.code
            scrap_date = asset.scrap_date
            asset_id = asset.id

            unposted_depreciation_lines.unlink()
            depreciation_line_obj.create({
                'amount': residual_value,
                'asset_id': asset_id,
                'sequence': sequence,
                'move_id': move.id,
                'is_scrap_line': True,
                'name': (asset_code or '') + '/' + str(sequence),
                'remaining_value': 0,
                'depreciated_value': asset_value - salvage_value,
                'depreciation_date': scrap_date,
            })

            fresh_asset = self.browse(asset_id)
            fresh_asset.write({
                'scrap_id': move.id,
                'method_end': scrap_date,
                'method_number': sequence,
                'state': 'scrap',
            })
            tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_end'])
            changes, tracking_value_ids = fresh_asset._mail_track(tracked_fields, old_values)
            if changes:
                fresh_asset.message_post(
                    subject=_('Asset sold or disposed. Accounting entry awaiting for validation.'),
                    tracking_value_ids=tracking_value_ids)

        return True

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
    
    
    
