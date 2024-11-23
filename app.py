from flask import Flask, jsonify, request, session, redirect, url_for
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import re
from flask_cors import CORS

app = Flask(__name__)
# CORS(app, supports_credentials=True)
CORS(app, origins="*", supports_credentials=True)
# Configuration de la base de données MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_DB'] = 'food'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

# Clé secrète pour les sessions
app.secret_key = 'aa'



# Route de connexion
@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    mdp = request.json.get('password')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE Email=%s", (email,))
    user_data = cur.fetchone()
    cur.close()

    if user_data:
        stored_password = user_data['password']
        print(f"Stored Password: {stored_password}")

        if bcrypt.check_password_hash(stored_password, mdp):
            session['user_id'] = user_data['id']
            return jsonify({'message': 'Login successful', 'user': user_data['id']}), 200
        else:
            return jsonify({'message': 'Invalid email or password'}), 401
    else:
        return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/signup', methods=['POST'])
def signup():
    cur = mysql.connection.cursor()
    data = request.get_json()

    # Mise à jour des champs requis selon la table users
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Missing required fields'}), 400

    email = data.get('email')

    # Vérification si l'email existe déjà
    cur.execute("SELECT * FROM users WHERE Email=%s", (email,))
    existing_user = cur.fetchone()

    if existing_user:
        return jsonify({'message': 'User with this email already exists'}), 400

    username = data.get('username')
    password = data.get('password')  # Utilisation de 'password' au lieu de 'mdp'

    # Hachage du mot de passe
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    cur.execute("INSERT INTO users (Username, Email,password) VALUES (%s, %s, %s)",
                (username, email, hashed_password))
    mysql.connection.commit()
    cur.close()

    return jsonify({'message': 'Utilisateur créé avec succès', 'user': cur.lastrowid}), 201
    # Route pour obtenir les informations du profil utilisateur
@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user_data = cur.fetchone()
    cur.close()

    if user_data:
        return jsonify({
            'username': user_data['username'],
            'email': user_data['email'],
        })
    else:
        return jsonify({'message': 'User not found'}), 404
@app.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    cur = mysql.connection.cursor()
    data = request.json

    # Récupérer les informations actuelles de l'utilisateur
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user_data = cur.fetchone()

    if user_data:
        # Vérifier les champs présents dans la requête
        updated_username = data.get('username', user_data['username'])
        updated_email = data.get('email', user_data['email'])

        query = """
            UPDATE users 
            SET username=%s, email=%s
            WHERE id=%s
        """
        values = (updated_username, updated_email, user_id)
        cur.execute(query, values)
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Profile updated successfully'})
    else:
        cur.close()
        return jsonify({'message': 'User not found'}), 404


# food
from flask import jsonify

@app.route('/allfoods', methods=['GET'])
def get_all_foods():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM foods')
    foods = cur.fetchall()
    cur.close()

    food_list = []
    for food in foods:
        food_list.append({
            'id': food['id'],
            'name': food['name'],
            'description': food['description'],
            'price': float(food['price']),
            'image_url':f"http://192.168.1.24:5000/imagesFood/{food['image_path']}",
            'category': food['category']  # Ajout de la catégorie
        })

    return jsonify({'foods': food_list})

import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
# Configuration pour les images
app.config['UPLOAD_FOLDER'] = 'C:/Users/User/Desktop/backend_flutter/imagesFood'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/imagesFood/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/foods/add', methods=['POST'])
def add_food():
    if 'image' not in request.files:
        return jsonify({'message': 'No image file provided'}), 400

    file = request.files['image']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        data = request.form
        name = data.get('name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')  # Récupération de la catégorie

        if not name or not description or not price or not category:
            return jsonify({'message': 'Missing required fields'}), 400

        cur = mysql.connection.cursor()
        query = "INSERT INTO foods (name, description, price, image_path, category) VALUES (%s, %s, %s, %s, %s)"
        values = (name, description, price, filename, category)
        cur.execute(query, values)
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Food item added successfully'}), 201
    else:
        return jsonify({'message': 'Invalid file type'}), 400





@app.route('/foods/category/<category>', methods=['GET'])
def get_foods_by_category(category):
    cur = mysql.connection.cursor()
    # Sélectionner les aliments qui correspondent à la catégorie donnée
    query = "SELECT * FROM foods WHERE category=%s"
    cur.execute(query, (category,))
    foods = cur.fetchall()
    cur.close()

    # Formater la réponse
    food_list = []
    for food in foods:
        food_list.append({
            'id': food['id'],
            'name': food['name'],
            'description': food['description'],
            'price': float(food['price']),
            'image_url': f"http://192.168.1.24:5000/imagesFood/{food['image_path']}",
            'category': food['category']
        })

    return jsonify({'foods': food_list})



