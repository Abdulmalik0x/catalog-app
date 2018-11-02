# coding: utf-8
from flask import Flask
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# from sqlalchemy_dao import Dao, POOL_DEFAULT, POOL_DISABLED
# from sqlalchemy.pool import SingletonThreadPool
from database_setup import Categories, Base, CategoryItems, User
from flask import (render_template,
                   url_for,
                   request,
                   redirect,
                   flash,
                   jsonify,
                   abort)
from flask import session as login_session
import random
import string
from flask_login import LoginManager
from functools import wraps
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import os


app = Flask(__name__)
# Connect to db and create db session
# this because sqlite require new thread for each transaction with DB

engine = create_engine('sqlite:///itemscategory.db',
                       connect_args={'check_same_thread': False})
""" MetaData object contains all of the schema
constructs we’ve associated with it """
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


os.chdir("D:/Downloads/fsnd-virtual-machine/FSND-Virtual-Machine/vagrant/")
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


@app.route('/login')
def loginOauth():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state, CLIENT_ID=CLIENT_ID)

# Facebook login oauth api


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # decode because value contant b'value' which affect the url
    access_token = request.data.decode()
    print("access token received %s " % access_token)

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_secret']
    url = """https://graph.facebook.com/oauth/access_token?grant_type=
    fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s""" % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    # problem is access token insetion be like b'value'
    result = h.request(url, 'GET')[1]
    print(result)  # to see the result of url

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange
        we have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then we
        split it on colons to pull out the actual token value and replace the
        remaining quotes with nothing so that it can be used directly in
        the graph api calls
    '''
    token = result.decode('utf8').split(',')[0].split(':')[1].replace(
        '"', '')  # decode('utf8') added to decode str to bytes

    url = """https://graph.facebook.com/v2.8/me?
    access_token=%s&fields=name,id,email""" % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    print("API JSON result: %s" % result)
    data = json.loads(result)
    print("Api date : %s" % data)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['facebook_id'] = data["id"]
    try:
        login_session['email'] = data["email"]
    except:
        pass

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = """https://graph.facebook.com/v2.8/me/picture?
    access_token=%s&redirect=0&height=200&width=200""" % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    print("Returned result after consume access token : %s" % (result,))
    data = json.loads(result)
    print("After converting to json : %s" % (data,))

    login_session['picture'] = data["data"]["url"]

    print("Reach here")
    # see if user exists
    user_id = getUserId(login_session['email'])
    if not user_id:
        # not tested yet, may be need serialize
        user_id = createUser(login_session)
        print("User created")

    login_session['user_id'] = user_id.id
    print("login_session info after sign in : %s " % login_session)

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ " style = "width: 300px; height: 300px;
    border-radius: 150px;-webkit-border-radius: 150px;
    -moz-border-radius: 150px;"> """

    flash("Now logged in as %s" % login_session['username'])
    return output


# Google oauth login API
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token, compare logged session with request session
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token for user data is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1].decode('utf-8'))

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps("""Current user is
        already connected."""), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    """ To check logged user have account in db, if not create one """
    email = login_session['email']
    try:
        print("email %s" % email)
        # print("Query : %s" % session.query(
        # User).filter_by(email=email).first())
        try:
            user = session.query(User).filter_by(
                email=login_session['email']).one()
            if user is not None:
                login_session['user_id'] = user.id
                print("User already have accoun in database")
        except:
            pass
    except:
        print("Error Happened")
        createUser(login_session)
        print("New user has been added")

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ " style = "width: 300px; height: 300px;
    border-radius: 150px;-webkit-border-radius: 150px;
    -moz-border-radius: 150px;"> """
    flash("you are now logged in as %s" % login_session['username'])
    print("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print('In gdisconnect access token is %s ' % access_token)
    print('User name is : %s' % login_session['username'])
    url = """https://accounts.google.com/o/oauth2/
    revoke?token=%s""" % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is : %s ' % result)

    if result['status'] == '200':  # response is 400 !!
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.'))
        response.headers['Content-Type'] = 'application/json'
    return response


def createUser(login_session):
    print("Here is login name " + login_session['username'])
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserId(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.serialize['id']
    except:
        return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
            flash("Welcome again")
        else:
            flash("You are not allowed to access there")
            return redirect('/login')
    return decorated_function


@app.route('/')
@app.route('/catalog/')
@login_required
def catalogIndex():
    categories = session.query(Categories).all()
    categoriesItems = session.query(CategoryItems).all()
    print("Leangth of category items : %s" % len(categoriesItems))
    return render_template('main.html', categories=categories,
                           categoriesItems=categoriesItems)


@app.route('/catalog/<categoryName>/items')
def showItems(categoryName):
        category = session.query(Categories).filter_by(
            name=categoryName).first()
        categoryItems = session.query(CategoryItems).filter_by(
            categoryId=category.id)
        categories = session.query(Categories).all()
        return render_template('categoryItems.html',
                               category=category,
                               categoryItems=categoryItems,
                               categories=categories)


@app.route('/catalog/<categoryName>/<itemName>/')
@login_required
def showItem(categoryName, itemName):
    print(login_session['username'])
    categories = session.query(Categories).all()
    category = session.query(Categories).filter_by(name=categoryName).first()
    CategoryItem = session.query(CategoryItems).filter_by(
        title=itemName, categoryId=category.id).first()
    return render_template('categoryItem.html', itemCategory=category,
                           item=CategoryItem, categories=categories)


@app.route('/catalog/addNewCategory/', methods=['GET', 'POST'])
@login_required
def addCategory():
    if request.method == 'GET':
        categories = session.query(Categories).all()
        return render_template('addNewCategory.html', categories=categories)
    else:
        try:
            newCategroy = Categories(name=request.form['category-name'])
            session.add(newCategroy)
            session.commit()
            flash("New category has bean added !")
            return redirect(url_for('catalogIndex'))
        except:
            abort(404)


@app.route('/catalog/<categoryName>/newItem', methods=['GET', 'POST'])
@login_required
def addNewCategroyItem(categoryName):
    print("login_session : %s " % login_session)
    print(request.method)
    category = session.query(Categories).filter_by(
        name=categoryName).first()
    if request.method == 'POST':
        category = session.query(Categories).filter_by(
            name=categoryName).first()
        # more filter to add for handling multiple values with same name
        print("login_session : %s " % login_session['email'])
        try:
            user_file = session.query(User).filter_by(
                id=login_session['user_id']).first()
        except:
            print("user not exist")
            createUser(login_session)
            user_file = session.query(User).filter_by(
                email=login_session['email']).first()
            login_session['user_id'] = user_file.id
            print("created")

        # print("user_file %s" + %user_file)
        newItem = CategoryItems(
                title=request.form['itemName'],
                categoryId=category.id, creatorId=user_file.id)
        session.add(newItem)
        session.commit()
        print(str(newItem.creatorId))
        flash("New menu item have added successfully!")
        return redirect(url_for('showItems', categoryName=category.name))
    else:
        categories = session.query(Categories).all()
        return render_template('addNewCategroyItem.html',
                               category=category, categories=categories)


@app.route('/catalog/<categoryName>/<itemName>/editItem',
           methods=['GET', 'POST'])
@login_required
def editCategoryItem(categoryName, itemName):
    category = session.query(Categories).filter_by(name=categoryName).first()
    item = session.query(CategoryItems).filter_by(
        title=itemName, categoryId=category.id).one()
    if request.method == 'POST':
        print(item.id)
        if login_session['user_id'] != item.creatorId:
            flash("Now allowed to edit")
            return redirect(url_for('showItem',
                                    categoryName=categoryName,
                                    itemName=itemName))
        selectedCategory = request.form.get('category-selected')

        newCategory = session.query(Categories).filter_by(
            name=selectedCategory).first()

        session.query(CategoryItems).filter_by(
            title=itemName,
            categoryId=category.id).update(
                {"title": request.form['itemName'],
                 "description": request.form['description'],
                 "categoryId": newCategory.id})

        """Update query doesn't delete the itme
        id if moved, query below to delete it"""
        if newCategory.id != category.id:

            session.query(CategoryItems).filter_by(
                categoryId=category.id, title=itemName).delete()
            print("new category name :" + newCategory.name)
            flash("Item has bean edited succefully!")
        return redirect(url_for('showItems', categoryName=selectedCategory))
    else:
        print("Reach 3")
        itemToEdit = session.query(CategoryItems).filter_by(
            categoryId=category.id, title=itemName).first()
        category = session.query(Categories).filter_by(
            name=categoryName).first()
        categories = session.query(Categories).all()
        return render_template('editCategoryItem.html', category=category,
                               categories=categories, item=itemToEdit)


@app.route('/catalog/<categoryName>/<itemName>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(categoryName, itemName):
    category = session.query(Categories).filter_by(name=categoryName).first()
    item = session.query(CategoryItems).filter_by(
                                        title=itemName,
                                        categoryId=category.id).one()
    if request.method == 'POST':
        print("POST")
        if(login_session['user_id'] == item.creatorId):
            session.query(CategoryItems).filter_by(categoryId=category.id,
                                                   title=itemName).delete()
            flash("Item has been deleted!")
        else:
            flash("Unaouthrized action")
            return redirect('/catalog/<categoryName>/<itemName>/')
        return redirect(url_for('showItems', categoryName=categoryName))
    else:
        print(categoryName + " " + itemName)
        return render_template('deleteItem.html', categoryName=categoryName,
                               itemName=itemName)


# API for all app categories info.
@app.route('/catalog/json')
def allAPI():

    categories = session.query(Categories).all()
    items = session.query(CategoryItems).all()

    CategorySerialized = [i.serialize for i in categories]
    ItemSerialized = [b.serialize for b in items]
    return jsonify(CategorySerialized=CategorySerialized,
                   ItemSerialized=ItemSerialized)


@app.route('/catalog/<categoryName>/json')
def categoryAPI(categoryName):

    category = session.query(Categories).filter_by(name=categoryName).one()

    CategorySerialized = [category.serialize]
    return jsonify(CategorySerialized=CategorySerialized)


@app.route('/catalog/<categoryName>/<itemName>/json')
def categoryWithItemsAPI(categoryName, itemName):
    category = session.query(Categories).filter_by(name=categoryName).one()
    items = session.query(CategoryItems)\
                   .filter_by(categoryId=category.id).all()

    ItemSerialized = [b.serialize for b in items]
    return jsonify(ItemSerialized=ItemSerialized)

if __name__ == '__main__':
    """ each session require secret key,
    to access the methods inside it like flash"""

    app.secret_key = 'super_secret_key'
    app.debug = True  # Auto reload for server if change occurs
    # login_manager = LoginManager()
    # login_manager.init_app(app)
    # login_manager.login_view = 'loginOauth'
    app.run(host='0.0.0.0', port=5050)
