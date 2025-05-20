import gradio as gr
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
CURRENT_USER_ID = "U002"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1029384756",
            database="EventManagementSystem"
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_user_info():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
        SELECT u.user_id, u.dept, u.no_of_events, l.account_type
        FROM USERS u
        JOIN LOGIN l ON u.user_id = l.user_id
        WHERE u.user_id = %s
        """, (CURRENT_USER_ID,))
        
        user = cursor.fetchone()
        if not user:
            return {"error": f"User {CURRENT_USER_ID} not found"}
        return user
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        conn.close()

def get_departments():
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dept FROM DEPARTMENT ORDER BY dept")
        departments = [dept[0] for dept in cursor.fetchall()]
        return departments
    except Exception as e:
        print(f"Error fetching departments: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_user_department():
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dept FROM USERS WHERE user_id = %s", (CURRENT_USER_ID,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        print(f"Error fetching user department: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_hosted_events():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame({"Error": ["Database connection failed"]})
    
    try:
        query = """
        SELECT 
            e.event_id, 
            e.date, 
            e.time, 
            e.dept,
            d.default_fees AS fee,
            d.default_max_capacity AS max_capacity,
            (SELECT COUNT(*) FROM HOST WHERE event_id = e.event_id) AS registration_count
        FROM EVENTS e
        JOIN DEPARTMENT d ON e.dept = d.dept
        JOIN HOST h ON e.event_id = h.event_id
        WHERE h.user_id = %s
        GROUP BY e.event_id
        ORDER BY e.date, e.time
        """
        
        df = pd.read_sql(query, conn, params=(CURRENT_USER_ID,))
        
        if df.empty:
            return pd.DataFrame({"Message": ["You haven't created any events yet"]})
        
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['time'] = df['time'].astype(str).str.slice(0, 5)
        
        now = datetime.now().date()
        df['status'] = df.apply(
            lambda row: "Upcoming" if pd.to_datetime(row['date']).date() >= now else "Past", 
            axis=1
        )
        
        df['availability'] = df.apply(
            lambda row: f"{int((row['max_capacity'] - row['registration_count']) / row['max_capacity'] * 100)}%" 
            if row['max_capacity'] > 0 else "N/A", 
            axis=1
        )
        
        display_df = df[['event_id', 'date', 'time', 'dept', 'fee', 'registration_count', 'max_capacity', 'availability', 'status']]
        display_df.columns = ['Event ID', 'Date', 'Time', 'Department', 'Fee', 'Registrations', 'Max Capacity', 'Availability', 'Status']
        
        return display_df
    except Exception as e:
        print(f"Error fetching hosted events: {e}")
        return pd.DataFrame({"Error": [str(e)]})
    finally:
        conn.close()

def get_event_registrations(event_id):
    if not event_id:
        return pd.DataFrame({"Message": ["Please provide an Event ID"]})
    
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame({"Error": ["Database connection failed"]})
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM HOST 
            WHERE event_id = %s AND user_id = %s
        """, (event_id, CURRENT_USER_ID))
        
        if cursor.fetchone()[0] == 0:
            return pd.DataFrame({"Error": ["You are not authorized to view registrations for this event"]})
        
        query = """
        SELECT 
            h.user_id,
            u.dept AS user_dept
        FROM HOST h
        JOIN USERS u ON h.user_id = u.user_id
        WHERE h.event_id = %s
        ORDER BY h.user_id
        """
        
        df = pd.read_sql(query, conn, params=(event_id,))
        
        if df.empty:
            return pd.DataFrame({"Message": [f"No registrations yet for event {event_id}"]})
        
        display_df = df[['user_id', 'user_dept']]
        display_df.columns = ['User ID', 'Department']
        
        return display_df
    except Exception as e:
        print(f"Error fetching event registrations: {e}")
        return pd.DataFrame({"Error": [str(e)]})
    finally:
        conn.close()

def create_event(event_id, date, time, department):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
    
    if not event_id or not date or not time or not department:
        return "All fields are required"
    
    if not event_id.startswith('E') or len(event_id) != 4:
        return "Event ID must be in format E### (e.g., E101)"
    
    try:
        event_date = datetime.strptime(date, "%Y-%m-%d").date()
        if event_date < datetime.now().date():
            return "Event date must be in the future"
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD"
    
    try:
        event_time = datetime.strptime(time, "%H:%M").time()
    except ValueError:
        return "Invalid time format. Use HH:MM (24-hour format)"
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM EVENTS WHERE event_id = %s", (event_id,))
        if cursor.fetchone()[0] > 0:
            return f"Event ID {event_id} already exists"
        
        cursor.execute("SELECT COUNT(*) FROM DEPARTMENT WHERE dept = %s", (department,))
        if cursor.fetchone()[0] == 0:
            return f"Department {department} does not exist"
        
        cursor.execute("""
            INSERT INTO EVENTS (event_id, date, time, dept)
            VALUES (%s, %s, %s, %s)
        """, (event_id, event_date, event_time, department))
        
        cursor.execute("""
            INSERT INTO HOST (event_id, user_id)
            VALUES (%s, %s)
        """, (event_id, CURRENT_USER_ID))
        
        conn.commit()
        return f"Successfully created event {event_id}"
    except Exception as e:
        conn.rollback()
        return f"Error creating event: {e}"
    finally:
        cursor.close()
        conn.close()