@app.route('/foods/<int:food_id>', methods=['GET'])
def get_food_by_id(food_id):
    cur = mysql.connection.cursor()
    query = "SELECT * FROM foods WHERE id = %s"
    cur.execute(query, (food_id,))
    food = cur.fetchone()
    cur.close()

    if food:
        food_details = {
            'id': food['id'],
            'name': food['name'],
            'description': food['description'],
            'price': float(food['price']),
            'image_url': f"http://192.168.1.24:5000/imagesFood/{food['image_path']}",
            'category': food['category']
        }
        return jsonify({'food': food_details}), 200
    else:
        return jsonify({'message': 'Food not found'}), 404



@app.route('/deletefood/<int:food_id>', methods=['DELETE'])
def delete_food(food_id):
    # Ouvrir un curseur pour exécuter la requête de suppression
    cur = mysql.connection.cursor()

    # Exécuter la requête de suppression
    cur.execute("DELETE FROM foods WHERE id = %s", (food_id,))

    # Committer les changements dans la base de données
    mysql.connection.commit()

    # Vérifier si l'aliment a été supprimé
    if cur.rowcount > 0:
        cur.close()
        return jsonify({'message': 'Food deleted successfully'}), 200
    else:
        cur.close()
        return jsonify({'message': 'Food not found'}), 404



@app.route('/foods/update/<int:food_id>', methods=['PUT'])
def update_food(food_id):
    # Ouvrir un curseur pour exécuter la requête de mise à jour
    cur = mysql.connection.cursor()

    # Vérifier si une nouvelle image est fournie
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            # Sauvegarder le nouveau fichier image
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Mettre à jour l'aliment avec le nouveau fichier image
            query = """
                UPDATE foods
                SET name = %s, description = %s, price = %s, image_path = %s, category = %s
                WHERE id = %s
            """
            data = (
                request.form.get('name'),
                request.form.get('description'),
                request.form.get('price'),
                filename,  # Nouvel image
                request.form.get('category'),
                food_id
            )
        else:
            return jsonify({'message': 'Invalid file type'}), 400
    else:
        # Si aucune image n'est fournie, mettre à jour sans l'image
        query = """
            UPDATE foods
            SET name = %s, description = %s, price = %s, category = %s
            WHERE id = %s
        """
        data = (
            request.form.get('name'),
            request.form.get('description'),
            request.form.get('price'),
            request.form.get('category'),
            food_id
        )

    # Exécuter la requête de mise à jour
    cur.execute(query, data)
    mysql.connection.commit()

    # Vérifier si la mise à jour a été effectuée
    if cur.rowcount > 0:
        cur.close()
        return jsonify({'message': 'Food updated successfully'}), 200
    else:
        cur.close()
        return jsonify({'message': 'Food not found'}), 404














@app.route('/cart', methods=['POST'])
def add_to_cart():
    data = request.json
    cur = mysql.connection.cursor()
    query = "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)"
    values = (data['user_id'], data['product_id'], data['quantity'])
    cur.execute(query, values)
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Product added to cart'}), 201


# Route pour obtenir les articles du panier
@app.route('/cart/<int:user_id>', methods=['GET'])
def get_cart(user_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM cart WHERE user_id=%s', (user_id,))
    cart_items = cur.fetchall()
    cur.close()

    cart_list = []
    for item in cart_items:
        cart_list.append({
            'id': item['id'],
            'product_id': item['product_id'],
            'quantity': item['quantity']
        })
    return jsonify({'cart': cart_list})

# Route pour supprimer un article du panier
@app.route('/cart/<int:cart_id>', methods=['DELETE'])
def delete_from_cart(cart_id):
    cur = mysql.connection.cursor()
    query = "DELETE FROM cart WHERE id=%s"
    cur.execute(query, (cart_id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Product removed from cart'})

@app.route('/products/search', methods=['GET'])
def search_products():
    name = request.args.get('name', '')
    cur = mysql.connection.cursor()
    query = "SELECT * FROM products WHERE name LIKE %s"
    cur.execute(query, ('%' + name + '%',))
    products = cur.fetchall()
    cur.close()

    product_list = []
    for product in products:
        product_list.append({
            'id': product['id'],
            'name': product['name'],
            'description': product['description'],
            'price': product['price'],
            'stock': product['stock'],
        })

    return jsonify({'products': product_list})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

