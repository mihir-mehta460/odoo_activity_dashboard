from odoo import models, fields, api

class ActivityWizard(models.TransientModel):
    _name = 'activity.wizard'
    _description = 'Activity Wizard'

    # Fields for the wizard
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    summary = fields.Char(string='Summary')
    date_deadline = fields.Date(string='Due Date')
    user_id = fields.Many2one('res.users', string='Assigned To')
    note = fields.Text(string='Notes')

    # Action for saving the wizard data to the actual model
    def action_save(self):
        # Here you would define how to save the data entered in the wizard
        # For example, creating an activity record from the wizard fields
        activity_vals = {
            'activity_type_id': self.activity_type_id.id,
            'summary': self.summary,
            'date_deadline': self.date_deadline,
            'user_id': self.user_id.id,
            'note': self.note,
        }
        self.env['mail.activity'].create(activity_vals)
        return {'type': 'ir.actions.act_window_close'}  # Close the wizard after saving

    # Action to cancel (close the wizard without saving)
    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
