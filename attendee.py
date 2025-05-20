import gradio as gr
import mysql.connector
import pandas as pd
from datetime import datetime
CURRENT_USER_ID = "U001"

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123456",
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

def get_all_events():
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
            (
                SELECT COUNT(*) 
                FROM HOST 
                WHERE event_id = e.event_id
            ) AS host_count
        FROM EVENTS e
        JOIN DEPARTMENT d ON e.dept = d.dept
        WHERE e.date >= CURDATE()
        ORDER BY e.date, e.time
        """
        
        df = pd.read_sql(query, conn)
        
        if df.empty:
            return pd.DataFrame({"Message": ["No upcoming events found"]})
        
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['time'] = df['time'].astype(str).str.slice(0, 5)
        
        for idx, row in df.iterrows():
            event_id = row['event_id']
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM HOST 
                WHERE event_id = %s AND user_id = %s
            """, (event_id, CURRENT_USER_ID))
            is_registered = cursor.fetchone()[0] > 0
            df.at[idx, 'registered'] = "Yes" if is_registered else "No"
            cursor.close()
        
        display_df = df[['event_id', 'date', 'time', 'dept', 'fee', 'host_count', 'max_capacity', 'registered']]
        display_df.columns = ['Event ID', 'Date', 'Time', 'Department', 'Fee', 'Host Count', 'Max Capacity', 'Registered']
        
        return display_df
    except Exception as e:
        print(f"Error fetching events: {e}")
        return pd.DataFrame({"Error": [str(e)]})
    finally:
        conn.close()

def get_user_events():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame({"Error": ["Database connection failed"]})
    
    try:
        query = """
        SELECT 
            h.event_id,
            e.date, 
            e.time, 
            e.dept,
            d.default_fees AS fee
        FROM HOST h
        JOIN EVENTS e ON h.event_id = e.event_id
        JOIN DEPARTMENT d ON e.dept = d.dept
        WHERE h.user_id = %s
        ORDER BY e.date, e.time
        """
        
        df = pd.read_sql(query, conn, params=(CURRENT_USER_ID,))
        
        if df.empty:
            return pd.DataFrame({"Message": ["You have no registered events"]})
        
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['time'] = df['time'].astype(str).str.slice(0, 5)
        
        now = datetime.now().date()
        df['is_upcoming'] = pd.to_datetime(df['date']) >= pd.to_datetime(now)
        
        display_df = df[['event_id', 'date', 'time', 'dept', 'fee', 'is_upcoming']]
        display_df['Status'] = display_df['is_upcoming'].apply(lambda x: "Upcoming" if x else "Past")
        display_df = display_df.drop(columns=['is_upcoming'])
        display_df.columns = ['Event ID', 'Date', 'Time', 'Department', 'Fee', 'Status']
        
        return display_df
    except Exception as e:
        print(f"Error fetching user events: {e}")
        return pd.DataFrame({"Error": [str(e)]})
    finally:
        conn.close()

def register_for_event(event_id):
    if not event_id:
        return "Please provide an Event ID"
    
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT event_id, date FROM EVENTS WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        if not event:
            return f"Event ID {event_id} not found"
        
        event_id, event_date = event
        if event_date < datetime.now().date():
            return f"Event {event_id} has already passed and cannot be registered for"
        
        cursor.execute("""
            SELECT COUNT(*) FROM HOST 
            WHERE user_id = %s AND event_id = %s
        """, (CURRENT_USER_ID, event_id))
        
        if cursor.fetchone()[0] > 0:
            return f"You are already registered for event {event_id}"
        
        cursor.execute("""
            SELECT 
                d.default_max_capacity,
                (SELECT COUNT(*) FROM HOST WHERE event_id = %s) AS current_hosts
            FROM EVENTS e
            JOIN DEPARTMENT d ON e.dept = d.dept
            WHERE e.event_id = %s
        """, (event_id, event_id))
        
        result = cursor.fetchone()
        if result:
            max_capacity, current_hosts = result
            if current_hosts >= max_capacity:
                return f"Event {event_id} is full, cannot register"
        
        cursor.execute("""
            INSERT INTO HOST (event_id, user_id)
            VALUES (%s, %s)
        """, (event_id, CURRENT_USER_ID))
        
        conn.commit()
        return f"Successfully registered for event {event_id}"
    except mysql.connector.errors.IntegrityError as e:
        if "Duplicate entry" in str(e):
            return f"You are already registered for event {event_id}"
        else:
            return f"Registration error: {e}"
    except Exception as e:
        return f"Error registering for event: {e}"
    finally:
        cursor.close()
        conn.close()

