"""Provider base-classes:
    (Beginning of) the contract that cloud providers must follow, and shared
    types that support that contract.
"""
import abc
import os
import yaml

import paramiko
import six
import toolz

from bcbio import utils
from bcbio.pipeline import config_utils

from bcbiovm import log as logging
from bcbiovm.common import cluster as clusterops
from bcbiovm.container.docker import remap as docker_remap

LOG = logging.get_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseCloudProvider(object):

    """Contract class for all cloud providers.

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

    _CHMOD = "chmod %(mode)s %(file)s"
    _HOME_DIR = "echo $HOME"
    _SCREEN = "screen -d -m -S %(name)s bash -c '%(script)s &> %(output)s'"
    flavors = {}

    def __init__(self, name=None):
        self._name = name or self.__class__.__name__
        self._ecluster = clusterops.ElastiCluster(self._name)
        self._biodata_template = None

    @property
    def name(self):
        """The cloud provider name."""
        return self._name

    @abc.abstractmethod
    def get_storage_manager(self, name=None):
        """Return a cloud provider specific storage manager.

        :param name: The name of the required storage manager.
        """
        pass

    @abc.abstractmethod
    def information(self, cluster, config):
        """
        Get all the information available for this provider.

        The returned information will be used to create a status report
        regarding the bcbio instances.

        :config:    elasticluster config file
        :cluster:   cluster name

        :return:    an instance of :class bcbio.common.objects.Report:
        """
        pass

    @abc.abstractmethod
    def colect_data(self, cluster, config, rawdir):
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def bootstrap(self, cluster, config, reboot):
        """Install or update the the bcbio code and the tools with
        the latest version available.

        :param config:    elasticluster config file
        :param cluster:   cluster name
        :param reboot:    whether to upgrade and restart the host OS
        """
        pass

    @staticmethod
    def _execute_remote(connection, command):
        """Execute command on frontend node."""
        try:
            _, stdout, stderr = connection.exec_command(command)
        except paramiko.SSHException as exc:
            return (None, exc)

        return (stdout.read(), stderr.read())

    def get_flavor(self, machine=None):
        """Get the flavor for received machine type."""
        if not machine:
            return self.flavors.keys()
        else:
            return self.flavors.get(machine)

    def start(self, cluster, config=None, no_setup=False):
        """Create a cluster using the supplied configuration.

        :param cluster:   Type of cluster. It refers to a
                          configuration stanza [cluster/<name>].
        :param config:    Elasticluster config file
        :param no_setup:  Only start the cluster, do not configure it.
        """
        return self._ecluster.start(cluster, config, no_setup)

    def stop(self, cluster, config=None, force=False, use_default=False):
        """Stop a cluster and all associated VM instances.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        :param force:       Remove the cluster even if not all the nodes
                            have been terminated properly.
        :param use_default: Assume `yes` to all queries and do not prompt.
        """
        return self._ecluster.stop(cluster, config, force, use_default)

    def setup(self, cluster, config=None):
        """Configure the cluster.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        """
        return self._ecluster.setup(cluster, config)

    def ssh(self, cluster, config=None, ssh_args=None):
        """Connect to the frontend of the cluster using the `ssh` command.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        :ssh_args:          SSH command.

        Note:
            If the ssh_args are provided the command will be executed on
            the remote machine instead of opening an interactive shell.
        """
        return self._ecluster.ssh(cluster, config, ssh_args)

    def run_script(self, cluster, config, script):
        """Run a script on the frontend node inside a screen session.

        :param cluster:     Type of cluster. It refers to a
                            configuration stanza [cluster/<name>].
        :param config:      Elasticluster config file
        :param script:      The path of the script.
        """
        self._ecluster.load_config(config)
        cluster = self._ecluster.get_cluster(cluster)

        frontend = cluster.get_frontend_node()
        client = frontend.connect(known_hosts_file=cluster.known_hosts_file)

        home_dir, _ = self._execute_remote(client, self._HOME_DIR)
        script_name = os.path.basename(script)
        remote_file = os.path.join(home_dir.strip(), script_name)
        ouput_file = ("%(name)s.log" %
                      {"name": os.path.splitext(remote_file)[0]})
        screen_name = os.path.splitext(script_name)[0]

        sftp = client.open_sftp()
        sftp.put(script, remote_file)
        sftp.close()

        self._execute_remote(client, self._CHMOD %
                             {"mode": "a+x", "file": remote_file})
        self._execute_remote(client, self._SCREEN %
                             {"name": screen_name, "script": remote_file,
                              "output": ouput_file})
        client.close()

    @abc.abstractmethod
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
        pass


@six.add_metaclass(abc.ABCMeta)
class Pack(object):

    """Prepare a running process to execute remotely, moving files
    as necessary to shared infrastructure.
    """

    def _remove_empty(self, argument):
        """Remove null values in a nested set of arguments."""
        if isinstance(argument, (list, tuple)):
            output = []
            for item in argument:
                item = self._remove_empty(item)
                if item is not None:
                    output.append(item)
            return output
        elif isinstance(argument, dict):
            output = {}
            for key, value in argument.items():
                value = self._remove_empty(value)
                if value is not None:
                    output[key] = value
            return output if output else None
        else:
            return argument

    @staticmethod
    def _local_directories(args):
        """Retrieve known local work directory and biodata directories
        as baselines for buckets.
        """
        _, data = config_utils.get_dataarg(args)
        work_dir = toolz.get_in(["dirs", "work"], data)
        if "alt" in data["reference"]:
            if data["reference"]["alt"].keys() != [data["genome_build"]]:
                raise NotImplementedError("Need to support packing alternative"
                                          " references.")

        parts = toolz.get_in(["reference", "fasta",
                              "base"], data).split(os.path.sep)
        while parts:
            if parts.pop() == data["genome_build"]:
                break

        biodata_dir = os.path.sep.join(parts) if parts else None
        return (work_dir, biodata_dir)

    def _map_directories(self, args, shipping_config):
        """Map input directories into stable containers and folders for
        storing files.

        :shipping_config: instance of :class bcbiovm.object.ShippingConf:
        """
        output = {}
        external_count = 0
        directories = set()
        work_dir, biodata_dir = self._local_directories(args)

        def _callback(filename, *args):
            """Callback function for remap.walk_files."""
            # pylint: disable=unused-argument
            directory = os.path.dirname(os.path.abspath(filename))
            directories.add(os.path.normpath(directory))

        docker_remap.walk_files(args, _callback, {}, pass_dirs=True)
        for directory in sorted(directories):
            if work_dir and directory.startswith(work_dir):
                folder = directory.replace(work_dir, "").strip("/")
                container = shipping_config.containers["run"]
            elif biodata_dir and directory.startswith(biodata_dir):
                folder = directory.replace(biodata_dir, "").strip("/")
                container = shipping_config.containers["biodata"]
            else:
                folder = os.path.join("externalmap", str(external_count))
                container = shipping_config.containers["run"]
                external_count += 1

            output[directory] = {
                "container": container,
                "folder": folder,
                "shipping_config": shipping_config
            }

        return output

    def send_run_integrated(self, config):
        """Integrated implementation sending run results back
        to central store.
        """

        def finalizer(args):
            output = []
            for arg_set in args:
                new_args = self.send_run(arg_set, config)
                output.append(new_args)
            return output

        return finalizer

    @abc.abstractmethod
    def send_run(self, args, config):
        """Ship required processing files to the storage service for running
        on non-shared filesystem instances.

        :param config: an instances of :class objects.ShippingConf:
        """
        pass

    @abc.abstractmethod
    def _remap_and_ship(self, orig_fname, context, remap_dict):
        """Uploads files if not present in the specified container.

        Remap a file into an storage service container and key,
        shipping if not present.

        Each value from :param remap_dict: is an directory wich contains
        the following keys:
            * container:        The name of the container that contains
                                the blob. All blobs must be in a container.
            * folder            The name of the folder where the file
                                will be stored.
            * shipping_config   an instance of :class objects.ShippingConfig:
        """
        pass

    @abc.abstractmethod
    def send_output(self, config, out_file):
        """Send an output file with state information from a run.

        :param config: an instances of :class objects.ShippingConf:
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class Reconstitute(object):

    """Reconstitute an analysis in a temporary directory
    on the current machine.

    Handles copying or linking files into a work directory,
    running an analysis, then handing off outputs to ship
    back to subsequent processing steps.
    """

    @staticmethod
    def is_required_resource(context, parallel):
        fresources = parallel.get("fresources")
        if not fresources:
            return True
        for fresource in fresources:
            if context[:len(fresource)] == fresource:
                return True
        return False

    @staticmethod
    def prep_systemconfig(datadir, args):
        """Prepare system configuration files on bare systems
        if not present.
        """
        default_system = os.path.join(datadir, "galaxy", "bcbio_system.yaml")
        if utils.file_exists(default_system):
            return

        with open(default_system, "w") as out_handle:
            _, data = config_utils.get_dataarg(args)
            output = {"resources": toolz.get_in(["config", "resources"],
                                                data, {})}
            yaml.safe_dump(output, out_handle, default_flow_style=False,
                           allow_unicode=False)

    def prepare_datadir(self, pack, args):
        """Prepare the biodata directory.

        :param config: an instances of :class objects.ShippingConf:
        """
        # pylint: disable=no-self-use
        if "datadir" in pack.data:
            return pack.datadir, args

        raise ValueError("Cannot handle biodata directory "
                         "preparation type: %s" % pack.data)

    @abc.abstractmethod
    def get_output(self, target_file, pconfig):
        """Retrieve an output file from pack configuration."""
        pass

    @abc.abstractmethod
    def prepare_workdir(self, pack, parallel, args):
        """Unpack necessary files and directories into a temporary structure
        for processing.
        """
        pass
