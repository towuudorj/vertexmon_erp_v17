from odoo import api, models, tools

class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        super(ResPartner, self)._compute_email_formatted()
        mail_server_id = self.env['ir.mail_server'].search([], limit=1)
        for obj in self:
            if mail_server_id:
                obj.email_formatted = tools.formataddr((
                    obj.name or u"False",
                    mail_server_id.from_filter
                ))

class MailMail(models.Model):

    _inherit = 'mail.mail'

    @api.model
    def default_get(self, fields):
        res = super(MailMail, self).default_get(fields)
        env_user = self.env.user
        if 'reply_to' in fields and not res.get('reply_to') and env_user.partner_id and env_user.partner_id.email:
            res['reply_to'] = env_user.partner_id.email
        return res