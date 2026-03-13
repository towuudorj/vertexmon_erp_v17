from odoo import api, fields, models, _


class Model(models.AbstractModel):
    _name = 'xls.report.base'
    _description = 'xls.report.base'

    preview_html = fields.Html(compute="_compute_preview_html", sanitize=False)

    def _compute_preview_html(self):
        for rec in self:
            rec.preview_html = f"""
                <iframe
                    src={f"/report/to_pdf/{rec._name}/{rec.id}"}
                    style="width:100%; height:100%; border:none;"
                    scrolling="true"
                    allow="autoplay; fullscreen; picture-in-picture" allowFullScreen="true"
                    frameborder="0"
                ></iframe>
            """

    def return_main_view(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Report view'),
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_mn_account_report.account_partner_ledger_excel_report_view').id,
            'target': 'new',
            'res_id': self.id,
            'res_model': self._name
        }
        view_id = self.env['ir.ui.view'].search([('model', '=', self._name), ('type', '=', 'form')], order='id desc', limit=1)
        if view_id:
            action['view_id'] = view_id.id
        return action

    def action_preview_report(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('PDF View'),
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'view_id': self.env.ref('vertexmon_tools.xls_report_base_preview').id,
            'res_model': self._name
        }
        return action

    def get_report_data(self):
        data = {'res_id': self.id}
        return data