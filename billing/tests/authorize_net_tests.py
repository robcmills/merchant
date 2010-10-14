from django.test import TestCase
from django.conf import settings
from billing import get_gateway, CreditCard
from billing.signals import *
from billing.models import AuthorizeAIMResponse
from billing.gateway import CardNotSupported

class AuthorizeNetAIMGatewayTestCase(TestCase):
    def setUp(self):
        self.merchant = get_gateway("authorize_net")
        self.merchant.test_mode = True
        self.credit_card = CreditCard(first_name="Test", last_name="User",
                                      month=10, year=2011, 
                                      number="4222222222222222", 
                                      verification_value="100")

    def testCardSupported(self):
        self.credit_card.number = "5019222222222222"
        self.assertRaises(CardNotSupported, 
                          self.merchant.purchase(1000, self.credit_card))

    def testCardValidated(self):
        self.merchant.test_mode = False
        self.assertFalse(self.merchant.validate(self.credit_card))

    def testPurchase(self):
        resp = self.merchant.purchase(1, self.credit_card)
        self.assertEquals(resp.status, "SUCCESS")
        # In test mode, the transaction ID from Authorize.net is 0
        self.assertEquals(resp.transaction_id, "0")
        self.assertTrue(isinstance(resp.actual, AuthorizeAIMResponse)) 

    def testPaymentSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        payment_was_successful.connect(receive)

        resp = self.merchant.purchase(1000, self.credit_card)
        self.assertEquals(received_signals, [payment_was_successful])

    def testPaymentUnSuccessfulSignal(self):
        received_signals = []

        def receive(sender, **kwargs):
            received_signals.append(kwargs.get("signal"))

        payment_was_unsuccessful.connect(receive)

        resp = self.merchant.purchase(6, self.credit_card)
        self.assertEquals(received_signals, [payment_was_unsuccessful])

    def testCreditCardExpired(self):
        resp = self.merchant.purchase(8, self.credit_card)
        self.assertNotEquals(resp.status, "SUCCESS")
