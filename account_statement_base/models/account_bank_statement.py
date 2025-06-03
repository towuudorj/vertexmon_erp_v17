from odoo import _, models, api, fields 


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"



    @api.depends('line_ids.internal_index', 'line_ids.state')
    def _compute_date_index(self):
        for stmt in self:
            if stmt.line_ids:
                #sorted_lines = stmt.line_ids.sorted('internal_index')
                #stmt.first_line_index = sorted_lines[:1].internal_index
                stmt.date = stmt.date
            else:
                stmt.date = fields.Date.today()

    @api.depends('line_ids.journal_id')
    def _compute_journal_id(self):
        for statement in self:
            if statement.line_ids:
                statement.journal_id = statement.line_ids.journal_id
            else:
                statement.journal_id = statement.journal_id



    def action_open_statement_lines(self):
        self.ensure_one()
        if not self:
            return {}
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_statement_base.account_bank_statement_line_action"
        )
        action.update(
            {
                "domain": [("statement_id", "=", self.id)],
                "context": {
                    "default_statement_id": self.id,
                    "default_journal_id": self._context.get("active_id")
                    if self._context.get("active_model") == "account.journal"
                    else None,
                    "account_bank_statement_line_main_view": True,
                },
            }
        )

        return action

    def open_entries(self):
        self.ensure_one()
        return {
            "name": _("Journal Items"),
            "view_mode": "tree,form",
            "res_model": "account.move.line",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": {"search_default_group_by_move": 1, "expand": 1},
            "search_view_id": self.env.ref("account.view_account_move_line_filter").id,
            "domain": [
                "&",
                ("parent_state", "=", "posted"),
                ("statement_id", "=", self.id),
            ],
        }
