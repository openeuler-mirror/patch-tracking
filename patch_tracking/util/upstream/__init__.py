"""upstream init"""
import patch_tracking.util.upstream.git as git
import patch_tracking.util.upstream.github as github


class Factory(object):
    """
    Factory
    """
    @staticmethod
    def create(track):
        """
        git type
        """
        if track.version_control == 'github':
            return github.GitHub(track)
        if track.version_control == 'git':
            return git.Git(track)
        return None