def get_event_details(event_id):
    if not event_id:
        return {"Message": "Please provide an Event ID"}
    
    conn = get_db_connection()
    if not conn:
        return {"Error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                e.event_id, 
                e.date, 
                e.time, 
                e.dept,
                d.default_fees,
                d.default_max_capacity,
                (SELECT COUNT(*) FROM HOST WHERE event_id = e.event_id) AS registration_count
            FROM EVENTS e
            JOIN DEPARTMENT d ON e.dept = d.dept
            WHERE e.event_id = %s
        """, (event_id,))
        
        event = cursor.fetchone()
        if not event:
            return {"Error": f"Event {event_id} not found"}
        
        event['date'] = event['date'].strftime('%Y-%m-%d')
        event['time'] = event['time'].strftime('%H:%M')
        
        cursor.execute("""
            SELECT COUNT(*) FROM HOST 
            WHERE event_id = %s AND user_id = %s
        """, (event_id, CURRENT_USER_ID))
        
        is_host = cursor.fetchone()[0] > 0
        event['is_host'] = is_host
        
        return event
    except Exception as e:
        print(f"Error fetching event details: {e}")
        return {"Error": str(e)}
    finally:
        cursor.close()
        conn.close()

def validate_host():
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT account_type 
            FROM LOGIN 
            WHERE user_id = %s
        """, (CURRENT_USER_ID,))
        
        result = cursor.fetchone()
        if not result:
            return False, f"User {CURRENT_USER_ID} not found"
        
        account_type = result[0]
        if account_type != 'admin' and account_type != 'host':
            return False, f"User {CURRENT_USER_ID} doesn't have host privileges"
            
        return True, "Valid host account"
    except Exception as e:
        return False, f"Error validating host: {e}"
    finally:
        cursor.close()
        conn.close()

def create_app():
    is_host, message = validate_host()
    if not is_host:
        with gr.Blocks(title="Host Dashboard") as app:
            gr.Markdown("# 🚫 Access Denied")
            gr.Markdown(f"**{message}**")
            gr.Markdown("You need host privileges to access this dashboard.")
        return app
    
    user_info = get_user_info()
    user_department = get_user_department()
    
    with gr.Blocks(title="Host Dashboard") as app:
        welcome_message = f"# 🎪 Host Dashboard"
        if "error" not in user_info:
            welcome_message += f"\n### Welcome, {user_info['user_id']} ({user_info['dept']})"
            welcome_message += f"\n#### You have hosted {user_info['no_of_events']} events"
        else:
            welcome_message += f"\n### User ID: {CURRENT_USER_ID}"
        
        gr.Markdown(welcome_message)
        
        with gr.Tab("My Hosted Events"):
            with gr.Row():
                refresh_events_button = gr.Button("Refresh Events List", variant="secondary")
            
            hosted_events_table = gr.DataFrame(label="Events You've Hosted")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### View Registrations")
                    event_id_input = gr.Textbox(label="Event ID", placeholder="Enter Event ID to view registrations")
                    view_registrations_button = gr.Button("View Registrations", variant="primary")
                
                with gr.Column(scale=2):
                    registrations_table = gr.DataFrame(label="Event Registrations")
            
            refresh_events_button.click(
                fn=get_hosted_events,
                inputs=[],
                outputs=hosted_events_table
            )
            
            view_registrations_button.click(
                fn=get_event_registrations,
                inputs=event_id_input,
                outputs=registrations_table
            )
        
        with gr.Tab("Create New Event"):
            with gr.Row():
                with gr.Column():
                    new_event_id = gr.Textbox(label="Event ID", placeholder="Enter Event ID (e.g., E104)")
                    
                    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                    new_event_date = gr.Textbox(label="Event Date", placeholder="YYYY-MM-DD", value=tomorrow)
                    
                    new_event_time = gr.Textbox(label="Event Time", placeholder="HH:MM (24-hour)", value="12:00")
                    
                    departments = get_departments()
                    new_event_dept = gr.Dropdown(label="Department", choices=departments, value=user_department if user_department else departments[0] if departments else None)
                    
                    create_event_button = gr.Button("Create Event", variant="primary")
                    create_event_status = gr.Textbox(label="Status", interactive=False)
            
            with gr.Row():
                gr.Markdown("""
                ### Event Creation Guidelines
                - Event ID must be in format E### (e.g., E101)
                - Event Date must be in the future
                - Event Time must be in 24-hour format (HH:MM)
                - Department must be selected from the dropdown
                """)
            
            create_event_button.click(
                fn=create_event,
                inputs=[new_event_id, new_event_date, new_event_time, new_event_dept],
                outputs=create_event_status
            )
        
        with gr.Tab("Event Details"):
            with gr.Row():
                with gr.Column(scale=1):
                    detail_event_id = gr.Textbox(label="Event ID", placeholder="Enter Event ID to view details")
                    detail_button = gr.Button("View Details", variant="secondary")
                
                with gr.Column(scale=2):
                    event_details = gr.JSON(label="Event Details")
            
            detail_button.click(
                fn=get_event_details,
                inputs=detail_event_id,
                outputs=event_details
            )
    
        app.load(
            fn=get_hosted_events,
            inputs=[],
            outputs=hosted_events_table
        )
    
    return app

demo = create_app()
if __name__ == "__main__":
    demo.launch(server_port=6002)