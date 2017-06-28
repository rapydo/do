
## Things to do

> to do is to be
> to be is to do
> do be do be do 

---

```bash
rapydo-utils/0.4.5
rapydo-controller/0.3.6
rapydo-http/0.2.8
```

---

- [ ] TASK: close the squash issue
- [ ] TEST: setup.py with setuptools
    - [ ] utils
    - [ ] controller/do
    - [ ] backend/http
- [ ] TEST: invoke as cli base
- [ ] TODO: template and update w/ @cookiecutter
- [ ] BUG: if git is not installed the import from git python lib fails
- [ ] TASK: tutorial (walkthrough) mode [rapydo/issues#12]
- [ ] TASK: PDF with swagger2markdown
- [ ] REFACTOR: checks into a subpackage of classes
- [ ] HOW TO: update environment (git pull, image builds, update requirements?)
- [ ] TEST: eudat re-pull rapydo/core? @ohboy
- [ ] EPOS: test code with mongo
    + squash
- [ ] TODO: evaluate tini: https://hynek.me/articles/docker-signals


---

## Already done

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
