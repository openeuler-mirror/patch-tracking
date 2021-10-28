#  patch-tracking

# Overview

During the development of the openEuler release version, the latest code of each software package in the upstream community must be updated in a timely manner to fix function bugs and security issues, ensuring that the released openEuler release version is free from defects and vulnerabilities.

This tool manages patches for software packages, proactively monitors the patches submitted by the upstream community, automatically generates patches, automatically submits issues to the corresponding maintainer, and automatically verifies basic patch functions to reduce the verification workload and support quick decision-making of the maintainer.

# Architecture

## C/S Architecture

The patch-tracking uses the C/S architecture.

On the server, patch-tracking executes patch tracking tasks, including maintaining tracking items, identifying branch code changes in the upstream repository and generating patch files, and submitting issues and PRs to Gitee. In addition, patch-tracking provides RESTful interfaces for adding, deleting, modifying, and querying tracking items.

On the client, the command line tool, patch-tracking-cli, invokes the RESTful interface of the patch-tracking to add, delete, modify, and query tracking items.

## Core Processes

- Patch tracking service process

**Procedures:**

1. Write tracking items into the command line tool.
2. Automatically obtains patch files from the upstream repository (for example, GitHub) configured for the tracking item.
3. Create a temporary branch and submit the obtained patch file to the temporary branch.
4. Automatically submit issues to the corresponding project and generate the PR associated with the issues.

