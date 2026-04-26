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
        # Support both single and multiple primary key columns
        pk_columns = data.get('primaryKeyColumns') or [data.get('primaryKeyColumn')]
        changes = data['changes']
        
        conn = get_connection()
        cursor = conn.cursor()
        
        rows_affected = 0
        for change in changes:
            change_type = change.get('type', 'update')
            
            # Get primary key value(s) - support both formats
            composite_key = change.get('compositeKey') or {pk_columns[0]: change.get('primaryKey')}
            
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
                for pk_col, pk_val in composite_key.items():
                    where_parts.append(f"{pk_col} = %s")
                    where_values.append(pk_val)
                
                where_clause = " AND ".join(where_parts)
                query = f"UPDATE {schema}.{table} SET {col} = %s WHERE {where_clause}"
                cursor.execute(query, [val] + where_values)
                rows_affected += cursor.rowcount
                
            elif change_type == 'insert':
                # Insert new row
                columns = list(row_data.keys())
                values = list(row_data.values())
                placeholders = ", ".join(["%s"] * len(values))
                col_names = ", ".join(columns)
                query = f"INSERT INTO {schema}.{table} ({col_names}) VALUES ({placeholders})"
                cursor.execute(query, values)
                rows_affected += cursor.rowcount
                
            elif change_type == 'delete':
                # Delete row
                where_parts = []
                where_values = []
                for pk_col, pk_val in composite_key.items():
                    where_parts.append(f"{pk_col} = %s")
                    where_values.append(pk_val)
                
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
