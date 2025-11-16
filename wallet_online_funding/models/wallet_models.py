from odoo import models, fields

class WalletFundLog(models.Model):
    _name = "wallet.fund.log"
    _description = "Paystack Funding Log"

    reference = fields.Char(required=True)
    amount = fields.Float(required=True)
    partner_id = fields.Many2one("res.partner", required=True)

class ResPartner(models.Model):
    _inherit = "res.partner"

    def add_wallet_amount(self, amount):
        wallet = self.env['pos.gift.card'].search([('customer_id', '=', self.id)], limit=1)
        if not wallet:
            raise Exception("Customer has no eWallet configured")
        wallet.balance += amount
        return True