from flask import Flask, jsonify, url_for, redirect, request, Response, send_from_directory
from flask_pymongo import PyMongo
from flask_restful import Api, Resource
import uuid
import json
import bson
from bson import json_util
from bson.json_util import dumps
from bson.objectid import ObjectId
import os

app = Flask(__name__)

def default_config():
    app.config["MONGO_DBNAME"] = "albums_db"


if os.getenv('VCAP_SERVICES'):
    try:
        services = os.getenv('VCAP_SERVICES')
        services_json = json.loads(services)
        mongodb_uri = services_json['MongoDB'][0]['credentials']['uri']
        app.config["MONGO_URI"] = mongodb_uri
    except Exception as e:
        default_config()
else:
    default_config()

mongo = PyMongo(app)

services = os.getenv('VCAP_SERVICES')

@app.before_first_request
def populate_collection() :
    if mongo.db.album:
        cursor = mongo.db.album.find({})
        if cursor.count() > 0:
            return
    with open("albums.json", "r") as f:
        albums = json.load(f)
    for a in albums:
        mongo.db.album.insert(a)

@app.route('/<path:path>')
def send_static(path):
    if 'appinfo' == path or 'appinfo/' == path:
        return send_from_directory('static', path, mimetype='application/json')
    return send_from_directory('static', path)

class Album(Resource):
    def get(self, id=None):
        data = []
        if id:
            album_info = mongo.db.album.find_one({"_id": ObjectId(id)})
            if album_info:
                album_info['id'] = album_info['_id']['$oid']
                return Response(dumps(album_info, default=json_util.default),
                mimetype='application/json')
            else:
                return jsonify({"response": "no album found for {}".format(id)})

        else:
            cursor = mongo.db.album.find({})
            #angular !hearts mongo
            data = [self.fix_id(a) for a in list(cursor)]
            return Response(dumps(data, default=json_util.default),
                mimetype='application/json')

    def fix_id(self, a):
        if a and a['_id']:
            a['id'] = str(a['_id'])
        return a

    def post(self):
        data = request.get_json()
        data.pop('_id', None)
        if 'id' in data:
            mongo.db.album.update({"_id" : ObjectId(data["id"])}, data)
        else:
            mongo.db.album.insert(data)
        return Response(dumps(data, default=json_util.default),
                mimetype='application/json')

    def put(self):
        return self.post()

    def delete(self, id):
        ret = mongo.db.album.remove({'_id': ObjectId(id)})
        print(ret)
        return jsonify({"response": "deleted album {}".format(id)})


class Index(Resource):
    def get(self):
        return app.send_static_file("index.html")


api = Api(app)
api.add_resource(Index, "/")
api.add_resource(Album, "/albums", endpoint="albums")
api.add_resource(Album, "/albums/<string:id>")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9099))
    app.run(debug=True, host='0.0.0.0', port=port)