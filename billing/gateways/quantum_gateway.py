
from django.conf import settings

from billing import Gateway
from billing.signals import transaction_was_successful, transaction_was_unsuccessful
from billing.utils.credit_card import Visa, MasterCard, Discover, AmericanExpress, InvalidCard

from django.template.loader import render_to_string
from datetime import datetime
import requests
from lxml import etree


def xml_to_dict(xml):
    d = {}
    for child in xml:
        if len(child):
            d[child.tag] = xml_to_dict(child)
        else:
            d[child.tag] = child.text
    return d


class QuantumGateway(Gateway):
    """
    Quantum Gateway XML Requester 
    http://www.quantumgateway.com/files/QuantumGatewayXMLRequester.pdf
    """
    request_url = 'https://secure.quantumgateway.com/cgi/xml_requester.php'
    supported_cardtypes = [Visa, MasterCard, Discover, AmericanExpress]
    default_currency = "USD"
    display_name = "Quantum"

    def _parse_xml(self, text):
        return etree.fromstring(text)

    def _build_request_xml(self, amount, credit_card, options):
        # required fields
        data = {
            'gateway_login': settings.MERCHANT_SETTINGS['gateway_login'],
            'gateway_key': settings.MERCHANT_SETTINGS['gateway_key'],
            'request_type': 'ProcessSingleTransaction',
            'transaction_type': 'CREDIT',
            'payment_type': 'CC',
            'amount': amount, 
            'cc_number': credit_card.number,
            'expire_month': credit_card.month,
            'expire_year': credit_card.year,
            'cvv': credit_card.verification_value,
            'transaction_date': datetime.today()
        }
        if options:
            data.update(options)
        return render_to_string("billing/quantum_request.xml", data).encode('utf-8')

    def handle_response(self, response, type):
        response_code = response.status_code
        xml = self._parse_xml(response.text)
        result = xml_to_dict(xml)
        if result.get('Result').get('ErrorCode'):
            transaction_was_unsuccessful.send(self, type=type, 
                response=response, response_code=response_code)
        else:
            transaction_was_successful.send(self, type=type, 
                response=response, response_code=response_code)
        return result

    def purchase(self, amount, credit_card, options=None):
        """Process Single Transaction"""
        if not self.validate_card(credit_card):
            raise InvalidCard("Invalid Card")

        headers = {'Content-Type':'text/xml'}
        xml = self._build_request_xml(amount, credit_card, options)
        files = {'file': ('quantum_request.xml', xml, 'text/xml')}
        response = requests.post(self.request_url, files=files, headers=headers)
        return self.handle_response(response, 'purchase')       


    def authorize(self, money, credit_card, options = None):
        raise NotImplementedError

    def capture(self, money, authorization, options = None):
        raise NotImplementedError

    def void(self, identification, options = None):
        raise NotImplementedError

    def credit(self, money, identification, options = None):
        raise NotImplementedError

    def recurring(self, money, creditcard, options = None):
        raise NotImplementedError

    def store(self, creditcard, options = None):
        raise NotImplementedError

    def unstore(self, identification, options = None):
        raise NotImplementedError
