"""Subcommands available for Azure provider."""
import os
import shutil

from bcbiovm import log as logging
from bcbiovm.client import base
from bcbiovm.common import utils
from bcbiovm.common import exception

LOG = logging.get_logger(__name__)


class DataDirectory(base.Command):

    """Create the datadir and add initial data."""

    def setup(self):
        """Extend the parser configuration in order to expose this command."""
        parser = self._parser.add_parser(
            "datadir", help="Create and setup the datadir.")
        parser.add_argument(
            "--path", default="~/install/bcbio-vm/data",
            help=("The location for the datadir. "
                  "[default: ~/install/bcbio-vm/data]"))
        parser.add_argument(
            "-f", "--force", default=False, action="store_true",
            help="Overwrite the datadir if already exits.")

        parser.set_defaults(work=self.run)

    def prologue(self):
        """Executed once before the command running."""
        if self.args.force:
            return

        self.args.path = os.path.abspath(self.args.datadir or self.args.path)
        if os.path.exists(self.args.path):
            raise exception.BCBioException("The datadir already exists.")

    def work(self):
        """Run the command with the received information."""
        if os.path.exists(self.args.path) and self.args.force:
            shutil.rmtree(self.args.path)

        os.makedirs(self.args.path)

    def epilogue(self):
        """Executed once after the command running."""
        if os.path.exists('/usr/local/share/bcbio_nextgen/genomes'):
            os.symlink(source='/usr/local/share/bcbio_nextgen/genomes',
                       link_name=os.path.join(self.args.path, "genomes"))
        if os.path.exists('/usr/local/share/gemini/data'):
            os.symlink(source='/usr/local/share/bcbio_nextgen/genomes',
                       link_name=os.path.join(self.args.path, "gemini_data"))

    def task_done(self, result):
        """What to execute after successfully finished processing a task."""
        super(DataDirectory, self).task_done(result)
        LOG.info("The datadir was successfully created.")

    def task_fail(self, exc):
        """What to do when the program fails processing a task."""
        if isinstance(exc, exception.BCBioException):
            LOG.error("The private key already exists. In order to "
                      "overwrite it the --force argument can be used.")
        else:
            super(DataDirectory, self).task_fail(exc)


