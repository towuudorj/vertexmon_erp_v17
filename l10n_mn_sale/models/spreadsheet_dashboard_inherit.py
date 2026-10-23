import base64
import json

from odoo import api, models

MIN_COL_SIZE = 160
SPACER_COL_SIZE = 50


class SpreadsheetDashboard(models.Model):
    _inherit = 'spreadsheet.dashboard'

    @api.model
    def _widen_dashboard_columns(self):
        """Widen narrow columns of every dashboard sheet so large amounts are not truncated."""
        for dashboard in self.search([]):
            try:
                data = json.loads(base64.b64decode(dashboard.spreadsheet_binary_data))
            except (ValueError, TypeError):
                continue
            changed = False
            for sheet in data.get('sheets', []):
                if sheet.get('name') != 'Dashboard':
                    continue
                for col in sheet.get('cols', {}).values():
                    if SPACER_COL_SIZE < col.get('size', 0) < MIN_COL_SIZE:
                        col['size'] = MIN_COL_SIZE
                        changed = True
            if changed:
                dashboard.spreadsheet_binary_data = base64.b64encode(
                    json.dumps(data, ensure_ascii=False).encode())
