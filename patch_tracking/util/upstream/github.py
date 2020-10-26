"""github upstream"""
import logging
from flask import current_app
from patch_tracking.util.github_api import GitHubApi
from patch_tracking.api.business import update_tracking
from sqlalchemy.exc import SQLAlchemyError
import patch_tracking.util.upstream.upstream as upstream

logger = logging.getLogger(__name__)


class GitHub(upstream.Upstream):
    """
    GitHub type
    """
    def __init__(self, track):
        super().__init__(track)
        self.github_api = GitHubApi()
        self.token = current_app.config['GITHUB_ACCESS_TOKEN']

    def get_latest_commit_id(self):
        """
        get latest commit id
        """
        status, result = self.github_api.get_latest_commit(self.track.scm_repo, self.track.scm_branch)
        logger.debug(
            'repo: %s branch: %s. get_latest_commit: %s %s', self.track.scm_repo, self.track.scm_branch, status, result
        )

        return status, result

    def get_commit_info(self, commit_id):
        """
        get commit info
        """
        status, result = self.github_api.get_commit_info(self.track.scm_repo, commit_id)
        logger.debug('get_commit_info: %s %s', status, result)

        return status, result

    def get_patch_list(self):
        """
        get patch list
        """
        commit_list = list()
        status, result = self.get_latest_commit_id()
        if status != 'success':
            logger.error(
                '[Patch Tracking] Fail to get latest commit id of scm_repo: %s scm_branch: %s. Return val: %s',
                self.track.scm_repo, self.track.scm_branch, result
            )
            return None
        latest_commit = result['latest_commit']
        if not self.track.scm_commit:
            data = {
                'version_control': self.track.version_control,
                'repo': self.track.repo,
                'branch': self.track.branch,
                'enabled': self.track.enabled,
                'scm_commit': latest_commit,
                'scm_branch': self.track.scm_branch,
                'scm_repo': self.track.scm_repo
            }
            try:
                update_tracking(data)
            except SQLAlchemyError as err:
                logger.error(
                    '[Patch Tracking update empty commit id] Fail to update tracking: %s. Result: %s', data, err
                )
            return None

        while self.track.scm_commit != latest_commit:
            status, result = self.get_commit_info(latest_commit)
            logger.debug('get_commit_info: %s %s', status, result)
            if status == 'success':
                if 'parent' in result:
                    ret = self.github_api.get_patch(self.track.scm_repo, latest_commit, latest_commit)
                    logger.debug('get patch api ret: %s', ret)
                    if ret['status'] == 'success':
                        result['patch_content'] = ret['api_ret']
                        # inverted insert commit_list
                        commit_list.insert(0, result)
                    else:
                        logger.error(
                            'Get scm: %s commit: %s patch failed. Result: %s', self.track.scm_repo, latest_commit,
                            result
                        )
                    latest_commit = result['parent']
                else:
                    logger.info(
                        '[Patch Tracking] Successful get scm commit from %s to %s ID/message/time/patch.',
                        self.track.scm_commit, latest_commit
                    )
                    break
            else:
                logger.error(
                    '[Patch Tracking] Get scm: %s commit: %s ID/message/time failed. Result: %s', self.track.scm_repo,
                    latest_commit, result
                )

        return commit_list

    def get_scm_patch(self):
        """get scm patch"""
        commit_list = self.get_patch_list()
        return commit_list

    def issue_table(self, commit_list):
        """issue message"""
        issue_table = "| Commit | Datetime | Message |\n| ------ | ------ | ------ |\n"
        for latest_commit in commit_list:
            scm_commit_url = '/'.join(['https://github.com', self.track.scm_repo, 'commit', latest_commit['commit_id']])
            latest_commit['message'] = latest_commit['message'].replace("\r", "").replace("\n", "<br>")
            issue_table += '| [{}]({}) | {} | {} |'.format(
                latest_commit['commit_id'][0:7], scm_commit_url, latest_commit['time'], latest_commit['message']
            ) + '\n'

        return issue_table
