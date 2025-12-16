from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'event-scheduler-key-2025'

def get_db_connection():
    """Get database connection using environment variables"""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

def check_conflict(event_id, resource_id, start_time, end_time):
    """Check if resource is already booked during event time"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check for overlapping events with same resource
    cursor.execute("""
        SELECT 1 FROM event_resource_allocation era
        JOIN events e ON era.event_id = e.event_id
        WHERE era.resource_id = %s AND e.event_id != %s
        AND ((e.start_time < %s AND e.end_time > %s) OR
             (e.start_time < %s AND e.end_time > %s) OR
             (%s < e.start_time AND %s > e.end_time))
    """, (resource_id, event_id, end_time, start_time, end_time, start_time, start_time, end_time))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

@app.route('/')
def index():
    """Homepage with recent events"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.*, GROUP_CONCAT(r.resource_name) as resources
        FROM events e 
        LEFT JOIN event_resource_allocation era ON e.event_id = era.event_id
        LEFT JOIN resources r ON era.resource_id = r.resource_id
        GROUP BY e.event_id 
        ORDER BY e.start_time DESC LIMIT 5
    """)
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', events=events)

@app.route('/events')
def events():
    """List all events"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.*, GROUP_CONCAT(r.resource_name) as resources
        FROM events e 
        LEFT JOIN event_resource_allocation era ON e.event_id = era.event_id
        LEFT JOIN resources r ON era.resource_id = r.resource_id
        GROUP BY e.event_id 
        ORDER BY e.start_time DESC
    """)
    events_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('events.html', events=events_list)

@app.route('/events/new', methods=['GET', 'POST'])
def new_event():
    """Add new event"""
    if request.method == 'POST':
        title = request.form['title']
        start_time = request.form['start_time'] + ':00'
        end_time = request.form['end_time'] + ':00'
        description = request.form.get('description', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, start_time, end_time, description) 
            VALUES (%s, %s, %s, %s)
        """, (title, start_time, end_time, description))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Event created successfully!')
        return redirect(url_for('events'))
    
    return render_template('event_form.html')

@app.route('/events/<int:event_id>/delete', methods=['POST'])
def delete_event(event_id):
    """Delete event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE event_id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Event deleted successfully!')
    return redirect(url_for('events'))

@app.route('/resources')
def resources():
    """List all resources"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM resources ORDER BY resource_type, resource_name")
    resources_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('resources.html', resources=resources_list)

@app.route('/resources/new', methods=['GET', 'POST'])
def new_resource():
    """Add new resource"""
    if request.method == 'POST':
        resource_name = request.form['resource_name']
        resource_type = request.form['resource_type']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resources (resource_name, resource_type) 
            VALUES (%s, %s)
        """, (resource_name, resource_type))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Resource added successfully!')
        return redirect(url_for('resources'))
    
    return render_template('resource_form.html')

@app.route('/resources/<int:resource_id>/delete', methods=['POST'])
def delete_resource(resource_id):
    """Delete resource"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resources WHERE resource_id = %s", (resource_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Resource deleted successfully!')
    return redirect(url_for('resources'))

@app.route('/events/<int:event_id>/allocate', methods=['GET', 'POST'])
def allocate(event_id):
    """Allocate resources to event with conflict checking"""
    # Get event details
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE event_id = %s", (event_id,))
    event = cursor.fetchone()
    
    if not event:
        flash('Event not found. Create events first.', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('events'))
    
    # Get all resources
    cursor.execute("""
        SELECT r.*, 
               CASE WHEN era.resource_id IS NOT NULL THEN 'Yes' ELSE 'No' END as is_allocated
        FROM resources r 
        LEFT JOIN event_resource_allocation era ON r.resource_id = era.resource_id AND era.event_id = %s
        ORDER BY r.resource_type, r.resource_name
    """, (event_id,))
    resources_list = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if request.method == 'POST':
        # SAFE: Check if resource_id exists in form
        resource_id = request.form.get('resource_id')
        
        if not resource_id:
            flash('ERROR: Please select a resource!', 'error')
        else:
            resource_id = int(resource_id)
            
            # Check for time conflicts
            if check_conflict(event_id, resource_id, event['start_time'], event['end_time']):
                flash('ERROR: Resource already booked during this time!', 'error')
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO event_resource_allocation (event_id, resource_id) 
                    VALUES (%s, %s)
                """, (event_id, resource_id))
                conn.commit()
                cursor.close()
                conn.close()
                flash('✅ Resource allocated successfully!')
        
        # Reload page to show updated status
        return redirect(url_for('allocate', event_id=event_id))
    
    return render_template('allocate.html', event=event, resources=resources_list)

@app.route('/report', methods=['GET', 'POST'])
def report():
    """Resource utilization report"""
    report_data = []
    
    if request.method == 'POST':
        start_date = request.form['start_date'] + ':00'
        end_date = request.form['end_date'] + ':00'
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.resource_name, r.resource_type,
                   COUNT(era.allocation_id) as bookings,
                   SEC_TO_TIME(SUM(TIMESTAMPDIFF(SECOND, e.start_time, e.end_time))) as total_hours
            FROM resources r 
            LEFT JOIN event_resource_allocation era ON r.resource_id = era.resource_id
            LEFT JOIN events e ON era.event_id = e.event_id
            WHERE e.start_time >= %s AND e.end_time <= %s
            GROUP BY r.resource_id 
            ORDER BY total_hours DESC
        """, (start_date, end_date))
        report_data = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('report.html', resources=report_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
