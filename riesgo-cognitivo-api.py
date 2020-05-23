from configs import ofacDatasetPath, satDatasetPath
from flask import Flask, jsonify, abort, make_response, request, url_for, Response
from pandas import pandas as pd

#TODO Remove unnecesary imports

app = Flask(__name__)

ofac = pd.read_csv(ofacDatasetPath)
ofac = ofac.loc[:, ~ofac.columns.str.contains('^Unnamed')]
sat = pd.read_csv(satDatasetPath)
sat = sat.loc[:, ~sat.columns.str.contains('^Unnamed')]


@app.route('/todo/api/v1.0/datasets/<string:dataset>', methods=['GET'])
def get_dataset(dataset):
    if(dataset == 'ofac'):
        return jsonify(list(ofac.columns))
        #return Response(ofac.head(5).to_json(orient="records"), mimetype='application/json')
    elif(dataset == 'sat'):
        return jsonify(list(sat.columns))
        #return Response(sat.head(5).to_json(orient="records"), mimetype='application/json')
    else:
        abort(404)

#Deal with error 404
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=True)