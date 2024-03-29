	FROM python:3.13.0a3-bookworm

	# Updating system packages
	RUN apt-get update
	RUN apt-get upgrade -y
	
	# Nessesary for cv2
	RUN apt-get install -y libgl1-mesa-glx

	# Set ENV for Repository extract
	
	RUN mkdir /app
	WORKDIR /pixelpacket
	COPY ["./Pixel Packet/", "./"]

	# Begin setup for Python
	RUN pip install --upgrade pip
	RUN pip install Pillow Flask opencv-python Werkzeug

	# Lauch PixelPacket
	CMD python /pixelpacket/cvr-r-place-backend.py
