"""
tracking job
"""
import logging
import base64
import datetime
import time
import random
from sqlalchemy.exc import SQLAlchemyError
from patch_tracking.util.gitee_api import create_branch, upload_patch, create_gitee_issue
from patch_tracking.util.gitee_api import create_pull_request, get_path_content, upload_spec, create_spec
from patch_tracking.database.models import Tracking
from patch_tracking.api.business import update_tracking, create_issue
from patch_tracking.task import scheduler
from patch_tracking.util.spec import Spec
from patch_tracking.util.upstream import Factory

logger = logging.getLogger(__name__)


def upload_patch_to_gitee(track):
    """
    upload a patch file to Gitee
    """
    cur_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    with scheduler.app.app_context():
        logger.info('[Patch Tracking %s] track.scm_commit_id: %s.', cur_time, track.scm_commit)
        git_api = Factory.create(track)
        patch = get_scm_patch(track, git_api)
        if patch:
            issue = create_patch_issue_pr(patch, cur_time, git_api)
            if issue:
                create_issue_db(issue)
            else:
                logger.info('[Patch Tracking %s] No issue need to create.', cur_time)
        else:
            logger.debug('[Patch Tracking %s] No new commit.', cur_time)


def get_scm_patch(track, git_api):
    """
    Traverse the Tracking data table to get the patch file of enabled warehouse.
    Different warehouse has different acquisition methods
    :return:
    """
    scm_dict = dict(
        scm_repo=track.scm_repo,
        scm_branch=track.scm_branch,
        scm_commit=track.scm_commit,
        enabled=track.enabled,
        repo=track.repo,
        branch=track.branch,
        version_control=track.version_control
    )

    commit_list = git_api.get_scm_patch()
    if commit_list:
        scm_dict['commit_list'] = commit_list
        return scm_dict
    logger.info('repo: %s branch: %s. get_latest_commit is None.', scm_dict['scm_repo'], scm_dict['scm_branch'])

    return None


def create_patch_issue_pr(patch, cur_time, git_api):
    """
    Create temporary branches, submit files, and create PR and issue
    :return:
    """
    issue_dict = dict()
    gitee_repo = patch["repo"].replace("https://gitee.com/", "")
    issue_dict['repo'] = patch['repo']
    issue_dict['branch'] = patch['branch']
    new_branch = 'patch-tracking/' + cur_time
    result = create_branch(gitee_repo, patch['branch'], new_branch)
    if result == 'success':
        logger.info('[Patch Tracking %s] Successful create branch: %s', cur_time, new_branch)
    else:
        logger.error('[Patch Tracking %s] Fail to create branch: %s', cur_time, new_branch)
        return None
    patch_lst = list()
    for latest_commit in patch['commit_list']:
        scm_commit_url = '/'.join(['https://github.com', patch['scm_repo'], 'commit', latest_commit['commit_id']])
        latest_commit['message'] = latest_commit['message'].replace("\r", "").replace("\n", "<br>")

        patch_file_content = latest_commit['patch_content']
        post_data = {
            'repo': gitee_repo,
            'branch': new_branch,
            'latest_commit_id': latest_commit['commit_id'],
            'patch_file_content': str(patch_file_content),
            'cur_time': cur_time,
            'commit_url': scm_commit_url
        }
        result = upload_patch(post_data)
        if result == 'success':
            logger.info(
                '[Patch Tracking %s] Successfully upload patch file of commit: %s', cur_time, latest_commit['commit_id']
            )
        else:
            logger.error(
                '[Patch Tracking %s] Fail to upload patch file of commit: %s', cur_time, latest_commit['commit_id']
            )
            return None
        patch_lst.append(str(latest_commit['commit_id']))

    result = upload_spec_to_repo(patch, patch_lst, cur_time)
    if result == "success":
        logger.info('[Patch Tracking %s] Successfully upload spec file.', cur_time)
    else:
        logger.error('[Patch Tracking %s] Fail to upload spec file. Result: %s', cur_time, result)
        return None

    issue_table = git_api.issue_table(patch['commit_list'])
    logger.debug(issue_table)
    result = create_gitee_issue(gitee_repo, patch['branch'], issue_table, cur_time)
    if result[0] == 'success':
        issue_num = result[1]
        logger.info('[Patch Tracking %s] Successfully create issue: %s', cur_time, issue_num)

        retry_count = 10
        while retry_count > 0:
            ret = create_pull_request(gitee_repo, patch['branch'], new_branch, issue_num, cur_time)
            if ret == 'success':
                logger.info('[Patch Tracking %s] Successfully create PR of issue: %s.', cur_time, issue_num)
                break
            logger.warning('[Patch Tracking %s] Fail to create PR of issue: %s. Result: %s', cur_time, issue_num, ret)
            retry_count -= 1
            time.sleep(random.random() * 5)
        if retry_count == 0:
            logger.error('[Patch Tracking %s] Fail to create PR of issue: %s.', cur_time, issue_num)
            return None

        issue_dict['issue'] = issue_num

        data = {
            'version_control': patch['version_control'],
            'repo': patch['repo'],
            'branch': patch['branch'],
            'enabled': patch['enabled'],
            'scm_commit': patch['commit_list'][-1]['commit_id'],
            'scm_branch': patch['scm_branch'],
            'scm_repo': patch['scm_repo']
        }
        try:
            update_tracking(data)
        except SQLAlchemyError as err:
            logger.error('[Patch Tracking %s] Fail to update tracking: %s. Result: %s', cur_time, data, err)
    else:
        logger.error('[Patch Tracking %s] Fail to create issue: %s. Result: %s', cur_time, issue_table, result[1])
        return None

    return issue_dict


