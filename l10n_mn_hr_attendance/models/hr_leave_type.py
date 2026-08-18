from odoo import api, fields, models
from odoo.exceptions import UserError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    use_in_api = fields.Boolean(default=False)

    def write(self, vals):
        for obj in self:
            if obj.use_in_api:
                raise UserError(u'Автомат чөлөөнд ашиглагддаг төрөл тул засах боломжгүй.')
        return super(HrLeaveType, self).write(vals)

    def unlink(self):
        for obj in self:
            if obj.use_in_api:
                raise UserError(u'Автомат чөлөөнд ашиглагддаг төрөл тул устгах боломжгүй.')
        return super(HrLeaveType, self).unlink()