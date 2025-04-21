from flask import Flask, render_template, url_for, redirect, request, send_from_directory, jsonify, session, Response, g, send_file, abort
from flask_sqlalchemy import SQLAlchemy
import html
import time
import string
import os
import datetime
import json
import random

import io

from contextlib import *
import traceback

import uuid
from sqlalchemy import text
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.attributes import flag_modified

from flask_socketio import SocketIO, send, join_room, leave_room, emit


import hashlib
from base64 import b64encode
from os import urandom

from PIL import Image, ImageDraw, ImageFont

import base64


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/boards'


app.secret_key = os.environ.get('SECRET_KEY', 'fallback-insecure-key')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-insecure-key')





# Set up app context globally using Flask's `before_request` hook
@app.before_request
def before_request():
    g.db = db.session  # Access the database session globally via `g`

@app.after_request
def after_request(response):
    db.session.remove()  # Clean up the database session after each request
    return response



@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response



#                 _        _
#  ___  ___   ___| | _____| |_
# / __|/ _ \ / __| |/ / _ \ __|
# \__ \ (_) | (__|   <  __/ |_
# |___/\___/ \___|_|\_\___|\__|







# socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")
socketio = SocketIO(app, logger=True, engineio_logger=True)




@socketio.on('join')
def handle_join(data):
    room = data['board_id']
    join_room(room)
    emit('update', room=room)





 #  _   _      _                     
 # | | | | ___| |_ __   ___ _ __ ___ 
 # | |_| |/ _ \ | '_ \ / _ \ '__/ __|
 # |  _  |  __/ | |_) |  __/ |  \__ \
 # |_| |_|\___|_| .__/ \___|_|  |___/
 #              |_|                  



ICON_SIZE = 128


def SHA1(string):
    return hashlib.sha1(string.encode()).hexdigest()

def get_salt(n):
    return b64encode(urandom(n)).decode('utf-8')



def generate_default_avatar(username):
    # Generate a background color from username
    color = '#' + hashlib.md5(username.encode()).hexdigest()[:6]

    # Create image
    img = Image.new('RGB', (ICON_SIZE, ICON_SIZE), color)
    draw = ImageDraw.Draw(img)

    # Get initials
    initials = ''.join([w[0] for w in username.split()[:2]]).upper()

    font = ImageFont.load_default(ICON_SIZE / 2)

    draw.text((ICON_SIZE / 2, ICON_SIZE / 2), initials, fill='white', font=font, anchor='mm')

    return img

def resize_image(image_file):
    # Open the image file
    img = Image.open(image_file)

    # Resize the image
    img = img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)

    return img


def img_to_bytes(img):
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


def get_blank_image():
    return Image.new("RGBA", (1, 1), (0, 0, 0, 0))



#  ____            _             _
# |  _ \    __ _  | |_    __ _  | |__     __ _   ___    ___
# | | | |  / _` | | __|  / _` | | '_ \   / _` | / __|  / _ \
# | |_| | | (_| | | |_  | (_| | | |_) | | (_| | \__ \ |  __/
# |____/   \__,_|  \__|  \__,_| |_.__/   \__,_| |___/  \___|




db = SQLAlchemy(app)


# Association Tables
board_user = db.Table('board_user',
    db.Column('board_id', UUID(as_uuid=True), db.ForeignKey('boards.board_id'), primary_key=True),
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.user_id'), primary_key=True)
)

user_joined_boards = db.Table(
    'user_joined_boards',
    db.Column('user_id', db.ForeignKey('users.user_id'), primary_key=True),
    db.Column('board_id', db.ForeignKey('boards.board_id'), primary_key=True)
)



class ImageFile(db.Model):
    __tablename__ = "images"
    image_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    owner = relationship("User", back_populates="images", foreign_keys=[owner_id])
    image_bytes = db.Column(db.LargeBinary)

    def __init__(self, owner, image):
        self.owner = owner
        self.image_bytes = img_to_bytes(image)
        db.session.commit()

    def get_url(self):
        return '/image/' + str(self.image_id)
    




