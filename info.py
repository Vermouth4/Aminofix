__title__ = 'Amino.fix'
__author__ = 'Vermouth'
__license__ = 'MIT'
__copyright__ = 'Copyright 2021-2023 Vermouth'
__version__ = '2.3.6.1'

from rich import print
from rich.console import Console
from rich.panel import Panel
from pyfiglet import Figlet
from requests import get
from json import loads

# Initialize the console
console = Console()

# Create a Figlet font object and render text with a large font
figlet = Figlet(font='big')
name_banner = figlet.renderText("Vermouth")

# Print the banner
console.print(
    Panel.fit(
        name_banner + "\nTelegram: https://t.me/XSromz\nGitHub: @Vermouth1",
        title="Credits",
        border_style="red"
    )
)

# Import local modules
from .client import Client
from .lib.util import exceptions, helpers, objects, headers
from .socket import Callbacks, SocketHandler
