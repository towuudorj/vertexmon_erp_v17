from openerp import models, api, fields


class AccountBankCheck(models.TransientModel):
    _name = "account.bank.check"
    _description = "Account Unreconcile"
    
    password = fields.Char(string='Password',required=True)

    def send_confirm(self):
        context = dict(self._context or {})
        if context.get('active_ids', False):
            self.env['account.bank.statement.line'].browse(context.get('active_ids')).journal_id.bank_config_id.get_token()
            self.env['account.bank.statement.line'].browse(context.get('active_ids')).get_send_statement_confirm_line(self.password)
        return {'type': 'ir.actions.act_window_close'}