# build image

#docker build -f Dockerfile-ubuntu -t $USERNAME/$IMAGE:$version .
#docker image tag $USERNAME/$IMAGE:$version $USERNAME/$IMAGE:latest

docker build -f Dockerfile-alpine -t $USERNAME/$IMAGE:$version-alpine .
docker image tag $USERNAME/$IMAGE:$version-alpine $USERNAME/$IMAGE:latest-alpine


# push it to docker
#docker push $USERNAME/$IMAGE:latest
docker push $USERNAME/$IMAGE:latest-alpine
#docker push $USERNAME/$IMAGE:$version
docker push $USERNAME/$IMAGE:$version-alpine