class Board(db.Model):
    __tablename__ = "boards"
    board_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.Text)
    current_users = db.relationship('User', secondary='board_user', backref=db.backref('boards', lazy=True), lazy='dynamic')
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    owner = relationship("User", back_populates="boards_owned", foreign_keys=[owner_id])
    grid_data = db.Column(MutableList.as_mutable(JSON), nullable=False)
    maps = db.Column(JSON, nullable=True)  # Store a list of JSON objects here
    members = db.relationship(
        "User",
        secondary=user_joined_boards,
        back_populates="joined_boards"
    )

    def __init__(self, name, owner):
        self.name = name
        self.owner = owner
        self.current_users = []
        self.grid_data = [[None] * 5 for _ in range(5)]
        self.maps = []
        self.members = []
        self.add_map(get_blank_image(), name='blank', editable=False)

    def add_user(self, user):
        if user not in self.current_users:
            self.current_users.append(user)
            db.session.commit()
        return None

    def remove_user(self, user):
        if user in self.current_users:
            self.current_users.remove(user)
            db.session.commit()
        return None

    # def set_grid_data(self, data):
    #     self.grid_data = data
    #     db.session.commit()

    def set_square(self, square, grid_data):
        changes = []
        if grid_data is not None and grid_data['type'] == 'avatar':
            for r in range(len(self.grid_data)):
                for c in range(len(self.grid_data[r])):
                    if self.grid_data[r][c] is not None:
                        if self.grid_data[r][c]['type'] == 'avatar' and self.grid_data[r][c]['id'] == grid_data['id']:
                            self.grid_data[r][c] = None
                            changes.append([{'r':r,'c':c}, None])
        self.grid_data[square['r']][square['c']] = grid_data
        changes.append([square, grid_data])
        flag_modified(self, "grid_data")
        
        db.session.commit()
        return changes
        

    def get_square(self, square):
        return self.grid_data[square['r']][square['c']]

    
    def add_map(self, image, name=None, editable=True):
        image_file = ImageFile(owner=self.owner, image=image)
        db.session.add(image_file)
        db.session.commit()
        self.maps.append({
            'image_id': str(image_file.image_id),
            'visible': True,
            'name': name if name is not None else self.name,
            'editable': editable
        })
        flag_modified(self, "maps")
        db.session.commit()

    
    def get_visible_map(self):
        for map in self.maps:
            if map['visible'] and map['editable']:
                return get_Image(map['image_id'])
        return get_Image(self.maps[0]['image_id'])

    def set_name(self, name):
        self.name = name
        db.session.commit()

    def toggle_map_visibility(self, image_id):
        print(self.maps)
        for i in range(len(self.maps)):
            if self.maps[i]['image_id'] == image_id:
                self.maps[i]['visible'] = not self.maps[i]['visible']
        flag_modified(self, 'maps')
        db.session.commit()

    def reset(self):
        for i in range(len(self.grid_data)):
            for j in range(len(self.grid_data[0])):
                self.grid_data[i][j] = None
        flag_modified(self, "grid_data")
        db.session.commit()

    def change_num_squares(self, axis, new_size):
        if axis not in ('x', 'y'):
            raise ValueError("Axis must be 'x' or 'y'")
        
        num_cols = len(self.grid_data[0])
        num_rows = len(self.grid_data)

        if axis == 'x':
            amount = new_size - num_cols

            for row in self.grid_data:
                if amount > 0:
                    row.extend([None] * amount)
                elif amount < 0:
                    del row[new_size:]

        elif axis == 'y':
            amount = new_size - num_rows

            if amount > 0:
                for _ in range(amount):
                    self.grid_data.append([None for _ in range(num_cols)])
            elif amount < 0:
                self.grid_data = self.grid_data[:new_size]

        flag_modified(self, 'grid_data')
        db.session.commit()

    def reorder_maps(self, order):
        # keep blank map first
        self.maps = sorted(self.maps, key = lambda x: order.index(x['image_id']) if x['image_id'] in order else -1)
        flag_modified(self, 'maps')
        db.session.commit()

    def delete_map(self, image_id):
        for map in self.maps:
            if map['image_id'] == image_id:
                self.maps.remove(map)
        flag_modified(self, 'maps')
        db.session.commit()

    def __repr__(self):
        return f'<name: {self.name}, owner: {self.owner.username}>'