def cancel_registration(event_id):
    if not event_id:
        return "Please provide an Event ID"
    
    conn = get_db_connection()
    if not conn:
        return "Database connection failed"
    
    cursor = conn.cursor()
    try:

        cursor.execute("""
            SELECT h.event_id, e.date
            FROM HOST h
            JOIN EVENTS e ON h.event_id = e.event_id
            WHERE h.event_id = %s AND h.user_id = %s
        """, (event_id, CURRENT_USER_ID))
        
        result = cursor.fetchone()
        if not result:
            return f"You are not registered for event {event_id}"
        
        event_id, event_date = result
        
        current_date = datetime.now().date()
        if event_date < current_date:
            return f"Cannot cancel registration for a past event"
        
        cursor.execute("""
            DELETE FROM HOST
            WHERE event_id = %s AND user_id = %s
        """, (event_id, CURRENT_USER_ID))
        
        conn.commit()
        return f"Successfully cancelled registration for event {event_id}"
    except Exception as e:
        return f"Error cancelling registration: {e}"
    finally:
        cursor.close()
        conn.close()

def create_app():
    with gr.Blocks(title="Attendee Dashboard") as app:
        user_info = get_user_info()
        
        welcome_message = f"Attendee Dashboard"
        if "error" not in user_info:
            welcome_message += f"\n### Welcome, {user_info['user_id']} ({user_info['dept']})"
        else:
            welcome_message += f"\n### User ID: {CURRENT_USER_ID}"
        
        gr.Markdown(welcome_message)
        
        with gr.Tab("View All Events"):
            with gr.Row():
                refresh_events_button = gr.Button("Refresh Events List", variant="secondary")
            
            events_table = gr.DataFrame(label="Available Events")
            
            refresh_events_button.click(
                fn=get_all_events,
                inputs=[],
                outputs=events_table
            )
        
        with gr.Tab("Register for an Event"):
            with gr.Row():
                with gr.Column():
                    register_event_id = gr.Textbox(label="Event ID", placeholder="Enter Event ID (e.g., E101)")
                    register_button = gr.Button("Register for Event", variant="primary")
                    registration_status = gr.Textbox(label="Registration Status", interactive=False)
            
            with gr.Row():
                view_events_button = gr.Button("View Available Events")
                events_for_registration = gr.DataFrame(label="Available Events")
            
            register_button.click(
                fn=register_for_event,
                inputs=register_event_id,
                outputs=registration_status
            )
            
            view_events_button.click(
                fn=get_all_events,
                inputs=[],
                outputs=events_for_registration
            )
        
        with gr.Tab("My Registrations"):
            with gr.Row():
                view_registrations_button = gr.Button("View My Registrations", variant="secondary")
            
            user_registrations = gr.DataFrame(label="Your Registered Events")
            
            with gr.Row():
                with gr.Column():
                    cancel_event_id = gr.Textbox(label="Event ID", placeholder="Enter Event ID to cancel")
                    cancel_button = gr.Button("Cancel Registration", variant="stop")
                    cancellation_status = gr.Textbox(label="Cancellation Status", interactive=False)
            
            view_registrations_button.click(
                fn=get_user_events,
                inputs=[],
                outputs=user_registrations
            )
            
            cancel_button.click(
                fn=cancel_registration,
                inputs=cancel_event_id,
                outputs=cancellation_status
            )
    
        app.load(
            fn=get_all_events,
            inputs=[],
            outputs=events_table
        )
    
        app.load(
            fn=get_user_events,
            inputs=[],
            outputs=user_registrations
        )

    return app

demo = create_app()
if __name__ == "__main__":
    demo.launch(server_port=6003)