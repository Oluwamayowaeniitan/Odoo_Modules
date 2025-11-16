from odoo import http
from odoo.http import request
import requests, json, logging

_logger = logging.getLogger(__name__)

class PaystackFundingController(http.Controller):

    @http.route('/wallet/fund', type='http', auth='public', website=True)
    def fund_form(self, **kw):
        return request.render("wallet_online_funding.wallet_fund_page", {})

    @http.route('/wallet/fund/submit', type='http', auth='public', website=True, csrf=False)
    def fund_submit(self, **post):
        name = post.get("name")
        email = post.get("email")
        amount = float(post.get("amount")) * 100

        secret = request.env["ir.config_parameter"].sudo().get_param(
            "wallet_online_funding.paystack_secret_key"
        )

        callback_url = "https://somisteam.easyappz.com/wallet/paystack/webhook"

        payload = {"email": email, "amount": int(amount), "metadata": {"name": name}}
        headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

        init_url = "https://api.paystack.co/transaction/initialize"
        res = requests.post(init_url, headers=headers, data=json.dumps(payload)).json()

        if not res.get("status"):
            return "Error initializing Paystack payment"

        return request.redirect(res["data"]["authorization_url"])

    @http.route('/wallet/paystack/webhook', type='json', auth='public', csrf=False)
    def paystack_webhook(self, **kw):
        data = json.loads(request.httprequest.data)

        if data.get("event") != "charge.success":
            return {"status": "ignored"}

        ref = data["data"]["reference"]
        email = data["data"]["customer"]["email"]
        amount = data["data"]["amount"] / 100
        name = data["data"]["metadata"].get("name")

        secret = request.env["ir.config_parameter"].sudo().get_param(
            "wallet_online_funding.paystack_secret_key"
        )

        existing = request.env["wallet.fund.log"].sudo().search([("reference", "=", ref)])
        if existing:
            return {"status": "duplicate"}

        verify = requests.get(
            f"https://api.paystack.co/transaction/verify/{ref}",
            headers={"Authorization": f"Bearer {secret}"},
        ).json()

        if not verify.get("status"):
            return {"status": "verification_failed"}

        partner = request.env["res.partner"].sudo().search([("email", "=", email)], limit=1)
        if not partner:
            partner = request.env["res.partner"].sudo().search([("name", "=", name)], limit=1)

        if not partner:
            return {"status": "customer_not_found"}

        partner.add_wallet_amount(amount)

        request.env["wallet.fund.log"].sudo().create({
            "reference": ref, "amount": amount, "partner_id": partner.id
        })

        return {"status": "success"}