class Token(db.Model):
    __tablename__ = "tokens"
    token_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.Text)
    image_id = db.Column(UUID(as_uuid=True), db.ForeignKey('images.image_id'), nullable=False)
    image = relationship("ImageFile", foreign_keys=[image_id])
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    owner = relationship("User", back_populates="tokens", foreign_keys=[owner_id])
    key = db.Column(db.Text)
    size = db.Column(db.Integer, default=1)

    def __init__(self, name, image, owner):
        self.name = name
        self.owner = owner
        self.size = 1
        self.set_image(image)

    def rename(self, name):
        self.name = name
        db.session.commit()

    def set_image(self, image):
        image_file = ImageFile(owner=self.owner, image=resize_image(image))
        db.session.add(image_file)
        db.session.commit()
        self.image_id = image_file.image_id

        db.session.commit()

    def set_key(self, key):
        self.key = key
        db.session.commit()

    def set_size(self, size):
        self.size = size
        db.session.commit()

    def get_url(self):
        return '/token/' + str(self.token_id)

    def export(self):
        return {'name': self.name, 'size': self.size, 'key': self.key}

class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.Text)
    salt = db.Column(db.Text)
    hashed_password = db.Column(db.Text)

    avatar_id = db.Column(UUID(as_uuid=True), db.ForeignKey('images.image_id'), nullable=True)
    avatar = relationship("ImageFile", foreign_keys=[avatar_id])
    
    boards_owned = db.relationship("Board", back_populates="owner", lazy='dynamic', foreign_keys=[Board.owner_id])
    tokens = db.relationship("Token", back_populates="owner", lazy='dynamic', foreign_keys=[Token.owner_id])
    
    current_board_id = db.Column(UUID(as_uuid=True), db.ForeignKey('boards.board_id'), nullable=True)
    current_board = relationship("Board", foreign_keys=[current_board_id])

    joined_boards = db.relationship("Board", secondary=user_joined_boards, back_populates="members")

    images = db.relationship("ImageFile", back_populates="owner", lazy='dynamic', foreign_keys=[ImageFile.owner_id])


    def __init__(self, username, password):
        self.set_username(username)
        self.set_password(password)
        self.set_avatar()


    def set_password(self, password):
        self.salt = get_salt(8)
        self.hashed_password = SHA1(password + self.salt)
        db.session.commit()

    def set_username(self, username):
        self.username = username
        db.session.commit()

    def set_avatar(self, image=None):
        real_image = None
        if image is None or image.filename == '':
            real_image = generate_default_avatar(self.username)
        else:
            real_image = resize_image(image)
        
        image_file = ImageFile(owner=self, image=real_image)
        db.session.add(image_file)
        db.session.commit()
        self.avatar_id = image_file.image_id
        self.images.append(image_file)

        db.session.commit()


    def validate(self, password):
        return self.hashed_password == SHA1(password + self.salt)

    def create_board(self, name):
        board = Board(name=name, owner=self)
        db.session.add(board)
        db.session.commit()
        # board.add_user(self)
        return board.board_id

    def leave(self):
        self.joined_boards.remove(self.current_board)
        if self.current_board:
            self.current_board.remove_user(self)
            self.current_board = None
        db.session.commit()

    def join(self, board):
        self.current_board_id = board.board_id
        board.add_user(self)
        self.joined_boards.append(board)
        db.session.commit()

    def create_token(self, name, image):
        token = Token(name, image, self)
        db.session.add(token)
        db.session.commit()
        return token
    
    def get_url(self):
        return '/avatar/' + str(self.avatar_id)

    def delete_token(self, token):
        self.tokens.remove(token)
        db.session.commit()


    def __repr__(self):
        return f'<Username: {self.username}, hashed_password: {self.hashed_password}>'


    

