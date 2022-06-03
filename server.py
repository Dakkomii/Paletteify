from crypt import methods
import os
import psycopg2

from flask import Flask, render_template, request, g, redirect, url_for, jsonify, send_file, session
from werkzeug.utils import secure_filename
import io
from math import sqrt

from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv, find_dotenv
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Token
from six.moves.urllib.parse import urlencode

from webcolors import name_to_rgb

import numpy as np

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

app = Flask(__name__)
app.secret_key = "WE ARE THE LEAKS"

oauth = OAuth(app)

AUTHO0_CLIENT_ID = env['auth0_client_id']
AUTHO0_CLIENT_SECRET = env['auth0_client_secret']
AUTHO0_DOMAIN = env['auth0_domain']

def fetch_token(name, request):
    token = OAuth2Token.find(
        name=name,
        user=request.user
    )
    return token.to_token()

auth0 = oauth.register(
    'auth0',
    client_id=AUTHO0_CLIENT_ID,
    client_secret=AUTHO0_CLIENT_SECRET,
    api_base_url='https://'+AUTHO0_DOMAIN,
    access_token_url='https://'+AUTHO0_DOMAIN+'/oauth/token',
    authorize_url='https://'+AUTHO0_DOMAIN+'/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f"https://"+AUTHO0_DOMAIN+"/.well-known" f"/openid-configuration",
    fetch_token=fetch_token,
)


####Database Functions

def connect_db():
    return psycopg2.connect(os.environ.get('DATABASE_URL'), sslmode='require')

def get_db():
    if not hasattr(g,'pg_db'):
        g.pg_db = connect_db()
    return g.pg_db

@app.after_request
def close_db(response):
    if hasattr(g, 'db'):
        app.logger.warn("teardown")
        g.pg_db.close()
    return response

###Auth0 Functions

