#!/usr/bin/python3
"""
    The MIT License (MIT)

    Copyright (c) 2023 pkjmesra

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

"""

import os
from sys import platform
import getpass
import re
import json
from PKDevTools.classes.Fetcher import fetcher
from PKDevTools.classes.Utils import random_user_agent
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes.Committer import Committer
from PKDevTools.classes import Archiver
from git import Repo
import git

class PKAnalyticsService():
    def collectMetrics(self):
        try:
            userName = self.getUserName()
            metrics = self.getApproxLocationInfo()
            dateTime = str(PKDateUtilities.currentDateTime())
            metrics["dateTime"] = dateTime
            metrics["userName"] = "DummyUser"
            self.tryCommitAnalytics(userDict=metrics)
        except:
            pass

    def getUserName(self):
        username = os.getlogin()
        if username is None or len(username) == 0:
            username = os.environ.get('username') if platform.startswith("win") else os.environ.get("USER")
            if username is None or len(username) == 0:
                username = os.environ.get('USERPROFILE')
                if username is None or len(username) == 0:
                    username = os.path.expandvars("%userprofile%") if platform.startswith("win") else getpass.getuser()
        return username

    def getApproxLocationInfo(self):
        url = 'http://ipinfo.io/json'
        f = fetcher()
        response = f.fetchURL(url=url,timeout=5,headers={'user-agent': f'{random_user_agent()}'})
        data = json.loads(response.text)
        return data
    
    def tryCommitAnalytics(self, userDict={}):
        scanResultFilesPath = os.path.join(Archiver.get_user_outputs_dir(), "users.txt")
        with open(scanResultFilesPath, "a+") as f:
            f.write(str(userDict))
        # repo = Repo(os.path.join(Archiver.get_user_outputs_dir(), "users"))
        # origin = repo.remote()
        # cli = origin.repo.git
        # cli.checkout('origin/master', 'path/to/file')
        repo_clone_url = "git@github.com:pkjmesra/PKUserAnalytics.git"
        local_repo = "PKUserAnalytics"
        test_branch = "main"
        repo = git.Repo.clone_from(repo_clone_url, local_repo)
        repo.git.checkout(test_branch)
        # write to file in working directory
        repo.index.add([scanResultFilesPath])
        commit = repo.index.commit("Commit test")
        Committer.commitTempOutcomes(addPath=scanResultFilesPath,commitMessage="[User-Analytics]")

analytics = PKAnalyticsService()
analytics.collectMetrics()


