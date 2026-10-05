from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Өмнө нь first_line_index тооцогдоогүй байсан тул бүх хуулгад дахин тооцоолно
    env = api.Environment(cr, SUPERUSER_ID, {})
    statements = env["account.bank.statement"].search([])
    env.add_to_compute(statements._fields["first_line_index"], statements)
    statements.flush_model(["first_line_index"])
