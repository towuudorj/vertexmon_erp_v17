from odoo import models


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def write(self, vals):
        amount_changed = 'amount' in vals

        result = super().write(vals)

        if (
            amount_changed
            and not self.env.context.get(
                'skip_recompute_following'
            )
        ):
            self.action_recompute_following_lines()

        return result

    def action_recompute_following_lines(self):
        for line in self:

            payslip = line.slip_id

            if not payslip:
                continue

            if payslip.state != 'draft':
                continue

            contract = line.contract_id

            if not contract:
                continue

            # Recalculate starting AFTER this line's sequence
            result_lines = self.env['hr.payslip']._get_payslip_lines(
                [contract.id],
                payslip.id,
                from_sequence=line.sequence,
            )

            result_map = {
                (
                    result['salary_rule_id'],
                    result['contract_id'],
                ): result
                for result in result_lines
            }

            # -----------------------------------------------------
            # Update only lines AFTER changed line
            # -----------------------------------------------------

            following_lines = payslip.line_ids.filtered(
                lambda l:
                    l.contract_id.id == contract.id
                    and l.sequence > line.sequence
                    and l.salary_rule_id
            )

            for existing_line in following_lines:

                result = result_map.get(
                    (
                        existing_line.salary_rule_id.id,
                        contract.id,
                    )
                )

                if not result:
                    continue

                existing_line.with_context(
                    skip_recompute_following=True
                ).write({
                    'amount': result['amount'],
                    'quantity': result['quantity'],
                    'rate': result['rate'],
                    'total': (
                        result['amount']
                        * result['quantity']
                        * result['rate']
                        / 100.0
                    ),
                })