def get_Image(image_id):
    return db.session.get(ImageFile, image_id)

def get_User(username):
    return User.query.filter_by(username=username).first()

def get_Token(token_id):
    return db.session.get(Token, token_id)


def get_Board(board_id):
    return db.session.get(Board, board_id)





@app.route('/image/<uuid:image_id>')
def image(image_id):
    image = ImageFile.query.get_or_404(image_id)
    return send_file(
        io.BytesIO(image.image_bytes),
        mimetype='image/png'
    )


@app.route('/avatar/<uuid:user_id>')
def avatar(user_id):
    user = User.query.get_or_404(user_id)
    return image(user.avatar_id)
    # return redirect(user.avatar.get_url())


@app.route('/token/<uuid:token_id>')
def token(token_id):
    token = Token.query.get_or_404(token_id)
    return image(token.image_id)
    # return redirect(token.image.get_url())

@app.route('/map/<uuid:board_id>')
def map(board_id):
    board = Board.query.get_or_404(board_id)
    return image(board.get_visible_map().image_id)
    # return redirect(board.get_visible_map().get_url())






#  _   _                                        _    _                 _      
# | | | | ___   ___  _ __      _ __ ___    ___ | |_ | |__    ___    __| | ___ 
# | | | |/ __| / _ \| '__|    | '_ ` _ \  / _ \| __|| '_ \  / _ \  / _` |/ __|
# | |_| |\__ \|  __/| |       | | | | | ||  __/| |_ | | | || (_) || (_| |\__ \
#  \___/ |___/ \___||_|       |_| |_| |_| \___| \__||_| |_| \___/  \__,_||___/
                                                                        




@app.route('/signup', methods=['POST'])
def signup():
    if request.method != 'POST':
        return 'Method not allowed', 405

    if 'username' not in request.form or 'password' not in request.form:
        return 'Insufficient data', 400

    username = request.form['username']
    password = request.form['password']

    if User.query.filter_by(username=username).first():
        return "Username already taken", 400

    new_user = User(username, password)
    db.session.add(new_user)
    db.session.commit()

    session['userid'] = new_user.user_id
    socketio.emit('refresh', room='admin')

    return 'User created successfully', 201



@app.route('/login', methods=['POST'])
def login():
    if request.method != 'POST':
        return 'Method not allowed', 405

    if 'username' not in request.form or 'password' not in request.form:
        return 'Insufficient data', 400

    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if user is None:
        return "No such user exists", 404

    if not user.validate(password):
        return 'Password Incorrect', 401

    session['userid'] = user.user_id

    return 'login successful', 201


@app.route('/logout', methods=["POST"])
def logout():
    session.pop('userid', None)
    return redirect('/')


@app.route('/update_user', methods=['POST'])
def update_user():
    if request.method != 'POST':
        return 'Method not allowed', 405

    # Check for required form data
    if 'userid' not in session:
        return 'You\'re not logged in', 400

    user = db.session.get(User, session['userid'])

    if user is None:
        logout()
        return 'User not found', 404

    # Handle username update
    if 'new_username' in request.form:
        user.set_username(request.form['new_username'])
        socketio.emit('refresh', room='admin')
        return redirect(request.referrer or '/')

    # Handle password update
    if 'new_password' in request.form:
        user.set_password(request.form['new_password'])
        socketio.emit('refresh', room='admin')
        return redirect(request.referrer or '/')

    # Handle avatar update
    if 'avatar' in request.files:
        user.set_avatar(request.files['avatar'])
        for board in user.joined_boards:
            socketio.emit(
                'update icon',
                {'type': 'avatar', 'id': str(user.user_id)},
                room=str(board.board_id)
            )
        socketio.emit('refresh', room='admin')
        
        return redirect(request.referrer or '/')


    return 'No valid data to update', 400



