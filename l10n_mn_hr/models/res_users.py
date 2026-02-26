# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_create_employee(self):
        self.ensure_one()
        self.env['hr.employee'].create(dict(
            name=self.name,
            company_id=self.env.company.id,
            accession_date=fields.Date.today(),
            **self.env['hr.employee']._sync_user(self)
        ))