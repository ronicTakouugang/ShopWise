"""Endpoints /lists : listes de produits personnalisées de l'utilisateur."""
from flask import Blueprint, jsonify, request, session

from repositories import lists_repository

lists_bp = Blueprint("lists", __name__)


@lists_bp.route('/lists', methods=['GET'])
def get_lists():
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    try:
        return jsonify(lists_repository.get_lists_by_email(session['email']))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lists_bp.route('/lists', methods=['POST'])
def create_list():
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    name = request.json.get('name')
    try:
        list_id = lists_repository.create_list(email, name)
        return jsonify({"id": list_id, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lists_bp.route('/lists/<int:list_id>/items', methods=['POST'])
def add_to_list(list_id):
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    product_url = request.json.get('productURL')
    try:
        if not lists_repository.list_belongs_to_email(list_id, email):
            return jsonify({"error": "Liste introuvable."}), 404
        lists_repository.add_item_to_list(list_id, product_url)
        return jsonify({"message": "Ajouté à la liste"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
