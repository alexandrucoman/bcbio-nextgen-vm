"""Azure Cloud Provider for bcbiovm."""
# pylint: disable=no-self-use
import os

from bcbiovm import log as loggig
from bcbiovm.common import constant
from bcbiovm.common import exception
from bcbiovm.common import objects
from bcbiovm.common import utils as common_utils
from bcbiovm.provider import base
from bcbiovm.provider.common import bootstrap as common_bootstrap
from bcbiovm.provider.azure import storage as azure_storage

LOG = loggig.get_logger(__name__)


class AzureProvider(base.BaseCloudProvider):

    """Azure Provider for bcbiovm.

    :ivar flavors: A dictionary with all the flavors available for
                   the current cloud provider.

    Example:
    ::
        flavors = {
            "m3.large": Flavor(cpus=2, memory=3500),
            "m3.xlarge": Flavor(cpus=4, memory=3500),
            "m3.2xlarge": Flavor(cpus=8, memory=3500),
        }
    """

    # More information regarding Azure instances types can be found on the
    # following link: https://goo.gl/mEjiC5
    flavors = {
        "ExtraSmall": objects.Flavor(cpus=1, memory=768),
        "Small": objects.Flavor(cpus=1, memory=1792),
        "Medium": objects.Flavor(cpus=2, memory=3584),
        "Large": objects.Flavor(cpus=4, memory=7168),
        "ExtraLarge": objects.Flavor(cpus=8, memory=14336),

        # General Purpose: For websites, small-to-medium databases,
        #                  and other everyday applications.
        "A0": objects.Flavor(cpus=1, memory=768),        # 0.75 GB
        "A1": objects.Flavor(cpus=1, memory=1792),       # 1.75 GB
        "A2": objects.Flavor(cpus=2, memory=3584),       # 3.50 GB
        "A3": objects.Flavor(cpus=4, memory=7168),       # 7.00 GB
        "A4": objects.Flavor(cpus=8, memory=14336),      # 14.00 GB

        # Memory Intensive: For large databases, SharePoint server farms,
        #                   and high-throughput applications.
        "A5": objects.Flavor(cpus=2, memory=14336),      # 14.00 GB
        "A6": objects.Flavor(cpus=4, memory=28672),      # 28.00 GB
        "A7": objects.Flavor(cpus=8, memory=57344),      # 56.00 GB

        # Network optimized: Ideal for Message Passing Interface (MPI)
        #                    applications, high-performance clusters,
        #                    modeling and simulations and other compute
        #                    or network intensive scenarios.
        "A8": objects.Flavor(cpus=8, memory=57344),      # 56.00 GB
        "A9": objects.Flavor(cpus=16, memory=114688),    # 112.00 GB

        # Compute Intensive: For high-performance clusters, modeling
        #                    and simulations, video encoding, and other
        #                    compute or network intensive scenarios.
        "A10": objects.Flavor(cpus=8, memory=57344),     # 56.00 GB
        "A11": objects.Flavor(cpus=16, memory=114688),   # 112.00 GB

        # Optimized compute: 60% faster CPUs, more memory, and local SSD
        # General Purpose: For websites, small-to-medium databases,
        #                  and other everyday applications.
        "D1": objects.Flavor(cpus=1, memory=3584),       # 3.50 GB
        "D2": objects.Flavor(cpus=2, memory=7168),       # 7.00 GB
        "D3": objects.Flavor(cpus=4, memory=14336),      # 14.00 GB
        "D4": objects.Flavor(cpus=8, memory=28672),      # 28.00 GB

        # Memory Intensive: For large databases, SharePoint server farms,
        #                   and high-throughput applications.
        "D11": objects.Flavor(cpus=2, memory=14336),     # 14.00 GB
        "D12": objects.Flavor(cpus=4, memory=28672),     # 28.00 GB
        "D13": objects.Flavor(cpus=8, memory=57344),     # 56.00 GB
        "D14": objects.Flavor(cpus=16, memory=114688),   # 112.00 GB
    }
    _STORAGE = {"AzureBlob": azure_storage.AzureBlob}

    def __init__(self):
        super(AzureProvider, self).__init__(name=constant.PROVIDER.AZURE)
        self._biodata_template = ("https://bcbio.blob.core.windows.net/biodata"
                                  "/prepped/{build}/{build}-{target}.tar.gz")

    def get_storage_manager(self, name="AzureBlob"):
        """Return a cloud provider specific storage manager.

        :param name: The name of the required storage manager.
        """
        return self._STORAGE.get(name)()

    def information(self, config, cluster):
        """
        Get all the information available for this provider.

        The returned information will be used to create a status report
        regarding the bcbio instances.

        :config:          elasticluster config file
        :cluster:         cluster name
        """
        raise exception.NotSupported(feature="Method information",
                                     context="Azure provider")

    def colect_data(self, config, cluster, rawdir):
        """Collect from the each instances the files which contains
        information regarding resources consumption.

        :param config:    elasticluster config file
        :param cluster:   cluster name
        :param rawdir:    directory where to copy raw collectl data files.

        Notes:
            The current workflow is the following:
                - establish a SSH connection with the instance
                - get information regarding the `collectl` files
                - copy to local the files which contain new information

            This files will be used in order to generate system statistics
            from bcbio runs. The statistics will contain information regarding
            CPU, memory, network, disk I/O usage.
        """
        raise exception.NotSupported(feature="Method collect_data",
                                     context="Azure provider")

    def resource_usage(self, bcbio_log, rawdir):
        """Generate system statistics from bcbio runs.

        Parse the files obtained by the :meth colect_data: and put the
        information in :class pandas.DataFrame:.

        :param bcbio_log:   local path to bcbio log file written by the run
        :param rawdir:      directory to put raw data files

        :return: a tuple with two dictionaries, the first contains
                 an instance of :pandas.DataFrame: for each host and
                 the second one contains information regarding the
                 hardware configuration
        :type return: tuple
        """
        raise exception.NotSupported(feature="Method resource_usage",
                                     context="Azure provider")

    def bootstrap(self, config, cluster, reboot):
        """Install or update the bcbio-nextgen code and the tools
        with the latest version available.

        :param config:    elasticluster config file
        :param cluster:   cluster name
        :param reboot:    whether to upgrade and restart the host OS
        """
        bootstrap = common_bootstrap.Bootstrap(provider=self, config=config,
                                               cluster_name=cluster,
                                               reboot=reboot)
        return bootstrap.run()

    def upload_biodata(self, genome, target, source, context):
        """Upload biodata for a specific genome build and target to a storage
        manager.

        :param genome:  Genome which should be uploaded.
        :param target:  The pice from the genome that should be uploaded.
        :param source:  A list of directories which contain the information
                        that should be uploaded.
        :param context: A dictionary that may contain useful information
                        for the cloud provider (credentials, headers etc).
        """
        storage_manager = self.get_storage_manager()
        biodata = self._biodata_template.format(build=genome, target=target)

        try:
            archive = common_utils.compress(source)
            file_info = storage_manager.parse_remote(biodata)
            if storage_manager.exists(file_info.container, file_info.blob,
                                      context):
                LOG.info("The %(biodata)r build already exist",
                         {"biodata": file_info.blob})
                return
            LOG.info("Upload pre-prepared genome data: %(genome)s, "
                     "%(target)s:", {"genome": genome, "target": target})
            storage_manager.upload(path=archive, filename=file_info.blob,
                                   container=file_info.container,
                                   context=context)
        finally:
            if os.path.exists(archive):
                os.remove(archive)
