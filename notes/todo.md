
## Things to do

> to do is to be
> to be is to do
> do be do be do 
> 
---

### DOING

- [ ] Fix the 'exception_label' in errors (e.g. [B2SAFE])
- [ ] Make the 'mode' more clear in output
- [ ] Can we infer the mode of a running container?
- [ ] TEST: new packaging
    * setup.py with setuptools 
    * remove subpackage of "rapydo.X"
    * add travis and automatic deploy from git tags
    - [x] utilities
    - [ ] controller
    - [ ] restapi
    - [ ] build-templates github release
- [ ] BUG: if git is not installed the import from git python lib fails
- [ ] BUG: network problems with start:
    [link](http://olicallaghan.com/post/a-survival-guide-to-communication-between-docker-containers)
    ```bash
    Client Error: Conflict ("cannot create network  (br-52cc0f455211): conflicts with network  (br-d5c22ead14f6): networks have overlapping IPv4")
    ```
- [ ] TASK: automatic certificate generation
    - [ ] cron on host
    - [ ] three commands: add, check, remove
- [ ] TASK: tutorial (walkthrough) mode [rapydo/issues#12]
- [ ] COOL: aliases and combo
- [ ] REFACTOR: checks into a subpackage of classes
- [ ] HOWTO: update environment (git pull, image builds, update requirements?)
- [ ] TEST: eudat re-pull rapydo/core? @ohboy
- [ ] EPOS: test code with mongo + squash
- [ ] TODO: evaluate tini: https://hynek.me/articles/docker-signals

---

### versions

```bash
rapydo-utils/0.5.0
rapydo-controller/0.5.0
rapydo-http/0.5.0
```

---

### EU

- [ ] SEADATA: testbed
    - [ ] b2safe
        + cineca, csc, dkrz
        + stfc, gr.net
    - [ ] b2stage
    - [ ] proxy to http api
    - [ ] docker registry b2host

---

### sponsor :D

CLI APPS:
- keep
- python-gist
- buku
- tnote


---

### Already done

- [x] fix restclient
- [x] fix tests inside container
- [x] fix restclient bash open
- [x] put @mongo back
- [x] generic operation with 'run' services like sqladmin or swaggerui
- [x] put back gitter things
- [x] auth service selection in yaml?
- [x] some fixes
- [x] time to do @releases: rapydo(utils, controller, http)
- [x] fix Travis
- [x] pull 0.4.1 from Rob?
- [x] SERIOUS BUG: yaml order on dictionary elements
- [x] BUG: services.yaml was not saved
- [x] BUG: swagger dir not saved as recursive
- [x] BUG: rapydo wrong blame. projects_defaults.yaml position
- [x] BUG: uwsgi.ini needs `PROJECT.__main__`
    - rebuild backend image
- [x] EUDAT: release 0.5 + changelog + milestones
    - [x] check with b2access dev
    - [x] check production locally with self signed cert
    - [x] add b2safe dev
    - [x] check with domain and prototype online
- [x] BUG: env variables stripper (detect)
- [x] BUG: PYTHONPATH fix on all modes?
- [x] BUG: compatibility with docker-compose > 1.13
- [x] TASK: close the squash issue
- [x] TASK: fix core backend run
- [x] TEST: invoke as cli base
- [x] TODO: remove COMPOSE_PROJECT_NAME and use --project
- [x] FIX: skip oauth2 if not needed
- [x] TODO: change TOFIX in FIXME (backend)
- [x] TODO: make env at each command (not for check and init)
- [x] TODO: recheck quick_start.sh
