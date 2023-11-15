import logging
import sys

from .errors import RR_ConnectionError
from .load_rrlib import rrLib


def server_connect(user_name=None, password=None, askForlogin=False):
    """Return a rrServer :class:`libpyRR39._rrTCP` connection
    
    .. note::
        Only works in your company: uses RR_ROOT enviroment variable.

    A login is required if you have enabled *Auth required for all connections* in *rrConfig* tab **rrLogin**
    Or if you connect via a router (router has to be setup in *rrConfig* as well)

    :param user_name: Name of the user, defaults to `None`
    :type user_name: str, optional

    :param password: user passowrd as set in *rrConfig*, defaults to `None`
    :type password: str, optional

    :param askForlogin: ask to input user_name and password if connection fails, defaults to `False`
    :type askForlogin: bool, optional

    Examples:

    * Anonymous :class:`libpyRR39._rrTCP` connection to Royal Render server

        .. code-block:: python

            import rr_python_utils.connection as rr_connect

            tcp = rr_connect.server_connect()

    * Connect via :class:`libpyRR39._rrTCP` with user name *Mario*. Ask to input a password if needed

        .. code-block:: python

            import rr_python_utils.connection as rr_connect

            tcp = rr_connect.server_connect(user_name="Mario", askForlogin=True)


    * Connect via :class:`libpyRR39._rrTCP` with user name *Mario* and password *mammamia!*

        .. code-block:: python

            import rr_python_utils.connection as rr_connect

            tcp = rr_connect.server_connect(user_name="Mario", password="mammamia!")
    """
    logger = get_logger()
    logger.debug("Collecting server and login info")


    # Or if you connect via a router (router has to be setup in rrConfig as well)
    # Note:  tcp does not keep an open connection to the rrServer.
    # Every command re-connects to the server

    tcp = rrLib._rrTCP("")

    # NOTE: getRRServer_OnPremise() does only work in your company.
    # It uses the RR_ROOT environment installed by rrWorkstationInstaller
    rr_server = tcp.getRRServer_OnPremise()

    if not rr_server:
        logger.error(tcp.errorMessage())

    logger.debug("server_connect:setServer")
    if not tcp.setServer(rr_server, 7773):
        logger.error("Server connection setup error: " + tcp.errorMessage())
        sys.exit()

    logger.debug("server_connect:setLogin")
    if not user_name:
        tcp.setLogin("", "")
    elif not password:
        tcp.setLogin(user_name, "")
    else:
        tcp.setLogin(user_name, password)

    logger.debug("server_connect:connectAndAuthorize")
    if not tcp.connectAndAuthorize():
        logger.warning("connectAndAuthorize failed")
        if askForlogin:
            server_login(tcp, user_name, password)
        else:
            raise RR_ConnectionError(tcp.errorMessage())
    logger.debug("server_connect: done")
    return tcp


def server_login(tcp, user_name=None, password=None):
    """Ask credentials for access to rrServer

    .. note::
        If you set a password, then the rrServer enables its authorization check.
        This means this user HAS TO to exist in RR.\n
        If you are running this script from your local intranet, you probably do not need a password.\n
        Please see rrHelp section Usage/External Connections/Security"""

    import getpass
    if not user_name:
        current_user = getpass.getuser()
        print("Please enter userName ({0}):\n".format(current_user))
        user_name = input("Please enter userName ({0}):\n".format(current_user)) or current_user
    if not password:
        password = getpass.getpass("Please enter the password for the user:")

    tcp.setLogin(user_name, password)
    if not tcp.connectAndAuthorize():
        raise RR_ConnectionError(tcp.errorMessage())


def get_logger():
    return logging.getLogger("rrPy")

