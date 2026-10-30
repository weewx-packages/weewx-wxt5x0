# installer for wxt5x0 driver
# Modified 2026-10-30 by weewx-packages: release 0.9.2.
# Modified 2026-10-22 by weewx-packages.
# Copyright 2017-2024 Matthew Wall
# Distributed under terms of the GPLv3

from weecfg.extension import ExtensionInstaller

def loader():
    return WXT5x0Installer()

class WXT5x0Installer(ExtensionInstaller):
    def __init__(self):
        super(WXT5x0Installer, self).__init__(
            version="0.9.2",
            name='wxt5x0',
            description='Collect data from WXT5x0 hardware',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            files=[('bin/user', ['bin/user/wxt5x0.py'])]
        )
