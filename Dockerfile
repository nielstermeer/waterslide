FROM ubuntu:16.04

# Make port 9090 available to the world outside this container
EXPOSE 9090
VOLUME /webroot

# Copy requirements.txt here so we don't have to rebuildt the whole image
# when no requirements change
COPY requirements.txt /

# Update and upgrade the base system, after which upgrade and install the python
# requirement, and remove both systems' caches
RUN apt-get update && apt-get install -y -q --no-install-recommends \
	python3 python3-pip python3-dev gcc && \
	\
	pip3 install --upgrade pip setuptools && \	
	pip3 install -r requirements.txt && \
	rm -r /root/.cache /var/lib/apt/lists/*

# Copy the rest of the application over, as not to trigger a
# full rebuild when only the application changes
COPY . /

# Run waterslide when the container launches with some sane defaults
ENTRYPOINT ["/wslide"]
CMD ["manage", \
	# get predictable paths
	"--single", \
	# enable multiplex server, but configure nothing
	"--just-serve", \
	# don't autoslave clients
	"--no-autoslave", \
	# don't serve static files, expect a webserver to do this
	"--disable-static", \
	# serve from the /webroot volume
	"/webroot" ]
