class InvalidZipFile(Exception):
    '''
    Exception raised when the file informed it's not a zip file
    '''

    def __init__(self, msg):
        super().__init__(msg)


class PluginNotFound(Exception):
    '''
    Exception raise when the file informed doesn't contain a correct shared library
    Ex.: The user informed a linux plugin on a Windows application.
    '''

    def __init__(self, msg):
        super().__init__(msg)


class InvalidDestinationPath(Exception):
    '''
    Exception raised when the destination path to install the plugin is not one of the paths used
    by HookMan to find plugins already installed
    '''

    def __init__(self, msg):
        super().__init__(msg)


class PluginAlreadyInstalled(Exception):
    '''
    Exception raise when a folder with the same name of the plugin already is placed on the destination folder informed
    '''

    def __init__(self, msg):
        super().__init__(msg)
