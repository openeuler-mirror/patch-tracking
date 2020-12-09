"""github upstream"""
import logging
import time
import requests
from flask import current_app
from requests import exceptions
from patch_tracking.api.business import update_tracking
from sqlalchemy.exc import SQLAlchemyError
import patch_tracking.util.upstream.upstream as upstream

logger = logging.getLogger(__name__)


def get_user_info(token):
    """
    get user info
    """
    url = "https://api.github.com/user"
    count = 30
    token = 'token ' + token
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Authorization': token,
        'Content-Type': 'application/json',
        'Connection': 'close',
        'method': 'GET',
        'Accept': 'application/json'
    }
    while count > 0:
        try:
            ret = requests.get(url, headers=headers)
            if ret.status_code == 200:
                return True, ret.text
            return False, ret.text
        except exceptions.ConnectionError as err:
            logger.warning(err)
            time.sleep(10)
            count -= 1
            continue
        except UnicodeEncodeError:
            return False, 'github token is bad credentials.'
        except IOError as error:
            return False, error
    if count == 0:
        logger.error('Fail to connnect to github: %s after retry 30 times.', url)
        return False, 'connect error'


class GitHub(upstream.Upstream):
    """
    GitHub type
    """
    def __init__(self, track):
        super().__init__(track)
        _token = 'token ' + current_app.config['GITHUB_ACCESS_TOKEN']
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Authorization': _token,
            'Content-Type': 'application/json',
            'Connection': 'close',
            'method': 'GET',
            'Accept': 'application/json'
        }

    def api_request(self, url, params=None):
        """
        request GitHub API
        """
        logger.debug("Connect url: %s", url)
        count = 30
        while count > 0:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                return response
            except exceptions.ConnectionError as err:
                logger.warning(err)
                time.sleep(10)
                count -= 1
                continue
            except IOError as err:
                logger.error(err)
                return False
        if count == 0:
            logger.error('Fail to connnect to github: %s after retry 30 times.', url)
            return False

    def get_patch(self, repo_url, scm_commit, last_commit):
        """
        get patch
        """
        api_url = 'https://github.com'
        if scm_commit != last_commit:
            commit = scm_commit + '...' + last_commit + '.diff'
        else:
            commit = scm_commit + '^...' + scm_commit + '.diff'
        ret_dict = dict()

        url = '/'.join([api_url, repo_url, 'compare', commit])
        ret = self.api_request(url)
        if ret:
            if ret.status_code == 200:
                patch_content = ret.text
                ret_dict['status'] = 'success'
                ret_dict['api_ret'] = patch_content
            else:
                logger.error('%s failed. Return val: %s', url, ret)
                ret_dict['status'] = 'error'
                ret_dict['api_ret'] = ret.text
        else:
            ret_dict['status'] = 'error'
            ret_dict['api_ret'] = 'fail to connect github by api.'
        return ret_dict

    def get_all_commit_list(self):
        """
        get latest 100 commit
        """
        url = '/'.join(['https://api.github.com/repos', self.track.scm_repo, 'commits'])
        params = {"sha": self.track.scm_branch, "page": 0, "per_page": 100}
        all_commits = list()
        ret = self.api_request(url, params=params)
        for item in ret.json():
            all_commits.append(item)

        logger.debug('[Patch Tracking] Successful get all commits.')
        return all_commits

    def get_latest_commit_id(self):
        """
        get latest commit_ID, commit_message, commit_date
        :return: res_dict
        """
        api_url = 'https://api.github.com/repos'
        url = '/'.join([api_url, self.track.scm_repo, 'branches', self.track.scm_branch])
        ret = self.api_request(url)
        res_dict = dict()
        if ret:
            if ret.status_code == 200:
                res_dict['latest_commit'] = ret.json()['commit']['sha']
                res_dict['message'] = ret.json()['commit']['commit']['message']
                res_dict['time'] = ret.json()['commit']['commit']['committer']['date']
                logger.debug(
                    'repo: %s branch: %s. get_latest_commit: %s %s', self.track.scm_repo, self.track.scm_branch,
                    'success', res_dict
                )
                return 'success', res_dict

            logger.error('%s failed. Return val: %s', url, ret)
            return 'error', ret.json()
        return 'error', 'connect error'

    def get_commit_info(self, repo_url, commit_id):
        """
        get commit info
        """
        res_dict = dict()
        api_url = 'https://api.github.com/repos'
        url = '/'.join([api_url, repo_url, 'commits', commit_id])
        ret = self.api_request(url)
        if ret:
            if ret.status_code == 200:
                res_dict['commit_id'] = commit_id
                res_dict['message'] = ret.json()['commit']['message']
                res_dict['time'] = ret.json()['commit']['author']['date']
                if 'parents' in ret.json() and ret.json()['parents']:
                    res_dict['parent'] = ret.json()['parents'][0]['sha']
                logger.debug('get_commit_info: %s %s', 'success', res_dict)
                return 'success', res_dict

            logger.error('%s failed. Return val: %s', url, ret)
            return 'error', ret.json()
        return 'error', 'connect error'

    def get_patch_list(self):
        """
        get patch list
        """
        all_commits_info = self.get_all_commit_list()
        all_commits = [item["sha"] for item in all_commits_info]

        if self.track.scm_commit not in all_commits:
            logger.error(
                '[Patch Tracking] Scm repo commit : %s not found in latest 100 commits of scm_repo: %s scm_branch: %s.',
                self.track.scm_commit, self.track.scm_repo, self.track.scm_branch
            )
            return None
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
            status, result = self.get_commit_info(self.track.scm_repo, latest_commit)
            logger.debug('get_commit_info: %s %s', status, result)
            if status == 'success':
                if 'parent' in result:
                    ret = self.get_patch(self.track.scm_repo, latest_commit, latest_commit)
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
