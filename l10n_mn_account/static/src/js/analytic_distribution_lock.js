/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";

// Түгжээтэй шинжилгээний дансыг хуваарилалтын сонголтод харуулахгүй
patch(AnalyticDistribution.prototype, {
    recordProps(line) {
        const props = super.recordProps(...arguments);
        for (const [name, field] of Object.entries(props.fields)) {
            if (name.startsWith("x_plan") && field.relation === "account.analytic.account") {
                field.domain = [...(field.domain || []), ["is_locked", "=", false]];
            }
        }
        return props;
    },
});
