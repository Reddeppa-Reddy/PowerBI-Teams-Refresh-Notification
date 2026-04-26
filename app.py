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
        changes = data['changes']
        
        conn = get_connection()
        cursor = conn.cursor()
        
        rows_affected = 0
        for change in changes:
            change_type = change.get('type', 'update')
            
            # Get composite key - structure: {columns: [...], values: {...}}
            composite_key = change.get('compositeKey', {})
            key_values = composite_key.get('values', {})
            
            col = change.get('columnName')
            val = change.get('newValue')
            row_data = change.get('rowData', {})
            
            if change_type == 'update' and col:
                # Validate column name
                if not col.replace('_', '').isalnum():
                    continue
                
                # Build WHERE clause for composite keys
                where_parts = []
                where_values = []
                for pk_col, pk_val in key_values.items():
                    where_parts.append(f"{pk_col} = %s")
                    where_values.append(str(pk_val))  # Convert to string
                
                if not where_parts:
                    continue
                
                where_clause = " AND ".join(where_parts)
                query = f"UPDATE {schema}.{table} SET {col} = %s WHERE {where_clause}"
                cursor.execute(query, [val] + where_values)
                rows_affected += cursor.rowcount
                
            elif change_type == 'insert':
                # Insert new row
                if row_data:
                    columns = list(row_data.keys())
                    values = [str(v) if v is not None else None for v in row_data.values()]
                    placeholders = ", ".join(["%s"] * len(values))
                    col_names = ", ".join(columns)
                    query = f"INSERT INTO {schema}.{table} ({col_names}) VALUES ({placeholders})"
                    cursor.execute(query, values)
                    rows_affected += cursor.rowcount
                
            elif change_type == 'delete':
                # Delete row
                where_parts = []
                where_values = []
                for pk_col, pk_val in key_values.items():
                    where_parts.append(f"{pk_col} = %s")
                    where_values.append(str(pk_val))
                
                if not where_parts:
                    continue
                
                where_clause = " AND ".join(where_parts)
                query = f"DELETE FROM {schema}.{table} WHERE {where_clause}"
                cursor.execute(query, where_values)
                rows_affected += cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "rowsAffected": rows_affected,
            "message": f"Processed {rows_affected} row(s)"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