@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture'],
    }
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO users (profile_id, username, image)
                                   values (%s, %s, %s)
                        ON CONFLICT (profile_id) DO UPDATE SET image=%s""", (userinfo['sub'], userinfo['name'], userinfo['picture'], userinfo['picture']))
    conn.commit()
    cur.close()

    return redirect(url_for('main'))

@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=url_for('callback_handling', _external = True))

#Use this function wrapper to make urls unreachable if client not logged in
def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/')
    return f(*args, **kwargs)

  return decorated

@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('main', _external=True), 'client_id': AUTHO0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('custom_404.html'), 404

@app.errorhandler(405)
def page_not_found(e):
    return render_template('custom_405.html'), 405

@app.route('/')
def main():
    return redirect(url_for('post_gallery'))

##Image Functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg']

@app.route('/image', methods=['POST'])
def upload_post():
    # check if the post request has the file part
    if 'image' not in request.files:
        return redirect(url_for("post_gallery", status="Image Upload Failed: No selected file"))
    file = request.files['image']
    average_rgb = request.form.get('rgb_average')
    rgb_1 = request.form.get('rgb_1')
    rgb_2 = request.form.get('rgb_2')
    rgb_3 = request.form.get('rgb_3')

    def rgb_str_to_tuple(rgb): # convert from rgb(r,g,b) to (r,g,b) format
        return list(map(int, rgb[4:-1].split(',')))

    rgb_1_tuple = rgb_str_to_tuple(rgb_1)
    rgb_2_tuple = rgb_str_to_tuple(rgb_2)
    rgb_3_tuple = rgb_str_to_tuple(rgb_3)


    # START Color Classifier Code by Ajinkya Chavan (published online):
    model = tf.keras.models.load_model('colormodel_trained_90.h5')
    color_dict={
        0 : 'red',
        1 : 'green',
        2 : 'blue',
        3 : 'yellow',
        4 : 'orange',
        5 : 'pink',
        6 : 'purple',
        7 : 'brown',
        8 : 'gray',
        9 : 'black',
        10 : 'white'
    }
    def predict_color(Red, Green, Blue):
        rgb = np.asarray((Red, Green, Blue)) #rgb tuple to numpy array
        input_rgb = np.reshape(rgb, (-1,3)) #reshaping as per input to ANN model
        color_class_confidence = model.predict(input_rgb) # Output of layer is in terms of Confidence of the 11 classes
        color_index = np.argmax(color_class_confidence, axis=1) #finding the color_class index from confidence
        color = color_dict[int(color_index)]
        return color
    # END Color Classifier Code by Ajinkya Chavan

    avg_color_name = predict_color(rgb_1_tuple[0], rgb_1_tuple[1], rgb_1_tuple[2])
    # if gray/white/black/brown, decide based off 2nd palette circle instead
    if avg_color_name == 'gray' or avg_color_name == 'white' or avg_color_name == 'black' or avg_color_name == 'brown':
        avg_color_name = predict_color(rgb_2_tuple[0], rgb_2_tuple[1], rgb_2_tuple[2])
        # if gray/white/black/brown, decide based off 3rd palette circle instead
        if avg_color_name == 'gray' or avg_color_name == 'white' or avg_color_name == 'black' or avg_color_name == 'brown':
            avg_color_name = predict_color(rgb_3_tuple[0], rgb_3_tuple[1], rgb_3_tuple[2])
            if avg_color_name == 'gray' or avg_color_name == 'white' or avg_color_name == 'black':
                # making sure photo isn't grayscale
                if predict_color(rgb_1_tuple[0], rgb_1_tuple[1], rgb_1_tuple[2]) == 'brown' or predict_color(rgb_3_tuple[0], rgb_3_tuple[1], rgb_3_tuple[2]) == 'brown':
                    avg_color_name = 'brown'
                # if still gray/white/black, check if truly black and white
                elif ((abs(rgb_1_tuple[0] - rgb_1_tuple[1]) > 5) or (abs(rgb_1_tuple[1] - rgb_1_tuple[2]) > 5) or (abs(rgb_2_tuple[0] - rgb_2_tuple[1]) > 5) or (abs(rgb_2_tuple[1] - rgb_2_tuple[2]) > 5) or (abs(rgb_3_tuple[0] - rgb_3_tuple[1]) > 5) or (abs(rgb_3_tuple[1] - rgb_3_tuple[2]) > 5)):
                    avg_color_name = 'gray' # 'gray' is the section for coming up black/white/gray but there is a hint of color in there
                # truly grayscale:
                else:
                    avg_color_name = 'black' # 'black if the photo is most likely completely grayscale


    metadata = request.form.get('metadata')
    typedata = request.form.getlist('typemetadata')
    description = request.form.get('description')
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return redirect(url_for("post_gallery", status="Image Upload Failed: No selected file"))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        data = file.read()
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO posts (username, filename, data, rgb_1, rgb_2, rgb_3, avg_color_name, average_rgb, metadata, typedata, profile_id, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (session["profile"]["name"], filename, data, rgb_1, rgb_2, rgb_3, avg_color_name, average_rgb, metadata, typedata, session["profile"]["user_id"], description))
        conn.commit()
        cur.close()
    return redirect(url_for("post_gallery", status="Image Uploaded Succesfully"))

@app.route('/imagegallery', methods=['GET'])
def post_gallery():
    status = request.args.get("status", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT post_id FROM posts ORDER BY post_id desc   ;")
    post_ids = [r[0] for r in cur]
    # cur.execute("SELECT COUNT(*) FROM posts ;")
    cur.execute("SELECT rgb_1 FROM posts ORDER BY post_id desc   ;")
    rgb_1_array = [r[0] for r in cur]
    cur.execute("SELECT rgb_2 FROM posts ORDER BY post_id desc   ;")
    rgb_2_array = [r[0] for r in cur]
    cur.execute("SELECT rgb_3 FROM posts ORDER BY post_id desc   ;")
    rgb_3_array = [r[0] for r in cur]
    cur.execute("SELECT average_rgb FROM posts ORDER BY post_id desc;")
    average_rgb_array = [r[0] for r in cur]
    if ('profile' in session):
        cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
        post_id = cur.fetchone()[0]
    else:
        post_id = []
    return render_template("home.html", post_ids = post_ids, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array, post_id=post_id)


@app.route('/image/<int:post_id>')
def view_post(post_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts WHERE post_id=%s", (post_id,))
    post_row = cur.fetchone()
    cur.close()
    stream = io.BytesIO(post_row[3])

    # use special "send_file" function
    return send_file(stream, attachment_filename=post_row[2])

@app.route('/post/<int:clicked_post_id>')
def clicked_post(clicked_post_id):
    str_id = str(clicked_post_id)
    if session.get('profile') is None:
        return redirect(url_for('login'))
    else:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT profile_id FROM posts WHERE post_id =%s",(str_id,))
        post_profile_id = cur.fetchone()[0]
        if len(post_profile_id) == 0:
            return redirect(url_for('post_gallery'))
        cur.execute("SELECT rgb_1 FROM posts WHERE post_id =%s",(str_id,))
        rgb_1_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_2 FROM posts WHERE post_id =%s",(str_id,))
        rgb_2_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_3 FROM posts WHERE post_id =%s",(str_id,))
        rgb_3_array = [r[0] for r in cur]
        cur.execute("SELECT average_rgb FROM posts WHERE post_id =%s",(str_id,))
        average_rgb_array = [r[0] for r in cur]
        cur.execute("SELECT metadata FROM posts WHERE post_id =%s",(str_id,))
        post_metadata = cur.fetchone()[0]
        cur.execute("SELECT typedata FROM posts WHERE post_id =%s",(str_id,))
        post_type = cur.fetchall()[0][0].replace("{","").replace("}", "").replace('"',"")
        cur.execute("SELECT description FROM posts WHERE post_id =%s",(str_id,))
        post_description = cur.fetchone()[0]
        cur.execute("SELECT username FROM posts WHERE post_id = %s;",(str_id,))
        username = cur.fetchone()[0]
        cur.execute("SELECT profile_id FROM posts WHERE post_id =%s",(str_id,))
        profid = cur.fetchone()[0]
        #sends the liked_posts array to update hearts
        cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
        post_id = cur.fetchone()[0]
        return render_template("palette_post.html", the_clicked_post_id = clicked_post_id, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array, post_profile_id = post_profile_id, post_metadata = post_metadata, post_type = post_type, post_description = post_description, username = username, profid=profid, post_id=post_id)

@app.route('/delete/<int:clicked_post_id>',methods=['POST'])
def delete_post(clicked_post_id):
    str_id = str(clicked_post_id)
    if session.get('profile') is None:
        return redirect(url_for('login'))
    else:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM posts WHERE post_id =%s",(str_id,))
        conn.commit()
        cur.execute("update users set liked_posts = array_remove(liked_posts, %s)", (clicked_post_id,))
        conn.commit()
        cur.close()
        return redirect(url_for('profile'))


@app.route('/upload')
def upload():
    return render_template("upload.html")


@app.route('/profile')
def profile():
    if session.get('profile') is None:
        return redirect(url_for('post_gallery'))
    else:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT post_id FROM posts WHERE profile_id = %s ORDER BY post_id desc   ;",(session['profile']['user_id'],))
        post_ids = [r[0] for r in cur]
        cur.execute("SELECT rgb_1 FROM posts WHERE profile_id = %s ORDER BY post_id desc   ;",(session['profile']['user_id'],))
        rgb_1_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_2 FROM posts WHERE profile_id = %s ORDER BY post_id desc   ;",(session['profile']['user_id'],))
        rgb_2_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_3 FROM posts WHERE profile_id = %s ORDER BY post_id desc   ;",(session['profile']['user_id'],))
        rgb_3_array = [r[0] for r in cur]
        cur.execute("SELECT average_rgb FROM posts WHERE profile_id =%s ORDER BY post_id desc;",(session['profile']['user_id'],))
        average_rgb_array = [r[0] for r in cur]
        cur.execute("SELECT username FROM users WHERE profile_id = %s;",(session['profile']['user_id'],))
        usernames = cur.fetchall()
        for u in usernames:
             username = u[0]
        cur.execute("SELECT background1 FROM users WHERE profile_id = %s;",(session['profile']['user_id'],))
        backgrounds1 = cur.fetchall()
        for b in backgrounds1:
            background1 = b[0]
        cur.execute("SELECT background2 FROM users WHERE profile_id = %s;",(session['profile']['user_id'],))
        backgrounds2 = cur.fetchall()
        for b in backgrounds2:
            background2 = b[0]
        return render_template("profile.html", post_ids = post_ids, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array, username = username, background1 = background1, background2 = background2)


@app.route('/editProfile')
def edit_profile():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE profile_id = %s;",(session['profile']['user_id'],))
    usernames = cur.fetchall()
    for u in usernames:
        username = u[0]
    cur.execute("SELECT background1 FROM users WHERE profile_id = %s;",(session['profile']['user_id'],))
    backgrounds1 = cur.fetchall()
    for b in backgrounds1:
        background1 = b[0]
    cur.execute("SELECT background2 FROM users WHERE profile_id = %s;",(session['profile']['user_id'],))
    backgrounds2 = cur.fetchall()
    for b in backgrounds2:
        background2 = b[0]
    cur.execute("SELECT post_id FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(session['profile']['user_id'],))
    post_ids = [r[0] for r in cur]
    cur.execute("SELECT rgb_1 FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(session['profile']['user_id'],))
    rgb_1_array = [r[0] for r in cur]
    cur.execute("SELECT rgb_2 FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(session['profile']['user_id'],))
    rgb_2_array = [r[0] for r in cur]
    cur.execute("SELECT rgb_3 FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(session['profile']['user_id'],))
    rgb_3_array = [r[0] for r in cur]
    cur.execute("SELECT average_rgb FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(session['profile']['user_id'],))
    average_rgb_array = [r[0] for r in cur]
    return render_template("edit_profile.html", username = username, background1 = background1, background2 = background2, post_ids = post_ids, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array)


@app.route('/editUsername', methods=['POST'])
def edit_username():
    editedUsername = request.form['editUsernameInput']
    if session.get('profile') is None:
        return redirect(url_for('post_gallery'))
    else:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET username =%s WHERE profile_id =%s;",(editedUsername, session['profile']['user_id']))
        conn.commit()
        cur.close()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE posts SET username =%s WHERE profile_id =%s;",(editedUsername, session['profile']['user_id']))
        conn.commit()
        cur.close()

        return redirect(url_for('edit_profile'))


@app.route('/search.html')
def search():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT post_id FROM posts ORDER BY post_id desc   ;")
    post_ids = [r[0] for r in cur]
    # cur.execute("SELECT COUNT(*) FROM posts ;")
    cur.execute("SELECT rgb_1 FROM  posts ORDER BY post_id desc   ;")
    rgb_1_array = [r[0] for r in cur]
    cur.execute("SELECT rgb_2 FROM  posts ORDER BY post_id desc   ;")
    rgb_2_array = [r[0] for r in cur]
    cur.execute("SELECT rgb_3 FROM  posts ORDER BY post_id desc   ;")
    rgb_3_array = [r[0] for r in cur]
    cur.execute("SELECT average_rgb FROM posts ORDER BY post_id desc ;")
    average_rgb_array = [r[0] for r in cur]
    if ('profile' in session):
        cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
        post_id = cur.fetchone()[0]
    else:
        post_id = []
    return render_template("search.html", post_ids = post_ids, post_id=post_id, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array)

@app.route('/search_result.html')
def search_results():
    conn = get_db()
    cur = conn.cursor()
    userstring = request.args.get("search")
    if "rgb" in userstring:
        cur.execute("SELECT post_id FROM posts where (color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42)  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, userstring, userstring, userstring, userstring, userstring))
        post_ids = [r[0] for r in cur]
        cur.execute("SELECT rgb_1 FROM posts where (color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42)  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, userstring, userstring, userstring, userstring, userstring))
        rgb_1_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_2 FROM posts where (color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42)  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, userstring, userstring, userstring, userstring, userstring))
        rgb_2_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_3 FROM posts where (color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42)  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, userstring, userstring, userstring, userstring, userstring))
        rgb_3_array = [r[0] for r in cur]
        cur.execute("SELECT average_rgb FROM posts where (color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42)  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, userstring, userstring, userstring, userstring, userstring))
        average_rgb_array = [r[0] for r in cur]
        if ('profile' in session):
            cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
            post_id = cur.fetchone()[0]
        else:
            post_id = []
        return render_template("search_result.html", post_ids = post_ids,post_id=post_id, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array)

    # if gets to this point, userstring is not in rgb(r,g,b) format
    try:
        # see if userstring is a css color name (if so, jump down to else case)
        rgb = name_to_rgb(userstring)
        rgb_string = f'rgb({rgb[0]}, {rgb[1]}, {rgb[2]})'
    except Exception as not_color:
        # userstring is not a css color name... search through metadata/typedata
        userstring= '%'+str(userstring)+'%'
        cur.execute("SELECT post_id FROM posts where lower(metadata) like %s  or lower(typedata) like %s  ORDER BY post_id desc;",(userstring, userstring))
        post_ids = [r[0] for r in cur]
        cur.execute("SELECT rgb_1 FROM posts where lower(metadata) like %s  or lower(typedata) like %s  ORDER BY post_id desc;",(userstring, userstring))
        rgb_1_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_2 FROM posts where lower(metadata) like %s  or lower(typedata) like %s  ORDER BY post_id desc;",(userstring, userstring))
        rgb_2_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_3 FROM posts where lower(metadata) like %s  or lower(typedata) like %s  ORDER BY post_id desc;",(userstring, userstring))
        rgb_3_array = [r[0] for r in cur]
        cur.execute("SELECT average_rgb FROM posts where lower(metadata) like %s  or lower(typedata) like %s  ORDER BY post_id desc;",(userstring, userstring))
        average_rgb_array = [r[0] for r in cur]
        if ('profile' in session):
            cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
            post_id = cur.fetchone()[0]
        else:
            post_id = []
        return render_template("search_result.html", post_ids = post_ids,post_id=post_id, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array=average_rgb_array)
    else:
        # case both for category buttons under the search bar and typing css color names into search bar:
        if userstring == 'red' or userstring == 'green' or userstring == 'blue' or userstring == 'yellow' or userstring == 'orange' or userstring == 'pink' or userstring == 'purple' or userstring == 'brown' or userstring == 'black' or userstring == 'gray':
            if userstring == 'orange': # because css orange default is too yellow
                rgb_string = 'rgb(224,113,74)'
            if userstring == 'brown': # because css brown default is too red
                rgb_string = 'rgb(105, 52, 20)'
            userstring= '%'+str(userstring)+'%'
            cur.execute("SELECT post_id FROM posts where avg_color_name like %s  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, rgb_string, rgb_string, rgb_string))
            post_ids = [r[0] for r in cur]
            cur.execute("SELECT rgb_1 FROM posts where avg_color_name like %s  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, rgb_string, rgb_string, rgb_string))
            rgb_1_array = [r[0] for r in cur]
            cur.execute("SELECT rgb_2 FROM posts where avg_color_name like %s  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, rgb_string, rgb_string, rgb_string))
            rgb_2_array = [r[0] for r in cur]
            cur.execute("SELECT rgb_3 FROM posts where avg_color_name like %s  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, rgb_string, rgb_string, rgb_string))
            rgb_3_array = [r[0] for r in cur]
            cur.execute("SELECT average_rgb FROM posts where avg_color_name like %s  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (userstring, rgb_string, rgb_string, rgb_string))
            average_rgb_array = [r[0] for r in cur]
            if ('profile' in session):
                cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
                post_id = cur.fetchone()[0]
            else:
                post_id = []
            return render_template("search_result.html", post_ids = post_ids, post_id=post_id,rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array)
        # userstring is a css color name
        rgb = name_to_rgb(userstring)
        rgb_string = f'rgb({rgb[0]}, {rgb[1]}, {rgb[2]})' #turning the string color name to rgb(r,g,b) format
        cur.execute("SELECT post_id FROM posts where color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (rgb_string, rgb_string, rgb_string, rgb_string, rgb_string, rgb_string))
        post_ids = [r[0] for r in cur]
        cur.execute("SELECT rgb_1 FROM posts where color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (rgb_string, rgb_string, rgb_string, rgb_string, rgb_string, rgb_string))
        rgb_1_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_2 FROM posts where color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (rgb_string, rgb_string, rgb_string, rgb_string, rgb_string, rgb_string))
        rgb_2_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_3 FROM posts where color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (rgb_string, rgb_string, rgb_string, rgb_string, rgb_string, rgb_string))
        rgb_3_array = [r[0] for r in cur]
        cur.execute("SELECT average_rgb FROM posts where color_distance(rgb_1, %s) < 42  or color_distance(rgb_2, %s) < 42  or color_distance(rgb_3, %s) < 42  ORDER BY LEAST(color_distance(rgb_1, %s), color_distance(rgb_2, %s), color_distance(rgb_3, %s)) ;", (rgb_string, rgb_string, rgb_string, rgb_string, rgb_string, rgb_string))
        average_rgb_array = [r[0] for r in cur]
        if ('profile' in session):
            cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
            post_id = cur.fetchone()[0]
        else:
            post_id = []
        return render_template("search_result.html", post_ids = post_ids, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array,post_id=post_id)

@app.route('/editProfile', methods=['POST'])
def edit_background_color():
    firstColorPicked = request.form['firstColorPicked']
    secondColorPicked = request.form['secondColorPicked']
    conn = get_db()
    cur = conn.cursor()
    if firstColorPicked:
        cur.execute("UPDATE users SET background1 =%s WHERE profile_id =%s;",(firstColorPicked, session['profile']['user_id']))
    else:
        print("Don't psql update.")
    if secondColorPicked:
        cur.execute("UPDATE users SET background2 =%s WHERE profile_id =%s;",(secondColorPicked, session['profile']['user_id']))
    else:
        print("Don't psql update.")

    conn.commit()
    cur.close()


    return redirect(url_for('profile'))

@app.route('/about_us', methods=['GET'])
def about_us():
    return render_template("about_us.html")

@app.route('/post/edit/title/<int:clicked_post_id>', methods=['POST'])
def change_title(clicked_post_id):
    str_id = str(clicked_post_id)
    conn = get_db()
    cur = conn.cursor()
    metadata = request.form.get('metadata')
    cur.execute("UPDATE posts SET metadata =%s WHERE post_id =%s;",(metadata,str_id))
    conn.commit()
    cur.close()
    return redirect(url_for('clicked_post',clicked_post_id = str_id))

@app.route('/post/edit/type/<int:clicked_post_id>', methods=['POST'])
def change_type(clicked_post_id):
    str_id = str(clicked_post_id)
    conn = get_db()
    cur = conn.cursor()
    typedata = request.form.getlist('typemetadata')
    cur.execute("UPDATE posts SET typedata =%s WHERE post_id =%s;",(typedata,str_id))
    conn.commit()
    cur.close()
    return redirect(url_for('clicked_post',clicked_post_id = str_id))

@app.route('/post/edit/desc/<int:clicked_post_id>', methods=['POST'])
def change_desc(clicked_post_id):
    str_id = str(clicked_post_id)
    conn = get_db()
    cur = conn.cursor()
    description = request.form.get('description')
    cur.execute("UPDATE posts SET description =%s WHERE post_id =%s;",(description,str_id))
    conn.commit()
    cur.close()
    return redirect(url_for('clicked_post',clicked_post_id = str_id))

@app.route('/post/edit/background/<int:clicked_post_id>', methods=['POST'])
def change_background(clicked_post_id):
    str_id = str(clicked_post_id)
    conn = get_db()
    cur = conn.cursor()
    background = request.form.get('background')
    cur.execute("UPDATE posts SET average_rgb =%s WHERE post_id =%s;",(background,str_id))
    conn.commit()
    cur.close()
    return redirect(url_for('clicked_post',clicked_post_id = str_id))

@app.route('/Profile/<string:username>')
def users_profile(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT profile_id FROM posts WHERE username = %s;",(username,))
    user = username
    cur.execute("SELECT * FROM users where profile_id = %s", (user,))
    p = cur.fetchall()
    person = []
    columnNames = [column[0] for column in cur.description]

    for record in p:
        person.append( dict( zip( columnNames , record )))

    if username == session['profile']['user_id']:
        return redirect(url_for('profile'))
    else:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT post_id FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(user,))
        post_ids = [r[0] for r in cur]
        cur.execute("SELECT rgb_1 FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(user,))
        rgb_1_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_2 FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(user,))
        rgb_2_array = [r[0] for r in cur]
        cur.execute("SELECT rgb_3 FROM posts WHERE profile_id = %s ORDER BY post_id desc;",(user,))
        rgb_3_array = [r[0] for r in cur]
        cur.execute("SELECT average_rgb FROM posts WHERE profile_id =%s ORDER BY post_id desc;",(user,))
        average_rgb_array = [r[0] for r in cur]
        cur.execute("SELECT username FROM users WHERE profile_id = %s;",(user,))
        usernames = cur.fetchall()
        for u in usernames:
             username = u[0]
        cur.execute("SELECT background1 FROM users WHERE profile_id = %s;",(user,))
        backgrounds1 = cur.fetchall()
        background1 = 0
        for b in backgrounds1:
            background1 = b[0]
        cur.execute("SELECT background2 FROM users WHERE profile_id = %s;",(user,))
        backgrounds2 = cur.fetchall()
        background2 = 0
        for b in backgrounds2:
            background2 = b[0]
        cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
        post_id = cur.fetchone()[0]
        return render_template("user_profile.html", post_ids = post_ids,post_id=post_id, rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array, username = username, background1 = background1, background2 = background2, person=person, id=user)

@app.route('/imagegallery', methods=['POST'])
def like_post():
    id = request.form.get('id')
    print(id)
    like_id = "{"+ id +"}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
    post_id = cur.fetchone()[0]
    post_id = set(post_id)
    if int(id) in post_id:
        return ''
    else:
        cur.execute("UPDATE users SET liked_posts = (SELECT liked_posts FROM users WHERE profile_id = %s) || %s where profile_id = %s;", (session['profile']['user_id'], like_id, session['profile']['user_id']))
        conn.commit()
        return ''

# update users set liked_posts = (select liked_posts from users where username = 'Luisa Jimenez Alarcon') || '{4}' where username = 'Luisa Jimenez Alarcon';

@app.route('/likes')
def liked_post():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT liked_posts FROM users where profile_id = %s", (session['profile']['user_id'],))
    post_id = cur.fetchone()[0]
    post_ids = list(dict.fromkeys(post_id))

    cur.execute("SELECT rgb_1 FROM posts ORDER BY post_id desc   ;")
    rgb_1_arraycopy = [r[0] for r in cur]
    rgb_1_array = []
    rgb_2_array = []
    rgb_3_array = []
    average_rgb_array = []
    for e in post_ids:
        cur.execute("SELECT rgb_1 FROM posts where post_id = %s  ORDER BY post_id desc ;", (e,))
        rgb_1_ = cur.fetchone()[0]
        rgb_1_array.append(rgb_1_)
        cur.execute("SELECT rgb_2 FROM posts where post_id = %s  ORDER BY post_id desc ;", (e,))
        rgb_2_ = cur.fetchone()[0]
        rgb_2_array.append(rgb_2_)
        cur.execute("SELECT rgb_3 FROM posts where post_id = %s  ORDER BY post_id desc ;", (e,))
        rgb_3_ = cur.fetchone()[0]
        rgb_3_array.append(rgb_3_)
        cur.execute("SELECT average_rgb FROM posts where post_id = %s  ORDER BY post_id desc ;", (e,))
        average_rgb_ = cur.fetchone()[0]
        average_rgb_array.append(average_rgb_)
    return render_template("liked_posts.html", post_ids = post_ids,post_id=post_id, rgb_1_arraycopy=rgb_1_arraycopy,  rgb_1_array = rgb_1_array, rgb_2_array = rgb_2_array, rgb_3_array = rgb_3_array, average_rgb_array = average_rgb_array)

@app.route('/likes', methods=['POST'])
def disliked_post():
    id = request.form.get('id')
    print(id)
    like_id = "{"+ id +"}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute("update users set liked_posts = array_remove(liked_posts, %s) where profile_id = %s", (id, session['profile']['user_id']))
    conn.commit()
    cur.close()
    return redirect(url_for('liked_post'))