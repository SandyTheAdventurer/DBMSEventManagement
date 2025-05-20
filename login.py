import gradio as gr
import mysql.connector as sqltor
from host import get_db_connection

conn = get_db_connection()
def login_fn(username, passwd, type):
    cursor = conn.cursor(dictionary= True)
    cursor.execute(f"SELECT * FROM LOGIN WHERE user_id = \"{username}\" and password = \"{passwd}\" and account_type = \"{type}\"")
    result = cursor.fetchall()
    if result == []:
        return gr.Info("Invalid Credentials", duration = 3)
    return gr.Info("Logged in successfully", duration = 3)


def create_account(username, passwd, type):
    cursor = conn.cursor(dictionary= True)
    cursor.execute(f"INSERT INTO LOGIN VALUES(\"{username}\", \"{passwd}\", \"{type}\"")
    
    return gr.Info("Created account", duration = 3)

with gr.Blocks() as login:
    gr.Markdown("# Login")
    login_mail = gr.Textbox(show_label= False, placeholder = "Email ID")
    login_passwd = gr.Textbox(show_label = False, placeholder = "Password", type = 'password')
    gr.Label= "Account Type"
    login_type = gr.Radio(choices = ["Host", "Attendee"], label = "Account Type", show_label = True)
    login_btn = gr.Button("Login")
    signup_menu = gr.Button("Create account", size = "sm")

    login_btn.click(fn = login_fn, inputs = [login_mail, login_passwd, login_type], outputs= gr.Info(), js="() => window.location.href = 'http://localhost:6002'")
    signup_menu.click(fn = create_account, inputs = [login_mail, login_passwd, login_type], outputs = gr.Info(), js="() => window.location.href = 'http://localhost:6003'")

login.launch(server_port=6001)