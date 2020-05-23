import os

from google.cloud import storage
from googleapiclient.discovery import build

from flask import Flask, jsonify, abort, make_response, request, url_for, Response
from pandas import pandas as pd

from configs import ofacDatasetPath, satDatasetPath, APIKEY, pathToCredentials, bucketName

#TODO Remove unnecesary imports

app = Flask(__name__)

ofac = pd.read_csv(ofacDatasetPath)
ofac = ofac.loc[:, ~ofac.columns.str.contains('^Unnamed')]
sat = pd.read_csv(satDatasetPath)
sat = sat.loc[:, ~sat.columns.str.contains('^Unnamed')]
imgFolder = 'img/app-uploads/'

# Get structure of datasets
@app.route('/riesgo-cognitivo-api/v1.0/datasets/<string:dataset>', methods=['GET'])
def get_dataset(dataset):
    if(dataset == 'ofac'):
        return jsonify(list(ofac.columns))
        #return Response(ofac.head(5).to_json(orient="records"), mimetype='application/json')
    elif(dataset == 'sat'):
        return jsonify(list(sat.columns))
        #return Response(sat.head(5).to_json(orient="records"), mimetype='application/json')
    else:
        abort(404)

#Save image to GCS
@app.route('/riesgo-cognitivo-api/v1.0/upload/img', methods=['POST'])
def upload():
    file = request.files['file']
    filename = file.filename
    file.save(os.path.join('tmp\\img', filename))
    url = upload_file_to_gcs('tmp\\img', filename, filename)
    os.remove(os.path.join('tmp/img', filename))
    return url
    
#Call Google Client API with bucket URI for image

#Call query to search for name on both datasets

# TODO Migrate to Big Query
# Regular expression Functions

def ofac_check(w):
    print (ofac[ofac['SDN_Name'].astype(str).str.contains(w)])

def sat_check(w):
    print (sat[sat['RAZÓN SOCIAL'].astype(str).str.contains(w)])

#Save image to GCS
def upload_file_to_gcs(local_path, local_file_name, target_key):
    try:
        client = storage.Client.from_service_account_json(
            pathToCredentials)
        bucket = client.bucket(bucketName)
        full_file_path = os.path.join(local_path, local_file_name)
        bucket.blob(imgFolder + target_key).upload_from_filename(full_file_path)
        return jsonify({'url': bucket.blob(target_key).public_url , 'uri' : 'gs://' + bucketName + '/' + imgFolder + target_key})

    except Exception as e:
        print(e)
    # TODO Control NONE
    return None

#Deal with error 404
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=True)