![PatchTracking](https://gitee.com/openeuler/patch-tracking/raw/master/images/PatchTracking.jpg)

- Process for the maintainer to handle the submitted patch

**Procedures:**

1. The Maintainer analyzes the patch file in the temporary branch and determines whether to incorporate the patch.
2. Execute the build. After the build is successful, determine whether to incorporate the code into the PR.

![Maintainer](https://gitee.com/openeuler/patch-tracking/raw/master/images/Maintainer.jpg)

## Data Structure

- Tracking table

| No.  | Name            | Note                                                  | Type    | Key     | Empty Allowed |
| ---- | --------------- | ----------------------------------------------------- | ------- | ------- | ------------- |
| 1    | id              | Sequence number of the self-added patch tracking item | int     | -       | No            |
| 2    | version_control | Version control system type of the upstream SCM       | String  | -       | No            |
| 3    | scm_repo        | Upstream SCM warehouse address                        | String  | -       | No            |
| 4    | scm_branch      | Upstream SCM tracking branch                          | String  | -       | No            |
| 5    | scm_commit      | Latest commit ID processed by the upstream code       | String  | -       | Yes           |
| 6    | repo            | Repository address of package source code on Gitee    | String  | Primary | No            |
| 7    | branch          | Repository branch of package source code on Gitee     | String  | Primary | No            |
| 8    | enabled         | Whether to start tracking                             | Boolean | -       | No            |

- Issue table

| No.  | Name   | Note                                               | Type   | Key     | Empty Allowed |
| ---- | ------ | -------------------------------------------------- | ------ | ------- | ------------- |
| 1    | issue  | Issue No.                                          | String | Primary | No            |
| 2    | repo   | Repository address of package source code on Gitee | String | -       | No            |
| 3    | branch | Repository branch of package source code on Gitee  | String | -       | No            |

# Deploying the Tool 

## Downloading the Software

Official release address for mounting the Repo source: <https://repo.openeuler.org/>

Obtain the RPM package from: <https://build.openeuler.org/package/show/openEuler:20.09/patch-tracking>.

## Installing the Tool

#### Method 1: Install from the Repo source

1. Use DNF to mount the repo source (the repo source of 20.09 or later is required. For details, see [Application Development Guide]([openEuler](https://www.openeuler.org/zh/) ) Then run the following commands to download and install patch-tracking and its dependencies:

2. Run the following command to install `patch-tracking`:

   ```
   dnf install patch-tracking
   ```

#### Method 2: Use the RPM package for installation

1. Install related dependencies.

   ```
   dnf install python3-uWSGI python3-flask python3-Flask-SQLAlchemy python3-Flask-APScheduler python3-Flask-HTTPAuth python3-requests python3-pandas git
   ```

2. For example, to install `patch-tracking-1.0.0-1.oe1.noarch.rpm`, run the following command:

   ```
   rpm -ivh patch-tracking-1.0.0-1.oe1.noarch.rpm
   ```

## Generating a Certificate

Run the following command to generate a certificate:

```
openssl req -x509 -days 3650 -subj "/CN=self-signed" \
-nodes -newkey rsa:4096 -keyout self-signed.key -out self-signed.crt
```

Copy the generated `self-signed.key` and `self-signed.crt` files to the **/etc/patch-tracking** directory.

## Configuring Parameters

Set the corresponding parameters in the configuration file in the `/etc/patch-tracking/settings.conf` directory.

1. Configure the service listening address.

   ```
   LISTEN = "127.0.0.1:5001"
   ```

2. GitHub token is used to access the repository information hosted in the upstream open-source software repository of GitHub. For details about how to generate a GitHub token, see [Creating a personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

   ```
   GITHUB_ACCESS_TOKEN = ""
   ```

3. For a warehouse that is hosted on Gitee and needs to be tracked, configure a Gitee token with the warehouse permission to submit patch files, issues, and PRs.

   ```
   GITEE_ACCESS_TOKEN = ""
   ```

4. Scans the database for new or modified tracking items periodically and obtains upstream patches for the scanning items. The time interval is in second.

   ```
   SCAN_DB_INTERVAL = 3600
   ```

5. When the command line tool is running, you need to enter the user name and password hash value for authentication for the POST interface.

   ```
   USER = "admin"
   
   PASSWORD = ""
   ```

> The default value of `USER` is `admin`.

Run the following command to obtain the hash value of the password. Test@123 is the configured password.

```
[root]# generate_password Test@123
pbkdf2:sha256:150000$w38eLeRm$ebb5069ba3b4dda39a698bd1d9d7f5f848af3bd93b11e0cde2b28e9e34bfbbae
```

> The password must meet the following complexity requirements:
>
> - Contains at least six characters.
> - The password must contain uppercase letters, lowercase letters, digits, and special characters (~!@# %^*-_=+).

Add the password hash value `pbkdf2:sha256:150000$w38eLeRm$ebb5069ba3b4dda39a698bd1d9d7f5f848af3bd93b11e0cde2b28e9e34bfbbae` to the quotation marks (" ") of PASSWORD = " ".

## Starting the Patch Tracking Service

You can start the service in either of the following ways:

- The systemd mode is used.

  ```
  systemctl start patch-tracking
  ```

- Run the executable program directly.

  ```
  /usr/bin/patch-tracking
  ```

# Using the Tool

## Adding a Tracking Item

Associate the software repository and branch to be tracked with the upstream open-source software repository and branch in any of the following ways:

### Adding Through the CLI

Parameter description:

> --user: User name to be authenticated for the POST interface. The value is the same as that of USER in settings.conf.
> --password: The password that needs to be authenticated for the POST interface. It is the actual password string corresponding to the PASSWORD hash value in settings.conf.
> --server: URL for starting the patch tracking service, for example, 127.0.0.1:5001.
> --version_control: Control tool of the upstream repository version. The github and git formats are supported.
> --repo: URL of the repository to be tracked. URLs that can be cloned only after the SSH key pair is configured are not supported.
> --branch: Branch name of the repository to be tracked.
> --scm_repo: Name of the traced upstream repository. --If the version_control is in the github format: organization/repository. --If the version_control is in the git format: repository URL. URLs that can be cloned only after the SSH key public/private key pair is configured are not supported.
> --scm_branch: Branch of the upstream warehouse that is tracked.
> --scm_commit: Specifies the start commit of the tracking. This parameter is optional. By default, the tracking starts from the latest commit.
> --enabled: Indicates whether to automatically track the warehouse.

For example:

```
patch-tracking-cli add --server 127.0.0.1:5001 --user admin --password Test@123 --version_control github --repo https://gitee.com/testPatchTrack/testPatch1 --branch master --scm_repo BJMX/testPatch01 --scm_branch test  --scm_commit <COMMIT_SHA> --enabled true
```

### Adding a Specified File

Parameter description:

> --server: URL for starting the patch tracking service, for example, 127.0.0.1:5001.
> --user: User name to be authenticated for the POST interface. The value is the same as that of USER in settings.conf.
> --password: Indicates the password that needs to be authenticated for the POST interface. It is the actual password string corresponding to the PASSWORD hash value in settings.conf.
> --file: YAML file path

Write the information about the repository, branch, version management tool, and whether to enable monitoring to the YAML file (for example, tracking.yaml). The file path is used as the input parameter invoking command of `--file`.

For example:

```
patch-tracking-cli add --server 127.0.0.1:5001 --user admin --password Test@123 --file tracking.yaml
```

The content format of the YAML file is as follows. The content on the left of the colon (:) cannot be modified, and the content on the right of the colon (:) needs to be set based on the site requirements.

```
version_control: github
scm_repo: <SCM_REPO>
scm_branch: master
repo: <URL>
branch: master
enabled: true
```

> version_control: Control tool of the upstream repository version. Only github format is supported.
> scm_repo: Indicates the name of the tracked upstream repository. For github format: organization/repository; for git format: repository URL. The URL that can be cloned only after the SSH key pair is configured is not supported.
> scm_branch: Branch of the upstream warehouse that is tracked.
> repo: URL of the repository to be tracked. URLs that can be cloned only after the SSH key pair is configured are not supported.
> branch: Branch name of the repository to be tracked.
> enabled: Indicates whether to automatically track the warehouse.

If the start commit is specified, a new line is added to the YAML file.

```
scm_commit: <commit sha>
```

> scm_commit: Indicates the start commit of a specified repository or branch to be tracked.

### Adding a Specified Directory

Place multiple `xxx.yaml` files in a specified directory, for example, `test_yaml`. Run the following command to record the tracking items of all YAML files in the specified directory:

Parameter description:

> --user: User name to be authenticated for the POST interface. The value is the same as that of USER in settings.conf.
> --password: Indicates the password that needs to be authenticated for the POST interface. It is the actual password string corresponding to the PASSWORD hash value in settings.conf.
> --server: URL for starting the patch tracking service, for example, 127.0.0.1:5001.
> --dir: path for storing the YAML file.

```
patch-tracking-cli add --server 127.0.0.1:5001 --user admin --password Test@123 --dir /home/Work/test_yaml/
```

## Querying Tracing Items

Parameter description:

> --server: Specifies the URL for starting the patch tracking service, for example, 127.0.0.1:5001. This parameter is mandatory.
> --table: Specifies the table to be queried. This parameter is mandatory.
> --repo: Specifies the repo to be queried. This parameter is optional. If this parameter is not specified, all repo information in the table is queried.
> --branch: Specifies the branch to be queried. This parameter is optional.

```
patch-tracking-cli query --server <LISTEN> --table tracking
```

For example:

```
patch-tracking-cli query --server 127.0.0.1:5001 --table tracking
```

## Querying the Generated Issues

```
patch-tracking-cli query --server <LISTEN> --table issue
```

For example:

```
patch-tracking-cli query --server 127.0.0.1:5001 --table issue
```

## Deleting a Tracking Item

```
patch-tracking-cli delete --server SERVER --user USER --password PWD --repo REPO [--branch BRANCH]
```

For example:

```
patch-tracking-cli delete --server 127.0.0.1:5001 --user admin --password Test@123 --repo https://gitee.com/testPatchTrack/testPatch1 --branch master
```

> You can delete a single piece of data of a specified repo and branch, or delete data of all branches in a specified repo.

## Viewing Issues and PRs on the Code Cloud

Log in to the Gitee and track the software project. On the Issues and Pull Requests tab pages of the project, you can view the item named `[patch tracking] TIME`, for example, ` [patch tracking] 20200713101548`. This item is the issue and PR of the patch file that is generated.

# FAQ

- Failed to access the `api.github.com` Connection refused.

During the running of the patch-tracking service, the error `September 21 22:00:10 localhost.localdomain patch-tracking[36358]: 2020-09-21 22:00:10,812 - patch_tracking.util.github_api - WARNING - HTTPSConnectionPool(host='api.github.com', port=443): Max retries exceeded with url: /user (Caused by NewConnectionError('<urllib3.connection.HTTPSConnection object at 0xfffe19d35820>: Failed to establish a new connection: [Errno 111] Connection refused'))` may be reported. The is because the network access between the patch-tracking service and the GitHub API service is unstable. Ensure that the network between the and GitHub API service is stable (for example, in the Hong Kong region of HUAWEI CLOUD).