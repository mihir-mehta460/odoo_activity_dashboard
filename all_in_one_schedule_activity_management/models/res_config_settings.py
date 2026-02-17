from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    notify_on_due_date = fields.Boolean(
        'Notify on Due Date',
        help="Notify on the due date",
        config_parameter="notify_on_due_date"
    )
    notify_on_expiry = fields.Boolean(
        'Notify on Expiry',
        help="Notify on the expiry date",
        config_parameter="notify_on_expiry"
    )

    @api.model
    def get_values(self):
        """Returns a list of values for the given configuration fields"""
        res = super(ResConfigSettings, self).get_values()
        res['notify_on_due_date'] = self.env[
            'ir.config_parameter'].sudo().get_param('notify_on_due_date')
        res['notify_on_expiry'] = self.env[
            'ir.config_parameter'].sudo().get_param('notify_on_expiry')
        return res

