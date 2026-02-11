from odoo import fields, models, api, _


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    @api.model
    def default_get(self, fields):
        result = super(ResourceCalendar, self).default_get(fields)
        result['attendance_ids'] = [
            (0, 0, {'name': _('Monday'), 'dayofweek': '0', 'hour_from': 9, 'hour_to': 18, 'day_period': 'morning'}),
            (0, 0, {'name': _('Tuesday'), 'dayofweek': '1', 'hour_from': 9, 'hour_to': 18, 'day_period': 'morning'}),
            (0, 0, {'name': _('Wednesday'), 'dayofweek': '2', 'hour_from': 9, 'hour_to': 18, 'day_period': 'morning'}),
            (0, 0, {'name': _('Thursday'), 'dayofweek': '3', 'hour_from': 9, 'hour_to': 18, 'day_period': 'morning'}),
            (0, 0, {'name': _('Friday'), 'dayofweek': '4', 'hour_from': 9, 'hour_to': 18, 'day_period': 'morning'})
        ]
        return result