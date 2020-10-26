"""abstract class Upstream"""
import abc


class Upstream(abc.ABC):
    """
    Upstream
    """
    def __init__(self, track):
        self.track = track

    @abc.abstractmethod
    def get_patch_list(self):
        """
        Get patch list from upstream
        """
