# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # Архиваас ялгаатай: данс харагдаж, тайлан/шүүлтүүрт ашиглагдана, зөвхөн шинэ гүйлгээнд сонгогдохгүй
    is_locked = fields.Boolean(string='Түгжээтэй', copy=False, tracking=True, index=True)
    lock_date = fields.Datetime(string='Түгжсэн огноо', copy=False, readonly=True)
    lock_user_id = fields.Many2one('res.users', string='Түгжсэн', copy=False, readonly=True)
    lock_reason = fields.Char(string='Түгжсэн шалтгаан', copy=False, tracking=True)

    def action_lock(self, reason=False):
        to_lock = self.filtered(lambda a: not a.is_locked)
        to_lock.write({
            'is_locked': True,
            'lock_date': fields.Datetime.now(),
            'lock_user_id': self.env.uid,
            'lock_reason': reason or False,
        })
        return True

    def action_unlock(self):
        self.filtered('is_locked').write({
            'is_locked': False,
            'lock_date': False,
            'lock_user_id': False,
            'lock_reason': False,
        })
        return True

    def _check_not_locked(self):
        locked = self.sudo().filtered('is_locked')
        if locked and not self.env.context.get('skip_analytic_lock_check'):
            raise ValidationError(_(
                "Түгжээтэй шинжилгээний данс ашиглах боломжгүй: %s",
                ', '.join(locked.mapped('display_name')),
            ))


class AnalyticMixin(models.AbstractModel):
    _inherit = 'analytic.mixin'

    @api.model
    def _analytic_ids_from_distribution(self, distribution):
        return {int(account_id) for key in (distribution or {}) for account_id in str(key).split(',') if account_id}

    @api.model_create_multi
    def create(self, vals_list):
        ids = set()
        for vals in vals_list:
            ids |= self._analytic_ids_from_distribution(vals.get('analytic_distribution'))
        if ids:
            self.env['account.analytic.account'].browse(ids).exists()._check_not_locked()
        return super().create(vals_list)

    def write(self, vals):
        if 'analytic_distribution' in vals:
            new_ids = self._analytic_ids_from_distribution(vals['analytic_distribution'])
            if new_ids:
                # Өмнө нь байсан түгжээтэй дансыг (жишээ нь хуучин мөрийг засахад) зөвшөөрнө, шинээр нэмэхийг хориглоно
                old_ids = set()
                for record in self:
                    old_ids |= self._analytic_ids_from_distribution(record.analytic_distribution)
                added = new_ids - old_ids
                if added:
                    self.env['account.analytic.account'].browse(added).exists()._check_not_locked()
        return super().write(vals)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _locked_check_fnames(self, vals):
        return [
            fname for fname in vals
            if fname in self._fields
            and self._fields[fname].type == 'many2one'
            and self._fields[fname].comodel_name == 'account.analytic.account'
        ]

    @api.model_create_multi
    def create(self, vals_list):
        ids = set()
        for vals in vals_list:
            # Журналын мөрийг батлахад үүсэх мөрийг шалгахгүй: дансыг журналын мөрөнд оноох үед аль хэдийн шалгасан.
            # Ингэснээр түгжихээс өмнө үүссэн ноорог (жишээ нь төсөл хаахад үүсэх нэхэмжлэл)-ийг батлах боломжтой.
            if vals.get('move_line_id'):
                continue
            ids |= {vals[f] for f in self._locked_check_fnames(vals) if vals[f]}
        if ids:
            self.env['account.analytic.account'].browse(ids).exists()._check_not_locked()
        return super().create(vals_list)

    def write(self, vals):
        fnames = self._locked_check_fnames(vals)
        ids = {vals[f] for f in fnames if vals[f]}
        # Тухайн мөрөнд аль хэдийн байгаа дансыг дахин бичихийг зөвшөөрнө
        ids -= {record[f].id for record in self for f in fnames}
        if ids:
            self.env['account.analytic.account'].browse(ids).exists()._check_not_locked()
        return super().write(vals)
