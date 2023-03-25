from flask import Flask, jsonify, Response, request, json, abort
from iptc import iptc, Table, Chain
from dotenv import dotenv_values
from functools import wraps
import sys, getopt
import subprocess

app = Flask(__name__)

def require_appkey(view_function):
  @wraps(view_function)
  # the new, post-decoration function. Note *args and **kwargs here.
  def decorated_function(*args, **kwargs):
    with open('api.key', 'r') as apikey:
      key=apikey.read().replace('\n', '')
    #if request.args.get('key') and request.args.get('key') == key:
    if request.headers.get('x-api-key') and request.headers.get('x-api-key') == key:
      return view_function(*args, **kwargs)
    else:
      abort(401)
  return decorated_function

@app.route("/test-connection")
def test_connection():
  return Response(json.dumps({'message': 'Connect successfully'}), status=200, mimetype='application/json')

@app.route("/rules")
@app.route("/rules/<table_name>")
@app.route("/rules/<table_name>/<chain_name>")
@require_appkey
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
@require_appkey
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

@app.route("/rules/flush", methods=['DELETE'])
@app.route("/rules/flush/<table_name>", methods=['DELETE'])
@app.route("/rules/flush/<table_name>/<chain_name>", methods=['DELETE'])
@require_appkey
def flush_rules(table_name = '', chain_name = ''):
  print(table_name, chain_name)
  try:
    if not table_name and not chain_name:
      iptc.easy.flush_all()
      return jsonify(message='Flush all rules successfully')
    if table_name and not chain_name:
      iptc.easy.flush_table(table_name)
      return jsonify(message=f'Flush all rules of table {table_name} successfully')
    if table_name and chain_name:
      iptc.easy.flush_chain(table_name, chain_name)
      return jsonify(message=f'Flush all rules of chain {chain_name} in table {table_name} successfully')  
  except Exception as err:
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')

@app.route("/rules/<table_name>/<chain_name>/<rule_order>", methods=['DELETE'])
@require_appkey
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
@require_appkey
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
@require_appkey
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

@app.route("/chains", methods=['POST'])
@require_appkey
def new_chain():
  try:
    body = request.get_json()
    if not "data" in body:
      raise ValueError('Data object must be specified')
    data = body['data']
    if not "table" in data:
      raise ValueError('Table name must be specified')
    if not "chain" in data:
      raise ValueError('New chain name must be specified')
    table = data['table']
    chain = data['chain']
    iptc.easy.add_chain(table, chain)
    return jsonify(message=f'Create new chain {chain} in table {table} successfully')
  except Exception as err:
    print(err)
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')

@app.route("/chains/zero", methods=['DELETE'])
@app.route("/chains/zero/<table_name>", methods=['DELETE'])
@app.route("/chains/zero/<table_name>/<chain_name>", methods=['DELETE'])
@require_appkey
def zero_chains(table_name = '', chain_name = ''):
  try:
    if not table_name and not chain_name:
      tables = iptc.easy.get_tables()
      if not tables or len(tables) == 0:
        return Response(json.dumps({'message': 'Empty tables'}), status=500, mimetype='application/json')
      print(tables)
      for _table in tables:
        print(_table)
        table = iptc.easy._iptc_gettable(_table)
        if not table:
          continue
        chains = table._get_chains()
        if not chains or len(chains) == 0:
          return Response(json.dumps({'message': f'Empty chains in table {_table}'}), status=500, mimetype='application/json')
        for chain in chains:
          chain.zero_counters()
      return jsonify(message='Zero all chains successfully')

    if table_name and not chain_name:
      table = iptc.easy._iptc_gettable(table_name)
      if not table:
        return Response(json.dumps({'message': f'Table {table_name} doesn\'t exist'}), status=500, mimetype='application/json')
      chains = table._get_chains()
      if not chains or len(chains) == 0:
        return Response(json.dumps({'message': f'Empty chains in table {_table}'}), status=500, mimetype='application/json')
      for chain in chains:
        chain.zero_counters()
      return jsonify(message=f'Zero all chains of table {table_name} successfully')

    if table_name and chain_name:
      print('call here', chain_name)
      table = iptc.easy._iptc_gettable(table_name)
      if not table:
        return Response(json.dumps({'message': f'Table {table_name} doesn\'t exist'}), status=500, mimetype='application/json')
      chain = iptc.easy._iptc_getchain(table_name, chain_name)
      if not chain:
        return Response(json.dumps({'message': f'Chain {chain_name} in table {_table} doesn\'t exist'}), status=500, mimetype='application/json')
      # chain.zero_counters()
      table.zero_entries(chain_name)
      # iptc.easy.zero_chain(table_name, chain_name)
      return jsonify(message=f'Zero chain {chain_name} in table {table_name} successfully')  
  except Exception as err:
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')


@app.route("/chains/<table_name>/<chain_name>", methods=['DELETE'])
@require_appkey
def delete_chain(table_name, chain_name):
  try:
    if not table_name:
      raise ValueError('Table name must be specified')
    if not chain_name:
      raise ValueError('Chain name must be specified')
    args = request.args
    is_flush = args.get('is_flush')
    iptc.easy.delete_chain(table_name, chain_name, False, is_flush)
    return jsonify(message=f'Delete chain {chain_name} on table {table_name} succesfully')
  except Exception as err:
    return Response(json.dumps({'message': str(err)}), status=500, mimetype='application/json')

@app.route("/dump-rules")
@require_appkey
def dump_rules():
  # version_info = sys.version_info
  # f = open("./test.txt", "w")
  # output = None
  # if version_info[0] < 3 or (version_info[0] == 3 and version_info[1] <= 4):
  #   subprocess.call(["sudo", "iptables-save"], stdout=f)
  # else:
  #   subprocess.run(["sudo", "iptables-save"], stdout=f)
  args = request.args
  print(args)
  cmd = "sudo iptables-save"
  if args.get('keep_track'):
    cmd += ' -c'
  if args.get('table') is not None:
    cmd += ' -t ' + args.get('table')
  output = subprocess.check_output(cmd, shell=True)
  output = output.decode('utf-8')
  # print(output)
  return jsonify(data=output)

@app.route('/import-rules', methods=['PUT'])
@require_appkey
def import_rules():
  arrCmd = ["sudo", "iptables-restore", "./rules-import.txt"]
  body = request.get_json()
  data = body['data']
  if not data or len(data) == 0:
    return Response(json.dumps({'message': 'Invalid rules data'}), status=500, mimetype='application/json')
  # f = open('./rules-import.txt', 'w')
  # f.write(data)
  if 'table' in body:
    arrCmd.append("-T")
    arrCmd.append(body['table'])
  if 'counters' in body and body['counters']:
    arrCmd.append('-c')
  if 'noflush' in body and body['noflush']:
    arrCmd.append('-n')
  print(arrCmd)
  version_info = sys.version_info
  try:
    if version_info[0] < 3 or (version_info[0] == 3 and version_info[1] <= 4):
      subprocess.call(arrCmd)
    else:
      subprocess.run(arrCmd)
  except Exception as ex:
    print(ex)
  return jsonify(data="Import rule successfully")

if __name__ == '__main__':
    config = dotenv_values(".env")
    host = config.get('HOST', 'localhost')
    port = config.get('PORT', 5001)
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