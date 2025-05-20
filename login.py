import gradio as gr
import mysql.connector as sqltor

def login_fn(username, passwd, type):
    return gr.Info("Logged in successfully", duration = 3)


def create_account(username, paswd, type):
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
    signup_menu.click(fn = create_account, inputs = [login_mail, login_passwd, login_type], outputs = gr.Info())

login.launch(server_port=6001)