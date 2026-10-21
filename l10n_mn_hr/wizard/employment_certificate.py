from odoo import api, fields, models


class EmploymentCertificate(models.TransientModel):
    _name = 'employment.certificate'
    _description = 'employment.certificate'

    employee_id = fields.Many2one('hr.employee', string="Employee",
                                  default=lambda self: self.env.context.get('active_id')
                                    if self.env.context.get('active_model') == 'hr.employee' else False)
    lang = fields.Selection([('en', u'Англи'), ('mn', u'Монгол')], required=True, default='mn', string="Language")
    certificate_to = fields.Char(string=u"Тодорхойлолт хүргэх")

    def export_certificate(self):
        self.ensure_one()
        company = self.employee_id.company_id or self.env.company
        code = 'employment_certificate_en' if self.lang == 'en' else 'employment_certificate_mn'
        location = company.street2 if self.lang == 'en' else company.street

        conf = self.env['contract.decree.conf'].get_conf(code, company_id=company)
        if conf and conf.file and conf.line_ids:
            return conf.action_download_docx(self.employee_id.id, custom_dict={'hurgeh': self.certificate_to, 'hayag': location})
        return None


