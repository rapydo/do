
## Testing with alpine python base

DEPRECATED

docker run --rm -it -v (pwd):/tmp/code -w /tmp/code python:3.4-alpine ash

apk update
apk add docker git 

# https://github.com/gliderlabs/docker-alpine/issues/183#issuecomment-257014744
apk add openrc --no-cache

rc-update add docker boot
service docker start
docker ps
pip install ipython

---

## Testing with alpine docker-in-docker base

```bash
docker run --rm --name dind -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v (pwd):/tmp/code -w /tmp/code \
    docker:17.05.0-ce ash

apk update
apk add git python3

# add pip...
# install rapydo-controller

# TRY
```


