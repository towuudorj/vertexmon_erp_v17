/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { useRecordObserver } from "@web/model/relational_model/utils";

/**
 * Float field that shows the record's `project_planned_info` as a toast
 * (instead of an onchange warning dialog) when the info changes.
 */
export class ProjectPlannedQtyField extends FloatField {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.lastInfo = this.props.record.data.project_planned_info || "";
        useRecordObserver((record) => {
            const info = record.data.project_planned_info || "";
            if (info && info !== this.lastInfo) {
                this.notification.add(info, {
                    title: "Төсөлд төлөвлөсөн тоо",
                    type: "warning",
                });
            }
            this.lastInfo = info;
        });
    }
}

registry.category("fields").add("project_planned_qty", {
    ...floatField,
    component: ProjectPlannedQtyField,
});
