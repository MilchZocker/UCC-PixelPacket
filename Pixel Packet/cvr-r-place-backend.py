from flask import Flask, request, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image
import cv2
import os
import logging
import hashlib
from time import time, gmtime, strftime

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

DATA_DIR = 'data/'
BACKUPS_DIR = 'backups/'
IMAGE_PATH = 'canvas.png'
VIDEO_PATH = 'canvas.mp4'
TIMELAPSE_VIDEO_PATH = 'timelapse.mp4'

IMAGE_SIZE = 64

# a value of < 1 disables the cooldown
PIXEL_PLACEMENT_COOLDOWN_IN_SECONDS = 30

def hex_to_rgb(hex):
  rgb = tuple(int(c1 + c2, 16) for c1, c2 in zip(hex[::2], hex[1::2]))
  if len(rgb) == 3 and not any(c < 0 or c > 255 for c in rgb):
    return rgb

def parse_instruction(instruction):
  mode = instruction[0]
  params = instruction[1:]
  if mode == 'p':
    index = int(params)
    if 0 <= index and index < IMAGE_SIZE * IMAGE_SIZE:
      col = index % IMAGE_SIZE
      row = index // IMAGE_SIZE
      return ('p', (col, row))
  elif mode == 'c':
    rgb = hex_to_rgb(params)
    if rgb is not None:
      return ('c', rgb)
    
  return (None, None)

def get_user_data_path(ip_hash):
  return f"{DATA_DIR}{ip_hash}.txt"

def get_pixel_colour_and_age(ip_hash):
  path = get_user_data_path(ip_hash)
  if not os.path.exists(path):
    # defaults to 0 seconds since epoch (which doesn't really make sense, but should always allow for placement)
    return ((0, 0, 0), 0)
  
  with open(path, "r", encoding="utf-8") as f:
    data = f.read().split(';')
    return (tuple(int(i) for i in data[0].split(',')), float(data[1]) if 1 < len(data) else 0)
  
def set_pixel_data(ip_hash, **kwargs):
  colour, age = get_pixel_colour_and_age(ip_hash)
  if 'colour' in kwargs:
    colour = kwargs['colour']
  if 'age' in kwargs:
    age = kwargs['age']

  with open(get_user_data_path(ip_hash), "w+", encoding="utf-8") as f:
    f.write(f"{','.join(str(i) for i in colour)};{age}")

def create_video():
  video_size = IMAGE_SIZE * 4
  video = cv2.VideoWriter(VIDEO_PATH, cv2.VideoWriter_fourcc(*'mp4v'), 1, (video_size, video_size))
  image = cv2.imread(IMAGE_PATH)
  image = cv2.resize(image, (video_size, video_size), interpolation = cv2.INTER_NEAREST)
  video.write(image)

  cv2.destroyAllWindows()
  video.release()

def create_timelapse_video():
  video_size = IMAGE_SIZE * 4
  video = cv2.VideoWriter(TIMELAPSE_VIDEO_PATH, cv2.VideoWriter_fourcc(*'mp4v'), 4, (video_size, video_size))
  
  paths = os.listdir(BACKUPS_DIR)
  paths.sort()
  for path in paths:
    image = cv2.imread(os.path.join(BACKUPS_DIR, path))
    image = cv2.resize(image, (video_size, video_size), interpolation = cv2.INTER_NEAREST)
    video.write(image)

  cv2.destroyAllWindows()
  video.release()

def can_place_pixel(pixel_age):
  time_since_pixel = time() - pixel_age
  return PIXEL_PLACEMENT_COOLDOWN_IN_SECONDS < time_since_pixel

@app.route('/place/<instruction>')
def video(instruction):
  ip_hash = hashlib.md5(request.remote_addr.encode('utf-8')).hexdigest()

  mode, data = parse_instruction(instruction)
  if data is None:
    return send_file(VIDEO_PATH, mimetype='video/mp4')
  
  if mode == 'c':
    set_pixel_data(ip_hash, colour = data)
  elif mode == 'p':
    colour, age = get_pixel_colour_and_age(ip_hash)
    if not can_place_pixel(age):
      return send_file(VIDEO_PATH, mimetype='video/mp4')
    
    image = Image.open(IMAGE_PATH)
    # If the pixel is the same it was, it was likely a misinput and we should probably not accept it as a valid placement
    if image.getpixel(data) == colour:
      return send_file(VIDEO_PATH, mimetype='video/mp4')
    
    image.putpixel(data, colour)
    image.save(IMAGE_PATH)
    image.save(os.path.join(BACKUPS_DIR, f'{strftime("%Y-%m-%d_%H-%M-%S", gmtime())}.png'))

    create_video()
    # For every 10th backup image, create a timelapse (10 was just a nice round number. Any number could do)
    if len([name for name in os.listdir(BACKUPS_DIR)]) % 10 == 0:
      create_timelapse_video()
    set_pixel_data(ip_hash, age = time())

  return send_file(VIDEO_PATH, mimetype='video/mp4')

@app.route('/place')
def get_video():
  return send_file(VIDEO_PATH, mimetype='video/mp4')

if __name__ == "__main__":
  if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
  if not os.path.exists(BACKUPS_DIR):
    os.makedirs(BACKUPS_DIR)
  if not os.path.exists(IMAGE_PATH):
    image = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), "black")
    image.save(IMAGE_PATH)
  if not os.path.exists(VIDEO_PATH):
    create_video()
  create_timelapse_video()
  logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
  app.run(host='0.0.0.0', port=5000)
