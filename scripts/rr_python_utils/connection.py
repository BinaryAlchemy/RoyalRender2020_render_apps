import logging
import sys

from .errors import RR_ConnectionError
from .load_rrlib import rrLib


def server_connect(user_name=None, password=None):
    """Return a rrServer tcp connection
    NOTE: only works in your company: uses RR_ROOT enviroment variable."""
    logger = get_logger()
    logger.info("Collecting server and login info")

    # A login is required if you have enabled 'Auth required for all connections' in rrConfig tab rrLogin
    # Or if you connect via a router (router has to be setup in rrConfig as well)
    # Note:  tcp does not keep an open connection to the rrServer.
    # Every command re-connects to the server

    tcp = rrLib._rrTCP("")

    # NOTE: getRRServer() does only work in your company.
    # It uses the RR_ROOT environment installed by rrWorkstationInstaller
    rr_server = tcp.getRRServer()

    if not rr_server:
        logger.error(tcp.errorMessage())

    if not tcp.setServer(rr_server, 7773):
        logger.error("Server connection setup error: " + tcp.errorMessage())
        sys.exit()

    tcp.setLogin("", "")
    if not tcp.connectAndAuthorize():
        server_login(tcp, user_name, password)

    return tcp


def server_login(tcp, user_name=None, password=None):
    """Ask credentials for access to rrServer

    IMPORTANT:  If you set a password, then the rrServer enables its authorization check.
                This means this user HAS TO to exist in RR.
                If you are running this script from your local intranet, you probably do not need a password.
                Please see rrHelp section Usage/External Connections/Security"""

    import getpass
    if not user_name:
        current_user = getpass.getuser()
        user_name = input("UserName ({0}):\n".format(current_user)) or current_user
    if not password:
        password = getpass.getpass("Password:")

    tcp.setLogin(user_name, password)
    if not tcp.connectAndAuthorize():
        raise RR_ConnectionError(tcp.errorMessage())


def get_logger():
    return logging.getLogger("RR_connect")

def set_logger(level=logging.WARNING):
    logger = get_logger()

    while logger.handlers:  # remove existing handlers to avoid double output
        logger.handlers.pop()

    handler = logging.StreamHandler()
    formatter = logging.Formatter( '%(asctime)s %(name)-12s %(levelname)-8s %(message)s', "%H:%M:%S")

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger
