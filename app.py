from flask import Flask, jsonify, Response, request, json
from iptc import iptc
from dotenv import dotenv_values
import sys, getopt

app = Flask(__name__)

@app.route("/test-connection")
def test_connection():
  return Response(json.dumps({'message': 'Connect successfully'}), status=200, mimetype='application/json')

@app.route("/rules")
@app.route("/rules/<table_name>")
@app.route("/rules/<table_name>/<chain_name>")
def list_rule(table_name='all', chain_name='all'):
  try:
    if table_name == 'all':
      return jsonify(iptc.easy.dump_all())
    if chain_name == 'all':
      return jsonify(iptc.easy.dump_table(table_name))
    return jsonify(iptc.easy.dump_chain(table_name, chain_name))
  except Exception as err:
    print(err)
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json') 

@app.route("/rules/<table_name>", methods=['POST'])
@app.route("/rules/<table_name>/<chain_name>", methods=['POST'])
def bulk_add_rule(table_name='filter', chain_name=''):
  print(chain_name)
  if not chain_name:
    return Response("{'message': 'Not found chain'}", status=500, mimetype='application/json')
  try:
    body = request.get_json()
    data = body['data']
    position = 0
    if "order" in body:
      position = int(body["order"])
    print(data)
    for i in range(len(data)):
      if not data[i]:
        return Response("{'message': 'Empty rule'}", status=500, mimetype='application/json') 
      iptc.easy.add_rule(table_name, chain_name, data[i], position)
    return jsonify(message='Hello')
  except ValueError as err:
    print(err)
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json') 

@app.route("/rules/<table_name>/<chain_name>/<rule_order>", methods=['DELETE'])
def delete_rule(table_name='filter', chain_name='', rule_order='1'):
  if not chain_name:
    return Response("{'message': 'Not found chain'}", status=500, mimetype='application/json')
  try:
    rule_d = iptc.easy.get_rule(table_name, chain_name, int(rule_order))
    iptc.easy.delete_rule(table_name, chain_name, rule_d)
    return jsonify(message="Delete rule sucessfully")
  except ValueError as err:
    print(err)
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')

@app.route('/policy/<table_name>/<chain_name>')
def get_policy(table_name='filter', chain_name=''):
  if not chain_name:
    return Response("{'message': 'Not found chain'}", status=500, mimetype='application/json')
  try:
    policy = iptc.easy.get_policy(table_name, chain_name)
    return jsonify(policy=policy)
  except ValueError as err:
    print(err)
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')

@app.route('/policy/<table_name>/<chain_name>', methods=['PUT'])
def update_pocily(table_name='filter', chain_name=''):
  if not chain_name:
    return Response("{'message': 'Not found chain'}", status=500, mimetype='application/json')
  try:
    body = request.get_json()
    print(table_name, chain_name, body)
    new_policy = body['policy']
    iptc.easy.set_policy(table_name, chain_name, new_policy)
    return jsonify(message="Update policy sucessfully")
  except ValueError as err:
    print(err)
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')

if __name__ == '__main__':
    config = dotenv_values(".env")
    host = config.get('HOST', 'localhost')
    port = config.get('PORT', 8001)
    argv = sys.argv[1:]
    if len(argv) > 0:
      try:
        opts, args = getopt.getopt(argv,"h:p:",["host=","port="])
      except getopt.GetoptError:
        print('Error when loading arguments')
      for opt, arg in opts:
        if opt in ("-h", "--host"):
          host = arg
        elif opt in ("-p", "--port"):
          port = arg
    print(f'Agent will run on {host}:{port}')
    app.run(host=host, port=port, debug=True)