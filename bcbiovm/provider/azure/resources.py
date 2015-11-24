"""
Helper class for collecting and processing information regarding
resources usage.
"""
import os

import toolz

from bcbiovm import log as logging
from bcbiovm.common import constant
from bcbiovm.provider.common import resources
from bcbiovm.provider.azure import common as azure_common

LOG = logging.get_logger(__name__)


class Report(resources.Report):

    """
    Collect information from the cluster and create a report
    with them.
    """

    def __init__(self, config, cluster):
        """
        :param config:    elasticluster config file
        :param cluster:   cluster name
        """
        super(Report, self).__init__(config=config, cluster=cluster,
                                     provider=constant.PROVIDER.AZURE)
        self._api = azure_common.AzureAPI(
            subscription_id=toolz.get_in(["cloud", "subscription_id"],
                                         self._cluster_config),
            cert_file=os.path.abspath(toolz.get_in(["cloud", "certificate"],
                                                   self._cluster_config)))

    def add_security_groups_info(self):
        """Add information regarding security groups."""
        sg_section = self._information.add_section(
            name="sg", title="Security groups")
        sg_section.add_field("sg", "Security Group")

        expected_sg_name = toolz.get_in(["cluster", "security_group"],
                                        self._cluster_config)
        security_groups = self._api.security_groups()

        if not security_groups:
            LOG.warning("No security groups defined.")
            return

        if expected_sg_name in security_groups:
            LOG.info("Expected security group %(sg_name)s exists.",
                     {"sg_name": expected_sg_name})
        else:
            LOG.warning("Security group %(sg_name)s does not exist.",
                        {"sg_name": expected_sg_name})

        sg_section.add_items(security_groups)

    def add_instance_info(self):
        """Add information regarding each instance from cluster."""
        instance_section = self._information.add_section(
            name="instance", title="Instances from current cluster"
        )

        instance_section.add_field("name", "Name")
        instance_section.add_field("type", "Type")
        instance_section.add_field("state", "State")
        instance_section.add_field("ip", "IP Address")
        instance_section.add_field("placement", "Placement")