@app.route('/new_board', methods=['POST'])
def new_board():
    if request.method != 'POST':
        return 'Method not allowed', 405

    # Check for required form data
    if 'userid' not in session:
        return 'You\'re not logged in', 400

    user = db.session.get(User, session['userid'])

    if user is None:
        logout()
        return 'User not found', 404

    if 'board_name' not in request.form:
        return 'Insufficient data', 400

    user.create_board(request.form['board_name'])
    socketio.emit('refresh', room='admin')

    return redirect(request.referrer or '/')




@app.route('/join', methods=['POST'])
def join():
    if request.method != 'POST':
        return 'Method not allowed', 405

    # Check for required form data
    if 'userid' not in session:
        return 'You\'re not logged in', 400

    user = db.session.get(User, session['userid'])

    if user is None:
        return logout()
        return 'User not found', 404

    if 'board_id' not in request.form:
        return 'Insufficient data', 400

    board = get_Board(request.form['board_id'])
    user.join(board)

    socketio.emit(
        'user joined',
        {
            'user_id': str(user.user_id),
            'tokens': {str(token.token_id): token.export() for token in user.tokens},
            'name': user.username
        },
        room=str(board.board_id)
    )
    socketio.emit('refresh', room='admin')
    
    return 'OK', 200



# @app.route('/leave', methods=['POST'])
# def leave():
#     if request.method != 'POST':
#         return 'Method not allowed', 405

#     # Check for required form data
#     if 'userid' not in session:
#         return 'You\'re not logged in', 400

#     user = db.session.get(User, session['userid'])

#     if user is None:
#         return logout()
#         # return 'User not found', 404

#     board_id = str(user.current_board.board_id)
#     user.leave()

#     socketio.emit(
#         'user left',
#         {
#             'user_id': str(user.user_id),
#             'tokens': [str(token.token_id) for token in user.tokens]
#         },
#         room=str(board.board_id)
#     )
#     socketio.emit('refresh', room='admin')

#     return redirect('/user')



@app.route('/create_token', methods=['POST'])
def create_token():
    if request.method != 'POST':
        return 'Method not allowed', 405

    # Check for required form data
    if 'userid' not in session:
        return 'You\'re not logged in', 400

    user = db.session.get(User, session['userid'])

    if user is None:
        logout()
        return 'User not found', 404

    token = user.create_token(request.form['name'], request.files['image'])
    
    for board in user.joined_boards:
        socketio.emit(
            'new token',
            {'id': str(token.token_id), 'token': token.export()},
            room=str(board.board_id)
        )
    socketio.emit('refresh', room='admin')

    return redirect(request.referrer or '/')




@app.route('/edit_token', methods=['POST'])
def edit_token():
    if request.method != 'POST':
        return 'Method not allowed', 405

    # Check for required form data
    if 'userid' not in session:
        return 'You\'re not logged in', 400
    
    user = db.session.get(User, session['userid'])

    if user is None:
        return logout()
        # return 'User not found', 404

    if 'token_id' not in request.form:
        return "Insufficient data", 400

    token = get_Token(request.form['token_id'])
    if token is None:
        return 'No token found', 404

    if token.owner_id != user.user_id:
        return 'You don\'t own this token', 405

    if 'action' not in request.form:
        return "Insufficient data", 400

    # try: 
   
    if request.form['action'] == 'rename':
        token.rename(request.form['name'])
        for board in user.joined_boards:
            socketio.emit(
                'update keybindings',
                {
                    'id': str(token.token_id),
                    'token': {'name': token.name, 'size': token.size, 'key': token.key}
                },
                room=str(board.board_id)
            )
    
    if request.form['action'] == 'change_key':
        token.set_key(request.form['key'])
        for board in user.joined_boards:
            socketio.emit(
                'update keybindings',
                {
                    'id': str(token.token_id),
                    'token': {'name': token.name, 'size': token.size, 'key': token.key}
                },
                room=str(board.board_id)
            )

    if request.form['action'] == 'change_size':
        token.set_size(request.form['size'])
        for board in user.joined_boards:
            socketio.emit(
                'update token size',
                 {
                    'id': str(token.token_id),
                    'token': token.export()
                },
                room=str(board.board_id)
            )
    
    if request.form['action'] == 'change_image':
        token.set_image(request.files['image'])
        for board in user.joined_boards:
            socketio.emit(
                'update icon',
                {'type': 'token', 'id': str(token.token_id)},
                room=str(board.board_id))

    if request.form['action'] == 'delete':
        user.delete_token(token)

    socketio.emit('refresh', room='admin')
    return redirect(request.referrer or '/')

    # except:
    #     return 'error', 400










