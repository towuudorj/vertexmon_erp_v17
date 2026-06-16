/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class NoFormatInteger extends Component {
    static template = "l10n_mn_payroll.NoFormatInteger";
    static props = {
        ...standardFieldProps,
    };

    onInputChange(ev) {
        const newValue = parseInt(ev.target.value || 0);
        this.props.record.update({[this.props.name]: newValue });
    }

    get displayValue() {
        const value = this.props.record.data[this.props.name];
        return (value !== false && value !== null) ? String(value) : "0";
    }
}

registry.category("fields").add("no_format_integer", {
    component: NoFormatInteger,
});