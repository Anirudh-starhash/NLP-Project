from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from application.database import db



chat_blueprint = Blueprint("chat", __name__)
@chat_blueprint.route("/prepare_document",methods=['POST'])
def prepare_document():
    pass