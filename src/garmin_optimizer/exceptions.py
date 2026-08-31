class OptimizerError(Exception):
    """Base user facing error type."""


class AdbNotFoundError(OptimizerError):
    pass


class NoAndroidDeviceError(OptimizerError):
    pass


class AndroidDeviceUnauthorizedError(OptimizerError):
    pass


class MultipleAndroidDevicesError(OptimizerError):
    pass


class AppiumUnavailableError(OptimizerError):
    pass


class UiAutomator2UnavailableError(OptimizerError):
    pass


class AndroidUiResearchDisabledError(OptimizerError):
    pass


class GarminConnectNotFoundError(OptimizerError):
    pass


class GarminConnectNotAuthenticatedError(OptimizerError):
    pass


class GarminDeviceNotFoundError(OptimizerError):
    pass


class NavigationMismatchError(OptimizerError):
    pass


class SettingReadError(OptimizerError):
    pass


class UnsafeWriteError(OptimizerError):
    pass


class WriteVerificationError(OptimizerError):
    pass


class RestoreVerificationError(OptimizerError):
    pass


class AmbiguousWriteError(OptimizerError):
    pass


class JournalWriteError(OptimizerError):
    pass