class ManagementCertificate(base.Command):

    """Generate a management certificate."""

    def __init__(self, parent, parser):
        super(ManagementCertificate, self).__init__(parent, parser)
        self._ssh_path = os.path.join(os.path.expanduser("~"), ".ssh")

    def _get_subject(self):
        """Return the information regarding client in subject format."""
        subject = []
        if self.args.country:
            subject.append("/C={}".format(self.args.country))
        if self.args.state:
            subject.append("/ST={}".format(self.args.state))
        if self.args.organization:
            subject.append("/O={}".format(self.args.organization))
        if self.args.cname:
            subject.append("/CN={}".format(self.args.cname))
        if self.args.email:
            subject.append("/emailAddress={}".format(self.args.email))
        return "".join(subject)

    def setup(self):
        """Extend the parser configuration in order to expose this command."""
        parser = self._parser.add_parser(
            "management-cert",
            help="Generate a management certificate.")
        parser.add_argument(
            "-c", "--country", default=None,
            help="Country Name (2 letter code)")
        parser.add_argument(
            "-st", "--state", default=None,
            help="State or Province Name (full name)")
        parser.add_argument(
            "-o", "--organization", default="bcbio-nexgen",
            help="Organization Name (eg, company)")
        parser.add_argument(
            "-cn", "--cname", default=None,
            help="Common Name (e.g. server FQDN or YOUR name)")
        parser.add_argument(
            "-e", "--email", default=None,
            help="Email Address")
        parser.add_argument(
            "-f", "--force", default=False, action="store_true",
            help="Overwrite the management certificate if already exits.")

        parser.set_defaults(work=self.run)

    def prologue(self):
        """Executed once before the command running."""
        if not os.path.exists(self._ssh_path):
            LOG.debug("Creating %(ssh_path)s.", {"ssh_path": self._ssh_path})
            os.makedirs(self._ssh_path)
            utils.execute(["chmod", 700, self._ssh_path],
                          cwd=os.path.dirname(self._ssh_path))

        if self.args.force:
            return

        for cert_format in ("managementCert.pem", "managementCert.cer"):
            if os.path.exists(os.path.join(self._ssh_path, cert_format)):
                raise exception.BCBioException("Cerificate already exists.")

    def work(self):
        """Run the command with the received information."""
        LOG.debug("Generating managementCert.pem")
        utils.execute(["openssl", "req", "-x509", "-nodes",
                       "-days", "365",
                       "-newkey", "rsa:2048",
                       "-keyout", "managementCert.pem",
                       "-out", "managementCert.pem",
                       "-subj", self._get_subject()],
                      cwd=self._ssh_path)
        utils.execute(["chmod", 600, "managementCert.pem"],
                      cwd=self._ssh_path)

        LOG.debug("Generating managementCert.cer")
        utils.execute(["openssl", "x509", "-outform", "der",
                       "-in", "managementCert.pem",
                       "-out", "managementCert.cer"],
                      cwd=self._ssh_path)
        utils.execute(["chmod", 600, "managementCert.cer"],
                      cwd=self._ssh_path)

    def task_done(self, result):
        """What to execute after successfully finished processing a task."""
        super(ManagementCertificate, self).task_done(result)
        LOG.info("The management certificate was successfully generated.")

    def task_fail(self, exc):
        """What to do when the program fails processing a task."""
        if not isinstance(exc, exception.BCBioException):
            super(ManagementCertificate, self).task_fail(exc)

        LOG.error("The management certificate already exists. In order to "
                  "overwrite it the --force argument can be used.")


class PrivateKey(base.Command):

    """Create a private key file that matches your management
    certificate.
    """

    def __init__(self, parent, parser):
        super(PrivateKey, self).__init__(parent, parser)
        self._ssh_path = os.path.join(os.path.expanduser("~"), ".ssh")

    def setup(self):
        """Extend the parser configuration in order to expose this command."""
        parser = self._parser.add_parser(
            "pkey",
            help="Create a private key file that matches the management cert.")
        parser.add_argument(
            "--cert", default="managementCert.pem",
            help=("The management certificate name. "
                  "[default: managementCert.pem]"))
        parser.add_argument(
            "-f", "--force", default=False, action="store_true",
            help="Overwrite the management certificate if already exits.")

        parser.set_defaults(work=self.run)

    def prologue(self):
        """Executed once before the command running."""
        if self.args.force:
            return

        if not os.path.exists(os.path.join(self._ssh_path, self.args.cert)):
            raise exception.NotFound("Invalid certificate name.")

        if os.path.exists(os.path.join(self._ssh_path, "managementCert.key")):
            raise exception.BCBioException("The private key already exists.")

    def work(self):
        """Run the command with the received information."""
        LOG.debug("Generating the managementCert.key.")
        utils.execute(["openssl", "rsa",
                       "-in", self.args.cert,
                       "-out", "managementCert.key"],
                      cwd=self._ssh_path)
        utils.execute(["chmod", 600, "managementCert.key"],
                      cwd=self._ssh_path)

    def task_done(self, result):
        """What to execute after successfully finished processing a task."""
        super(PrivateKey, self).task_done(result)
        LOG.info("The private key was successfully generated.")

    def task_fail(self, exc):
        """What to do when the program fails processing a task."""
        if isinstance(exc, exception.NotFound):
            LOG.error("The certificate name %(cert)s do not exist in %(ssh)s",
                      {"cert": self.args.cert, "ssh": self._ssh_path})
        elif isinstance(exc, exception.BCBioException):
            LOG.error("The private key already exists. In order to "
                      "overwrite it the --force argument can be used.")
        else:
            super(PrivateKey, self).task_fail(exc)
