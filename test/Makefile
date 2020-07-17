IMAGE=orm-test
CONTAINER=orm-test

default: run

image:
	docker build -t $(IMAGE) .

run: image
	docker run --rm --net=host --env="DISPLAY" \
		--volume="$$HOME/.Xauthority:/root/.Xauthority:rw" \
		--name $(CONTAINER) \
		$(IMAGE)
