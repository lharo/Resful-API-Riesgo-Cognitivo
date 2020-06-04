import os
import base64
import json

from google.cloud import storage
from googleapiclient.discovery import build

from flask import Flask, jsonify, abort, make_response, request, url_for, Response, redirect
from pandas import pandas as pd

from configs import ofacDatasetPath, satDatasetPath, APIKEY, pathToCredentials, bucketName

#TODO Remove unnecesary imports

app = Flask(__name__, static_folder="dist/angular-blog-clean", static_url_path="")

ofac = pd.read_csv(ofacDatasetPath)
ofac = ofac.loc[:, ~ofac.columns.str.contains('^Unnamed')]
sat = pd.read_csv(satDatasetPath)
sat = sat.loc[:, ~sat.columns.str.contains('^Unnamed')]
sat.rename(columns={'RAZÓN SOCIAL': 'Razon_Social'}, inplace=True)

imgFolder = 'img/app-uploads/'

@app.route("/")
def home():
 return make_response(open('dist/angular-blog-clean/index.html').read())

@app.route("/home")
def homeroot():
 return redirect("/")

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
@app.route('/riesgo-cognitivo-api/v1.0/identify-image/<string:uri>', methods=['GET'])
def identify_image(uri):
    IMAGE = 'gs://' + bucketName + '/' + imgFolder + uri
    vservice = build('vision', 'v1', developerKey=APIKEY)
    request = vservice.images().annotate(body={
        'requests': [{
        'image': {
            'source': {
                'gcs_image_uri': IMAGE
            }
        },
        'features': [{
            'type': 'TEXT_DETECTION',
            'maxResults': 3,
            }]
        }],
    })
    responses = request.execute(num_retries=3)
    try:
        api_text = (responses['responses'][0]['textAnnotations'][0]['description'])
        start = api_text.find("NOMBRE") + len("NOMBRE")
        end = api_text.find("DOMICILIO")
        name = api_text[start:end]
        name = name.replace("\n", " ")
        """
        api_array = api_text.splitlines()
        name_like_variable = difflib.get_close_matches('NOMBRE', api_array)
        address_like_variable = difflib.get_close_matches('DOMICILIO', api_array)
        name_like_variable_idx = api_array.index(''.join(name_like_variable))
        address_like_variable_idx = api_array.index(''.join(address_like_variable))

        name = ''
        i = name_like_variable_idx + 1
        while i < address_like_variable_idx:
            name += api_array[i] + " "
            i += 1
        """
        return jsonify({'name': name}, {'error':False})
    except Exception as e:
    # TODO Control Messaging for errors
        return jsonify({'error':True, 'uri': IMAGE,'message': responses['responses'][0]['textAnnotations'][0]})

#Call query to search for name on both datasets
#TODO Migrate to Big Query
# Regular expression Functions
#On client side use %20
@app.route('/riesgo-cognitivo-api/v1.0/check-ofac/<string:name>', methods=['GET'])
def check_ofac(name):
    df = ofac[ofac.SDN_Name == name]
    res = df.to_dict(orient='records')
    return json.dumps(res)

#On client side use %20
@app.route('/riesgo-cognitivo-api/v1.0/check-sat/<string:name>', methods=['GET'])
def check_sat(name):
    df = sat[sat.Razon_Social == name]
    res = df.to_dict(orient='records')
    return json.dumps(res)
    
#Save image to GCS
def upload_file_to_gcs(local_path, local_file_name, target_key):
    try:
        client = storage.Client.from_service_account_json(
            pathToCredentials)
        bucket = client.bucket(bucketName)
        full_file_path = os.path.join(local_path, local_file_name)
        blob = bucket.blob(imgFolder + target_key)
        blob.upload_from_filename(full_file_path)
        blob.make_public()
        return jsonify({'url': bucket.blob(target_key).public_url , 'uri' : 'gs://' + bucketName + '/' + imgFolder + target_key , 'imgName' : target_key })

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