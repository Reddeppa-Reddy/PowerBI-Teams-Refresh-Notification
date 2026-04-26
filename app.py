from flask import Flask, request, jsonify
from flask_cors import CORS
import snowflake.connector

app = Flask(__name__)
CORS(app)

# Snowflake credentials
SNOWFLAKE_CONFIG = {
    "account": "pcxtnvv-ty06666",
    "user": "REDDEPAAREDDY117A",
    "password": "8686808462aA#aA",
    "warehouse": "COMPUTER_WH",
    "database": "WRITEBACK",
    "role": "ACCOUNTADMIN"
}

def get_connection():
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)

@app.route('/')
def home():
    return jsonify({"status": "healthy", "service": "Snowflake Write-back API"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/writeback', methods=['POST', 'OPTIONS'])
def writeback():
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        schema = data.get('schema', 'PUBLIC')
        table = data['table']
        pk_column = data['primaryKeyColumn']
        changes = data['changes']
        
        conn = get_connection()
        cursor = conn.cursor()
        
        rows_affected = 0
        for change in changes:
            pk = change['primaryKey']
            col = change['columnName']
            val = change['newValue']
            
            if not col.replace('_', '').isalnum():
                continue
            
            query = f"UPDATE {schema}.{table} SET {col} = %s WHERE {pk_column} = %s"
            cursor.execute(query, (val, pk))
            rows_affected += cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "rowsAffected": rows_affected,
            "message": f"Updated {rows_affected} row(s)"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
