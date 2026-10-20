from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    attendance_from_systray = fields.Boolean(
        string='Attendance From Systray',
        default=False,
    )