#  ____                          _                       _    _                 _      
# | __ )   ___    __ _  _ __  __| |     _ __ ___    ___ | |_ | |__    ___    __| | ___ 
# |  _ \  / _ \  / _` || '__|/ _` |    | '_ ` _ \  / _ \| __|| '_ \  / _ \  / _` |/ __|
# | |_) || (_) || (_| || |  | (_| |    | | | | | ||  __/| |_ | | | || (_) || (_| |\__ \
# |____/  \___/  \__,_||_|   \__,_|    |_| |_| |_| \___| \__||_| |_| \___/  \__,_||___/
                                                                                    



@app.route('/board_access', methods=['POST'])
def board_access():
    if request.method != 'POST':
        return 'Method not allowed', 405

    # Check for required form data
    if 'userid' not in session:
        return 'You\'re not logged in', 400

    user = db.session.get(User, session['userid'])

    if user is None:
        return logout()

    data = {}

    content_type = request.content_type or ""
    if 'application/json' in content_type:
        data = request.get_json()
    elif 'multipart/form-data' in content_type or 'application/x-www-form-urlencoded' in content_type:
        data = request.form.to_dict()
        if 'image' in request.files:
            data['image'] = request.files['image']
    elif request.method == 'POST':
        try:
            data = request.get_json(force=True) or {}
        except:
            pass


    if 'board_id' not in data:
        return 'insufficient data', 400
    
    if 'board_method' not in data:
        return 'insufficient data', 400
    
    board = get_Board(data['board_id'])


    if data['board_method'] == 'change_name':
        board.set_name(data['name'])
    if data['board_method'] == 'upload_map':
        board.add_map(Image.open(data['image']), data['name'])
        socketio.emit(
            'new map',
            {'map': board.maps[-1]},
            room=str(board.board_id)
        )
    if data['board_method'] == 'toggle_map_visibility':
        board.toggle_map_visibility(data['image_id'])
        socketio.emit(
            'toggle visibility',
            {'image_id': data['image_id']},
            room=str(board.board_id)
        )
    if data['board_method'] == 'reset':
        board.reset()
        socketio.emit(
            'update grid data',
            {'board': board.grid_data},
            room=str(board.board_id)
        )
    if data['board_method'] == 'change_num_squares':
        board.change_num_squares(data['axis'], int(data['num']))
        socketio.emit(
            'update grid data',
            {'board': board.grid_data},
            room=str(board.board_id)
        )
    if data['board_method'] == 'reorder_maps':
        board.reorder_maps(data['order'])
        socketio.emit(
            'rebuild map select',
            {'maps': board.maps},
            room=str(board.board_id)
        )
    if data['board_method'] == 'set_square':
        changes = board.set_square(data['square'], data['content'])
        socketio.emit(
            'update squares',
            {'board': board.grid_data,
             'changes': changes},
            room=str(board.board_id)
        )   
    if data['board_method'] == 'delete_map':
        board.delete_map(data['image_id'])
        socketio.emit(
            'delete map',
            {'image_id': data['image_id']},
            room=str(board.board_id)
        )
   



    socketio.emit('refresh', room='admin')
    return redirect(request.referrer or '/')










