"""
Common utilities and helper functions used by Azure Provider.
"""

from xml.etree import ElementTree

import requests

from bcbiovm import log as logging

LOG = logging.get_logger(__name__)


class AzureAPI(object):

    """Wrapper over the Windows Azure API."""

    def __init__(self, subscription_id, cert_file):
        self._subscription_id = subscription_id
        self._cert_file = cert_file
        self._host = ("https://management.core.windows.net/%(subscription)s/" %
                      {"subscription": subscription_id})
        self._ns = {
            "azure": "http://schemas.microsoft.com/windowsazure"
        }

    def cloud_services(self):
        """Returns a list of the cloud services that are available under
        the specified subscription.
        """
        output = set()
        response = requests.get(
            url=requests.compat.urljoin(
                self._host, "services/hostedservices"),
            cert=self._cert_file,
            headers={"Content-Type": "application/xml",
                     "x-ms-version": "2014-10-01"})

        if response.status_code == 200:
            try:
                root = ElementTree.fromstring(response.text)
                for host in root.findall("azure:HostedService", self._ns):
                    name = host.find("azure:ServiceName", self._ns)
                    if name is not None:
                        output.add(name.text)
            except ElementTree.ParseError as exc:
                LOG.exception(exc)
        else:
            LOG.error("Failed to get cloud services!")

        return output

    def security_groups(self):
        """Returns a list of the network security groups in the current
        subscription.
        """
        output = set()
        response = requests.get(
            url=requests.compat.urljoin(
                self._host, "services/networking/networksecuritygroups"),
            cert=self._cert_file,
            headers={"Content-Type": "application/xml",
                     "x-ms-version": "2014-10-01"})

        if response.status_code == 200:
            try:
                root = ElementTree.fromstring(response.text)
                network_sg = root.findall('azure:NetworkSecurityGroup',
                                          self._ns)
                for security_group in network_sg:
                    name = security_group.find("azure:Name", self._ns)
                    if name is not None:
                        output.add(name.text)
            except ElementTree.ParseError as exc:
                LOG.exception(exc)
        else:
            LOG.error("Failed to get security groups !")

        return output
