	FROM python:3.13.0a3-bookworm

	# Updating system packages
	RUN apt-get update
	RUN apt-get upgrade
	
	# Nessesary for cv2
	RUN apt-get install -y libgl1-mesa-glx

	# Set ENV for Repository extract
	WORKDIR "/debian/Desktop/UCC-PixelPacket/Pixel Packet"
	COPY ["./Pixel Packet/", "./"]

	# Begin setup for Python
	RUN pip install --upgrade pip
	RUN pip install Pillow Flask opencv-python Werkzeug

	# Lauch PixelPacket
	CMD python cvr-r-place-backend.py