#  ____                                _
# |  _ \    __ _    __ _    ___       / \      ___    ___    ___   ___   ___
# | |_) |  / _` |  / _` |  / _ \     / _ \    / __|  / __|  / _ \ / __| / __|
# |  __/  | (_| | | (_| | |  __/    / ___ \  | (__  | (__  |  __/ \__ \ \__ \
# |_|      \__,_|  \__, |  \___|   /_/   \_\  \___|  \___|  \___| |___/ |___/
#                  |___/



@app.route('/')
def index():
    logged_in = 'userid' in session and db.session.get(User, session['userid']) is not None
    username = ''
    if logged_in:
        username = db.session.get(User, session['userid']).username

    return render_template(
        'index.html',
        logged_in=logged_in,
        username=username
    )


@app.route('/user')
def user():
    if 'userid' not in session:
        return redirect('/')

    user = db.session.get(User, session['userid'])
   
    if user is None:
        logout()
        return redirect('/')

    return render_template(
        'user.html',
        user=user
    )


@app.route('/board/<string:board_id>')
def board(board_id):
    try:
        # Check if the board_id is a valid UUID
        uuid_obj = uuid.UUID(board_id)  # This will raise an exception if invalid
    except ValueError:
        # If the UUID is invalid, return 404
        abort(404)

    board = get_Board(board_id)
    if board is None:
        abort(404)

    logged_in = 'userid' in session
    username = ''
    if logged_in:
        user = db.session.get(User, session['userid'])
        if user is None:
            return logout()
        else:
            username = user.username

            if user in board.members:

                icons = {'avatar': {}, 'token': {}}
                for board_user in board.members:
                    for token in board_user.tokens:
                        icons['token'][str(token.token_id)] = token.export()
                    icons['avatar'][str(board_user.user_id)] = {'name': board_user.username}
                return render_template(
                    'board.html',
                    board=board,
                    user=user,
                    num_squares={
                        'x':len(board.grid_data[0]),
                        'y':len(board.grid_data)
                    },
                    icons=icons,
                    maps=board.maps,
                    is_owner=board.owner_id==user.user_id
                )

    return render_template(
        'join.html',
        board=board,
        logged_in=logged_in,
        username=username
    )
    


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', e=e), 404






#     _          _               _                _
#    / \      __| |  _ __ ___   (_)  _ __        / \      ___    ___    ___   ___   ___
#   / _ \    / _` | | '_ ` _ \  | | | '_ \      / _ \    / __|  / __|  / _ \ / __| / __|
#  / ___ \  | (_| | | | | | | | | | | | | |    / ___ \  | (__  | (__  |  __/ \__ \ \__ \
# /_/   \_\  \__,_| |_| |_| |_| |_| |_| |_|   /_/   \_\  \___|  \___|  \___| |___/ |___/


@app.route('/create')
def create():
    os.system("createdb boards")

    # Recreate tables
    db.create_all()

    # Add dummy users
    users = []
    for i in range(1, 4):
        user = User(username=f"test {i}", password=f"test{i}")
        users.append(user)
        db.session.add(user)
    db.session.commit()

    users[0].create_board('board1')

    return redirect('/all')



@app.route('/all')
def all():
    return render_template(
        'all.html',
        s=session,
        images=list(db.session.query(ImageFile)),
        users=sorted(list(db.session.query(User)), key=lambda x: x.username),
        boards=sorted(list(db.session.query(Board)), key=lambda x: x.name),
        tokens=sorted(list(db.session.query(Token)), key=lambda x: x.name)
    )







if __name__ == "__main__":
    app.debug = True
    socketio.run(
        app,
        host='0.0.0.0',
        port=9000,
        use_reloader=True,
        debug=True
    )