"""Run on a cluster using IPython parallel."""

import os

import yaml
from bcbio.distributed import clargs
from bcbio.pipeline import main

from bcbiovm import log as logging
from bcbiovm.client import base
from bcbiovm.common import constant
from bcbiovm.container.docker import common as docker_common
from bcbiovm.container.docker import mounts as docker_mounts
from bcbiovm.ipython import batchprep
from bcbiovm.provider import factory as provider_factory

LOG = logging.get_logger(__name__)


class IPython(base.Command):

    """Run on a cluster using IPython parallel."""

    def __init__(self, parent, parser):
        super(IPython, self).__init__(parent, parser)
        self._need_prologue = True
        self._need_datadir = True

    def setup(self):
        """Extend the parser configuration in order to expose this command."""
        parser = self._parser.add_parser(
            "ipython",
            help="Run on a cluster using IPython parallel.")
        parser.add_argument(
            "sample_config",
            help="YAML file with details about samples to process.")
        parser.add_argument(
            "scheduler", help="Scheduler to use.",
            choices=["lsf", "sge", "torque", "slurm", "pbspro"])
        parser.add_argument(
            "queue", help="Scheduler queue to run jobs on.")
        parser.add_argument(
            "-r", "--resources",
            help=("Cluster specific resources specifications. "
                  "Can be specified multiple times.\n"
                  "Supports SGE and SLURM parameters."),
            default=[], action="append")
        parser.add_argument(
            "--fcdir",
            help="A directory of Illumina output or fastq files to process",
            type=lambda path: (os.path.abspath(os.path.expanduser(path))))
        parser.add_argument(
            "--systemconfig",
            help=("Global YAML configuration file specifying system details. "
                  "Defaults to installed bcbio_system.yaml."))
        parser.add_argument(
            "-n", "--numcores", type=int, default=1,
            help="Total cores to use for processing")
        parser.add_argument(
            "--timeout", default=15, type=int,
            help=("Number of minutes before cluster startup times out."
                  "Defaults to 15"))
        parser.add_argument(
            "--retries", default=0, type=int,
            help=("Number of retries of failed tasks during distributed "
                  "processing. Default 0 (no retries)"))
        parser.add_argument(
            "-t", "--tag", default="",
            help="Tag name to label jobs on the cluster")
        parser.add_argument(
            "--tmpdir",
            help="Path of local on-machine temporary directory to process in.")
        parser.set_defaults(work=self.run)

    def prologue(self):
        """Executed once before the arguments parsing."""
        # Add user configured defaults to supplied command line arguments.
        self.defaults.add_defaults()
        # Retrieve supported remote inputs specified on the command line.
        self.defaults.retrieve()
        # Check if the datadir exists if it is required.
        self.defaults.check_datadir("Could not run IPython parallel "
                                    "analysis.")
        # Add all the missing arguments related to docker image.
        self.install.image_defaults()

    def work(self):
        """Run the command with the received information."""
        work_dir = os.getcwd()
        ready_config_file = os.path.join(
            work_dir, "%s-ready%s" %
            (os.path.splitext(os.path.basename(self.args.sample_config))))

        parallel = clargs.to_parallel(self.args, "bcbiovm.container.docker")
        parallel["wrapper"] = "runfn"

        LOG.debug("Loading the config: %s", self.args.sample_config)
        with open(self.args.sample_config) as in_handle:
            ready_config, _ = docker_mounts.normalize_config(
                yaml.load(in_handle), self.args.fcdir)

        LOG.debug("Writing the %s file.", ready_config_file)
        with open(ready_config_file, "w") as out_handle:
            yaml.safe_dump(ready_config, out_handle, default_flow_style=False,
                           allow_unicode=False)

        systemconfig = docker_common.local_system_config(
            config=self.args.systemconfig, work_dir=work_dir,
            datadir=self.args.datadir)

        ship_conf = provider_factory.get_ship_config("shared")
        parallel["wrapper_args"] = [
            constant.DOCKER,
            {
                "sample_config": ready_config_file,
                "fcdir": self.args.fcdir,
                "pack": ship_conf(work_dir, self.args.datadir,
                                  self.args.tmpdir),
                "systemconfig": systemconfig,
                "image": self.args.image
            }]

        # For testing, run on a local ipython cluster
        parallel["run_local"] = parallel.get("queue") == "localrun"

        main.run_main(work_dir,
                      run_info_yaml=ready_config_file,
                      config_file=systemconfig,
                      fc_dir=self.args.fcdir,
                      parallel=parallel)

        # Approach for running main function inside of docker.
        # Could be useful for architectures where we can spawn docker
        # jobs from docker.
        #
        # cmd_args = {
        #     "systemconfig": systemconfig,
        #     "image": args.image,
        #     "pack": cur_pack,
        #     "sample_config": args.sample_config,
        #     "fcdir": args.fcdir,
        #     "orig_systemconfig": args.systemconfig
        # }
        # main_args = [work_dir, ready_config_file, systemconfig,
        #              args.fcdir, parallel]
        # run.do_runfn("run_main", main_args, cmd_args, parallel,
        #              content.DOCKER)


