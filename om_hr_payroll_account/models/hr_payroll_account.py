# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """
        Get partner_id of slip line to use in account_move_line
        """
        # use partner of salary rule or fallback on employee's address
        register_partner_id = self.salary_rule_id.register_id.partner_id
        partner_id = register_partner_id.id
        if credit_account:
            if register_partner_id or self.salary_rule_id.account_credit.account_type in ('asset_receivable', 'liability_payable'):
                return partner_id
        else:
            if register_partner_id or self.salary_rule_id.account_debit.account_type in ('asset_receivable', 'liability_payable'):
                return partner_id
        return False


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    date = fields.Date(
        'Date Account', help="Keep empty to use the period of the validation(Payslip) date."
    )
    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', required=True, domain=[('type', '=', 'salary')],
        default=lambda self: self.env['account.journal'].search([('type', '=', 'salary')], limit=1)
    )
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        if 'journal_id' in self.env.context:
            for vals in vals_list:
                vals['journal_id'] = self.env.context.get('journal_id')
        res = super(HrPayslip, self).create(vals_list)
        res.get_worked_day_lines(res.contract_id, res.date_from, res.date_to)
        return res

    @api.onchange('contract_id')
    def onchange_contract(self):
        super(HrPayslip, self).onchange_contract()
        self.journal_id = self.contract_id.journal_id.id or (not self.contract_id and self.default_get(['journal_id'])['journal_id'])

    def action_payslip_cancel(self):
        if any(slip.payslip_run_id for slip in self):
            raise UserError(_('Цалингийн хуудсын багцаас үүссэн тул багцаас цуцлана уу'))
        moves = self.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()
        return super(HrPayslip, self).action_payslip_cancel()

    def action_payslip_done(self):
        super(HrPayslip, self).action_payslip_done()

        all_line_ids = []
        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            # if not any(line.salary_rule_id.account_debit and line.salary_rule_id.account_credit for line in slip.details_by_salary_rule_category):
            #     raise UserError(_('Missing Debit Or Credit Account in Salary Rule'))
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue

                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id
                # if not debit_account_id or not credit_account_id:
                #     raise UserError(_('Missing Debit Or Credit Account in salary rule: "%s" !') % (
                #         line.salary_rule_id))
                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': slip.employee_id.work_contact_id.id or line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_distribution': {line.salary_rule_id.analytic_account_id.id: 100} if line.salary_rule_id.analytic_account_id else {},
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': slip.employee_id.work_contact_id.id or line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_distribution': {line.salary_rule_id.analytic_account_id.id: 100} if line.salary_rule_id.analytic_account_id else {},
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                })
                line_ids.append(adjust_credit)

            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            if self.env.context.get('form_payslip_run'):
                all_line_ids.extend(line_ids)
            else:
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                slip.write({'move_id': move.id, 'date': date})
                move.action_post()

        if self.env.context.get('form_payslip_run'):
            return all_line_ids


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    account_tax_id = fields.Many2one('account.tax', 'Tax')
    account_debit = fields.Many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)])


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    journal_id = fields.Many2one('account.journal', 'Salary Journal')


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', required=True, domain=[('type', '=', 'salary')],
        default=lambda self: self.env['account.journal'].search([('type', '=', 'salary')], limit=1)
    )
    account_move_date = fields.Date(
        'Date Account', help="Keep empty to use the period of the validation(Payslip) date."
    )
    move_id = fields.Many2one('account.move')

    def done_payslip_run(self):
        for run in self:
            if not run.slip_ids:
                raise UserError(_("Цалингийн хуудас үүсээгүй байна!"))
            move_line_vals = []
            for line in run.slip_ids:
                lines = line.with_context(form_payslip_run=True).action_payslip_done()
                if lines:
                    move_line_vals += lines

            if not move_line_vals:
                raise UserError(_("Санхүүгийн бичилт үүсгэх мөр олдсонгүй! Цалингийн дүрмийн дансны тохиргоог шалгана уу."))

            date = run.account_move_date or run.date_end
            move_dict = {
                'narration': _('Payslip of %s') % run.name,
                'ref':  (_('Advance salary') if 'payslip_type' in run and run.payslip_type == 'advance' else _('Final salary')) + " " + run.name,
                'journal_id': run.journal_id.id,
                'date': date,
                'line_ids': move_line_vals,
            }

            move = self.env['account.move'].create(move_dict)
            run.slip_ids.write({'move_id': move.id, 'date': date})
            move.action_post()
            run.write({'state': 'done', 'move_id': move.id})

    def see_move(self):
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref("account.view_move_form").id,
            'target': 'new',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
        }
        return action

    def cancel_payslip_run(self):
        for run in self:
            moves = run.mapped('move_id')
            moves.filtered(lambda x: x.state == 'posted').button_cancel()
            moves.unlink()
            run.slip_ids.write({'date': False, 'state': 'draft'})
            run.write({'state': 'draft', 'move_id': False})
