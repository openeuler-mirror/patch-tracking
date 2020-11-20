"""git type upstream"""
import logging
import os
from datetime import datetime
import git
import git.exc
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
import time
from patch_tracking.api.business import update_tracking
import patch_tracking.util.upstream.upstream as upstream

logger = logging.getLogger(__name__)


def url_to_dir(repo_url):
    """
    url to dir name
    """
    path = repo_url.rstrip(".git")
    path = path.replace("://", "_")
    path = path.replace(":", "_")
    path = path.replace("/", "_")
    return path


def time_stamp_to_utc(time_stamp):
    """time stamp to utc time"""
    time_stamp = int(time_stamp)
    utc_format = '%Y-%m-%dT%H:%M:%SZ'
    utc_time = datetime.utcfromtimestamp(time_stamp)
    utc_time = datetime.strftime(utc_time, utc_format)

    return utc_time


class Git(upstream.Upstream):
    """
    Git type
    """
    def __init__(self, track):
        super().__init__(track)
        self.repo_dir_name = url_to_dir(self.track.scm_repo)
        self.base_path = current_app.config["GIT_BASE_PATH"]

    def git_clone(self):
        """
        git clone
        """
        repo_path = os.path.join(self.base_path, self.repo_dir_name)
        url = self.track.scm_repo
        try:
            logging.info("Cloning repo %s to %s", url, repo_path)
            git.Repo.clone_from(url=url, to_path=repo_path, mirror=True)
            logging.info("Cloned repo done %s.", url)
            return True
        except git.exc.GitError as err:
            logging.error("Clone or fetch repo %s failed. Error: %s", url, err)
            return False

    def git_fetch(self, repo):
        """git fetch"""
        logging.info("Fetching repo %s.", repo)
        if os.path.exists(repo):
            repo = git.Repo(repo)
            count = 10
            while count > 0:
                try:
                    repo.remote().fetch()
                    logging.info("Fetch repo %s finish.", repo)
                    break
                except git.exc.GitError as err:
                    logging.warning("Fetching repo %s failed. Error: %s", repo, err)
                count -= 1
                time.sleep(1)
            if count == 0:
                logging.error("Fetching repo %s failed.", repo)
                return False
        else:
            try:
                self.git_clone()
                logging.info("Cloned repo done %s.", repo)
            except git.exc.GitError as err:
                logging.error("Fetching repo %s failed. Error: %s", repo, err)
                return False
        return True

    def git_latest_sha(self):
        """
        get latest commit id
        """
        repo_path = os.path.join(self.base_path, self.repo_dir_name)
        try:
            repo = git.Repo(repo_path)
            sha = repo.commit(self.track.scm_branch).hexsha
            logging.info(
                "Getting latest commit id of repo: %s branch: %s sha: %s .", repo_path, self.track.scm_branch, sha
            )
            return sha
        except git.exc.GitError as err:
            logging.error(
                "Get latest commit id of repo: %s branch: %s failed. Error: %s", repo_path, self.track.scm_branch, err
            )
            return False

    def get_all_commit_list(self):
        """get all commits of a repo/branch"""
        repo_path = os.path.join(self.base_path, self.repo_dir_name)
        logging.info("Getting all commit id of repo: %s.", repo_path)
        try:
            repo = git.Repo(repo_path)
            repo.git.symbolic_ref("HEAD", "refs/heads/" + self.track.scm_branch)
            all_commit_list = [str(item) for item in repo.iter_commits()]
            logging.info("Get all commit id of repo: %s branch: %s.", repo_path, self.track.scm_branch)
            return all_commit_list
        except git.exc.GitError as err:
            logging.error("Get all commit id of repo: %s failed. Error: %s", repo_path, err)
            return False

    def check_commit_exist(self, commit):
        """check commit exist"""
        repo_path = os.path.join(self.base_path, self.repo_dir_name)
        branch = self.track.scm_branch
        repo = git.Repo(repo_path)
        try:
            ret = repo.git.branch("--contains", commit)
            if ret:
                ret = [r.split(" ")[-1] for r in ret.split("\n")]
                if branch in ret:
                    return True
            return False
        except git.exc.GitCommandError as err:
            logging.error("Error: %s.", err)
            return False

    def get_commit_list(self, start_commit, latest_commit):
        """get commit list"""
        commit_list = list()
        if start_commit == latest_commit:
            return commit_list
        fetch_ret = self.git_fetch(os.path.join(self.base_path, self.repo_dir_name))
        if fetch_ret:
            if not self.check_commit_exist(start_commit):
                logging.error(
                    "Commit sha: %s not exist in repo: %s branch: %s.", start_commit, self.track.scm_repo,
                    self.track.scm_branch
                )
                return commit_list
            all_commit_list = self.get_all_commit_list()
            for commit in all_commit_list:
                if commit != start_commit:
                    commit_list.append(commit)
                else:
                    break
            commit_list.append(start_commit)
        return commit_list

    @staticmethod
    def git_patch(repo, start, end):
        """
        get latest commit id
        """
        logging.info("Getting diff from %s to %s for repo: %s.", start, end, repo)
        try:
            repo = git.Repo(repo)
            hdiff = repo.git.diff(start, end)
            return hdiff
        except git.exc.GitError as err:
            logging.error("Getting diff from %s to %s for repo: %s. Error: %s", start, end, repo, err)
            return False

    def get_commit_info(self, commit_id):
        """
        get commit info
        """
        logging.info("Getting commit info: %s.", commit_id)
        repo = os.path.join(self.base_path, self.repo_dir_name)
        try:
            message = git.Repo(repo).commit(commit_id).message
            date = git.Repo(repo).commit(commit_id).committed_date
            return message, time_stamp_to_utc(date)
        except git.exc.GitError as err:
            logging.error("Getting commit info: %s. Error: %s", commit_id, err)
            return False

    def get_patch_list(self):
        """
        get patch list
        """
        repo = os.path.join(self.base_path, self.repo_dir_name)
        patch_list = list()
        latest_commit = self.git_latest_sha()
        if not latest_commit:
            return None

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

        commit_list = self.get_commit_list(self.track.scm_commit, latest_commit)
        if not commit_list:
            return None

        for i in range(len(commit_list) - 1):
            patch_dict = dict()
            patch_dict['commit_id'] = commit_list[i]
            patch_dict['message'], patch_dict['time'] = self.get_commit_info(commit_list[i])
            patch_ret = self.git_patch(repo, commit_list[i], commit_list[i + 1])
            if patch_ret:
                patch_dict['patch_content'] = patch_ret
            else:
                return None
            patch_list.append(patch_dict)
        patch_list.reverse()

        return patch_list

    def get_scm_patch(self):
        """get scm patch"""
        commit_list = list()
        fetch_ret = self.git_fetch(os.path.join(self.base_path, self.repo_dir_name))
        if fetch_ret:
            commit_list = self.get_patch_list()

        return commit_list

    @staticmethod
    def issue_table(commit_list):
        """issue message"""
        issue_table = "| Commit | Datetime | Message |\n| ------ | ------ | ------ |\n"
        for latest_commit in commit_list:
            latest_commit['message'] = latest_commit['message'].replace("\r", "").replace("\n", "<br>")
            issue_table += '| {} | {} | {} |'.format(
                latest_commit['commit_id'][0:7], latest_commit['time'], latest_commit['message']
            ) + '\n'

        return issue_table
