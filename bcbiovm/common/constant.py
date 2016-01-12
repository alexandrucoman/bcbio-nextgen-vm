"""
Shared constants across the bcbio-nextgen-vm project.
"""

import logging
import os
import sys

# pylint: disable=no-init,old-style-class

DOCKER = {
    "port": 8085,
    "biodata_dir": "/usr/local/share/bcbio-nextgen",
    "work_dir": "/mnt/work",
    "image_url": "bcbio/bcbio",
}


class ANSIBLE:

    """Ansible specific settings."""

    FORKS = 10
    KEY_CHECKING = "False"


class PATH:

    """Default paths used across the project."""

    ANSIBLE_BASE = os.path.join(sys.prefix, "share", "bcbio-vm", "ansible")
    BCBIO = os.path.join(os.path.expanduser("~"), '.bcbio')
    EC = os.path.join(BCBIO, "elasticluster")
    EC_CONFIG = os.path.join(EC, "{provider}.config")


class PROVIDER:

    """Contains the available providers' name."""

    AWS = "aws"
    AZURE = "azure"


class SSH:

    """SSH specific settings."""

    HOST = '127.0.0.1'
    PORT = 22
    USER = 'root'
    PROXY = ('ssh -o VisualHostKey=no -W %(host)s:%(port)d '
             '%(user)s@%(bastion)s')


DEFAULTS = {
    "bcbio.repo": "https://github.com/chapmanb/bcbio-nextgen.git",
    "bcbio.branch": "master",
    "docker.image": "bcbio/bcbio",
    "docker.bcbio_image": "bcbio-nextgen-docker-image.gz",
    "env.BCBIO_PROVIDER": PROVIDER.AWS,
    "log.verbosity": 0,
    "log.file.level": logging.DEBUG,
    "log.file.format": "%(asctime)s,%(name)s,%(levelname)s,%(message)s",
    "supported.genomes": ["GRCh37", "hg19", "hg38", "hg38-noalt", "mm10",
                          "mm9", "rn6", "rn5", "canFam3", "dm3", "galGal4",
                          "phix", "pseudomonas_aeruginosa_ucbpp_pa14",
                          "sacCer3", "TAIR10", "WBcel235", "xenTro3", "Zv9",
                          "GRCz10"],
    "supported.indexes": ["bowtie", "bowtie2", "bwa", "novoalign", "rtg",
                          "snap", "star", "ucsc", "seq", "hisat2"],
}

ENVIRONMENT = {
    "development": {
        "conda.channels": ("bioconda", "bcbio-dev"),
        "conda.package": "bcbio-nextgen-vm",
        "log.cli.format": "%(name)s - [%(levelname)s]: %(message)s",
        "log.cli.level": logging.DEBUG,
        "log.file.path": "/tmp/bcbio/bcbiovm-devel-cli.log",
        "misc.attempts": 3,
        "misc.retry_interval": 0.1,
    },

    "production": {
        "conda.channels": ("bioconda", ),
        "conda.package": "bcbio-nextgen-vm",
        "log.cli.format": "[%(levelname)s]: %(message)s",
        "log.cli.level": logging.INFO,
        "log.file.path": "/tmp/bcbio/bcbiovm-cli.log",
        "misc.attempts": 4,
        "misc.retry_interval": 0.5,
    }
}
