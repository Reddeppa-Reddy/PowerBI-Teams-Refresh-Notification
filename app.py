from flask import Flask, request, jsonify
from flask_cors import CORS
import snowflake.connector
import json

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

@app.route('/debug', methods=['POST', 'OPTIONS'])
def debug():
    """Debug endpoint to see what data is being sent"""
    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json()
    return jsonify({"received": data})

@app.route('/writeback', methods=['POST', 'OPTIONS'])
def writeback():
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        schema = data.get('schema', 'PUBLIC')
        table = data.get('table')
        
        if not table:
            return jsonify({"success": False, "message": "Table name is required"}), 400
        
        changes = data.get('changes', [])
        
        if not changes:
            return jsonify({"success": True, "rowsAffected": 0, "message": "No changes to process"})
        
        conn = get_connection()
        cursor = conn.cursor()
        
        rows_affected = 0
        errors = []
        
        for i, change in enumerate(changes):
            try:
                change_type = change.get('type', 'update')
                
                # Get composite key - structure: {columns: [...], values: {...}}
                composite_key = change.get('compositeKey', {})
                key_columns = composite_key.get('columns', [])
                key_values = composite_key.get('values', {})
                
                col = change.get('columnName')
                val = change.get('newValue')
                row_data = change.get('rowData', {})
                
                # Build WHERE clause
                where_parts = []
                where_params = []
                
                for pk_col in key_columns:
                    pk_val = key_values.get(pk_col)
                    if pk_val is not None:
                        where_parts.append(f'"{pk_col}" = %s')
                        # Convert value to appropriate type
                        if isinstance(pk_val, (int, float)):
                            where_params.append(pk_val)
                        else:
                            where_params.append(str(pk_val))
                
                if change_type == 'update' and col:
                    if not where_parts:
                        errors.append(f"Change {i}: No primary key values for update")
                        continue
                    
                    where_clause = " AND ".join(where_parts)
                    
                    # Handle value type
                    if val is None:
                        query = f'UPDATE "{schema}"."{table}" SET "{col}" = NULL WHERE {where_clause}'
                        cursor.execute(query, where_params)
                    else:
                        query = f'UPDATE "{schema}"."{table}" SET "{col}" = %s WHERE {where_clause}'
                        cursor.execute(query, [val] + where_params)
                    
                    rows_affected += cursor.rowcount
                    
                elif change_type == 'insert':
                    if row_data:
                        columns = []
                        values = []
                        for c, v in row_data.items():
                            columns.append(f'"{c}"')
                            values.append(v)
                        
                        placeholders = ", ".join(["%s"] * len(values))
                        col_names = ", ".join(columns)
                        query = f'INSERT INTO "{schema}"."{table}" ({col_names}) VALUES ({placeholders})'
                        cursor.execute(query, values)
                        rows_affected += cursor.rowcount
                    
                elif change_type == 'delete':
                    if not where_parts:
                        errors.append(f"Change {i}: No primary key values for delete")
                        continue
                    
                    where_clause = " AND ".join(where_parts)
                    query = f'DELETE FROM "{schema}"."{table}" WHERE {where_clause}'
                    cursor.execute(query, where_params)
                    rows_affected += cursor.rowcount
                    
            except Exception as e:
                errors.append(f"Change {i}: {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        result = {
            "success": True,
            "rowsAffected": rows_affected,
            "message": f"Processed {rows_affected} row(s)"
        }
        
        if errors:
            result["warnings"] = errors
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