class IPythonPrep(base.Command):

    """Prepare a batch script to run bcbio on a scheduler."""

    def setup(self):
        """Extend the parser configuration in order to expose this command."""
        parser = self._parser.add_parser(
            "ipythonprep",
            help="Prepare a batch script to run bcbio on a scheduler.")
        parser.add_argument(
            "sample_config",
            help="YAML file with details about samples to process.")
        parser.add_argument(
            "--fcdir",
            help="A directory of Illumina output or fastq files to process",
            type=lambda path: (os.path.abspath(os.path.expanduser(path))))
        parser.add_argument(
            "--systemconfig",
            help=("Global YAML configuration file specifying system details. "
                  "Defaults to installed bcbio_system.yaml."))
        parser.add_argument(
            "-n", "--numcores", type=int, default=1,
            help="Total cores to use for processing")
        parser.add_argument(
            "scheduler", help="Scheduler to use.",
            choices=["lsf", "sge", "torque", "slurm", "pbspro"])
        parser.add_argument(
            "queue", help="Scheduler queue to run jobs on.")
        parser.add_argument(
            "-r", "--resources",
            help=("Cluster specific resources specifications. "
                  "Can be specified multiple times.\n"
                  "Supports SGE and SLURM parameters."),
            default=[], action="append")
        parser.add_argument(
            "--timeout", default=15, type=int,
            help=("Number of minutes before cluster startup times out."
                  "Defaults to 15"))
        parser.add_argument(
            "--retries", default=0, type=int,
            help=("Number of retries of failed tasks during distributed "
                  "processing. Default 0 (no retries)"))
        parser.add_argument(
            "-t", "--tag", default="",
            help="Tag name to label jobs on the cluster")
        parser.add_argument(
            "--tmpdir",
            help="Path of local on-machine temporary directory to process in.")
        parser.set_defaults(work=self.run)

    def prologue(self):
        """Executed once before the arguments parsing."""
        # Add user configured defaults to supplied command line arguments.
        self.defaults.add_defaults()
        # Retrieve supported remote inputs specified on the command line.
        self.defaults.retrieve()
        # Check if the datadir exists if it is required.
        self.defaults.check_datadir("Could not prep batch scripts.")

    def work(self):
        """Run the command with the received information."""
        return batchprep.submit_script(self.args)

    def task_done(self, result):
        """What to execute after successfully finished processing a task."""
        commands = {"slurm": "sbatch", "sge": "qsub",
                    "lsf": "bsub", "torque": "qsub",
                    "pbspro": "qsub"}

        LOG.info("Start analysis with: %(command)s %(outfile)s",
                 {"command": commands[self.args.scheduler], "outfile": result})