def upload_spec_to_repo(patch, patch_lst, cur_time):
    """
    update and upload spec file
    """
    new_branch = 'patch-tracking/' + cur_time
    gitee_repo = patch["repo"].replace("https://gitee.com/", "")
    _, repo_name = gitee_repo.split('/')
    spec_file = repo_name + '.spec'

    patch_file_lst = [patch + '.patch' for patch in patch_lst]

    log_title = "{} patch-tracking".format(datetime.datetime.now().strftime("%a %b %d %Y"))
    log_content = "append patch file of upstream repository from <{}> to <{}>".format(patch_lst[0], patch_lst[-1])

    ret = get_path_content(gitee_repo, patch['branch'], spec_file)
    if 'content' in ret:
        spec_content = str(base64.b64decode(ret['content']), encoding='utf-8')
        spec_sha = ret['sha']
        new_spec = modify_spec(log_title, log_content, patch_file_lst, spec_content)
        result = update_spec_to_repo(gitee_repo, new_branch, cur_time, new_spec, spec_sha)
    else:
        spec_content = ''
        new_spec = modify_spec(log_title, log_content, patch_file_lst, spec_content)
        result = create_spec_to_repo(gitee_repo, new_branch, cur_time, new_spec)

    return result


def modify_spec(log_title, log_content, patch_file_lst, spec_content):
    """
    modify spec file
    """
    spec = Spec(spec_content)
    return spec.update(log_title, log_content, patch_file_lst)


def update_spec_to_repo(repo, branch, cur_time, spec_content, spec_sha):
    """
    update spec file
    """
    ret = upload_spec(repo, branch, cur_time, spec_content, spec_sha)
    if ret == 'success':
        logger.info('[Patch Tracking %s] Successfully update spec file.', cur_time)
    else:
        logger.error('[Patch Tracking %s] Fail to update spec file. Result: %s', cur_time, ret)

    return ret


def create_spec_to_repo(repo, branch, cur_time, spec_content):
    """
    create new spec file
    """
    ret = create_spec(repo, branch, spec_content, cur_time)
    if ret == 'success':
        logger.info('[Patch Tracking %s] Successfully create spec file.', cur_time)
    else:
        logger.error('[Patch Tracking %s] Fail to create spec file. Result: %s', cur_time, ret)

    return ret


def create_issue_db(issue):
    """
    create issue into database
    """
    issue_num = issue['issue']
    tracking = Tracking.query.filter_by(repo=issue['repo'], branch=issue['branch']).first()
    tracking_repo = tracking.repo
    tracking_branch = tracking.branch
    data = {'issue': issue_num, 'repo': tracking_repo, 'branch': tracking_branch}
    logger.debug('issue data: %s', data)
    create_issue(data)
