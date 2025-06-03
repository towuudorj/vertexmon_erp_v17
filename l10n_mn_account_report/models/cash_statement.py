# -*- coding: utf-8 -*-

from odoo import api, fields, models, _



class account_bank_statement_line(models.Model):
     _inherit = 'account.bank.statement.line'

     
     def print_cash_order(self):
            ''' Кассын орлогын баримт, зарлагын баримт хэвлэх
            '''
         
            if self.statement_id.journal_id.type == 'bank':
                com_bank_name = ''
                com_account_number = ''
                com_partner = ''
                com_bnk_code = ''
                partner_bnk_name = ''
                partner_account_number = ''
                ctx = dict(
                            default_model='account.bank.statement.line',
                            default_res_id=self.id,
                            amount = self.amount,
                            amount_text = self.amount_text,
                            name = self.name,
                            date = self.date,
                            company = self.company_id.id,
                            partner = self.partner_id.name,
                            move_type = self.cash_move_type,
                            com_bank_name = com_bank_name,
                            com_account_number = com_account_number,
                            com_partner = com_partner,
                            com_bnk_code = com_bnk_code,
                            partner_bnk_name = partner_bnk_name,
                            partner_account_number = partner_account_number,
                        )
                compose_form = self.env.ref('l10n_mn_account_report.payment_order_view', False)
                return {
                    'name': _('Hevleh'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'payment.order.reportsd',
                    'views': [(compose_form.id, 'form')],
                    'view_id': compose_form.id,
                    'target': 'new',
                    'context': ctx,
                }
            
            if self.statement_id.journal_id.type == 'cash':
                return self.env.ref('l10n_mn_account_report.action_print_cash_order').report_action(self)
        
        
        
