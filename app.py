import streamlit as st
import pandas as pd
import datetime, os, json, sqlite3

st.set_page_config(page_title="JAWABU LEARNING CENTRE", page_icon="🏫", layout="wide")
st.markdown("""
<style>
.stApp {background: #fff0f3;}
h1,h2,h3 {color: #ff4d7a!important;}
div[data-testid="stMetric"] {background:white; border:1px solid #ffe4e9; border-radius:20px; padding:10px;}
.stButton>button {background:#ff85a1; color:white; border-radius:12px; border:none; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

FEE_STRUCTURE = {"Play Group": 5000, "PP1": 7000, "PP2": 7000, "Grade 1": 10000, "Grade 2": 10000, "Grade 3": 10000, "Grade 4": 10000, "Grade 5": 10000, "Grade 6": 10000, "Grade 7": 12000, "Grade 8": 12000, "Grade 9": 12000}
CLASSES = list(FEE_STRUCTURE.keys())
SUBJECTS_MAP = {
    "Play Group": ["Language","Mathematical","Environmental","Psychomotor & Creative","Religious"],
    "PP1": ["Language","Mathematical","Environmental","Psychomotor & Creative","Religious"],
    "PP2": ["Language","Mathematical","Environmental","Psychomotor & Creative","Religious"],
    "Grade 1": ["Mathematics","English","Kiswahili","Environmental","Creative Art","Hygiene"],
    "Grade 2": ["Mathematics","English","Kiswahili","Environmental","Creative Art","Hygiene"],
    "Grade 3": ["Mathematics","English","Kiswahili","Environmental","Creative Art","Hygiene & Nutrition"],
    "Grade 4": ["Mathematics","English","Kiswahili","Science & Tech","Social Studies","CRE","Agriculture","Creative Arts"],
    "Grade 5": ["Mathematics","English","Kiswahili","Science & Tech","Social Studies","CRE","Agriculture","Creative Arts"],
    "Grade 6": ["Mathematics","English","Kiswahili","Science & Tech","Social Studies","CRE","Agriculture","Creative Arts"],
    "Grade 7": ["Mathematics","English","Kiswahili","Integrated Science","Social Studies","CRE","Agriculture","Pre-Technical","Business"],
    "Grade 8": ["Mathematics","English","Kiswahili","Integrated Science","Social Studies","CRE","Agriculture","Pre-Technical","Business"],
    "Grade 9": ["Mathematics","English","Kiswahili","Integrated Science","Social Studies","CRE","Agriculture","Pre-Technical","Business"]
}

@st.cache_resource
def get_conn():
    return sqlite3.connect('jawabu.db', check_same_thread=False)
conn = get_conn()
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS students (reg_no TEXT PRIMARY KEY, name TEXT, parent_name TEXT, parent_phone TEXT, class TEXT, gender TEXT, dob TEXT, nemis TEXT, adm_date TEXT, fee_total INT, paid INT, balance INT, arrears INT)")
cur.execute("CREATE TABLE IF NOT EXISTS mpesa_trans (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, reg_no TEXT, mpesa_code TEXT, amount INT, phone TEXT, tuition INT, transport INT, library INT, status TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, amount INT, description TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS academics (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, term TEXT, exam_type TEXT, subjects_json TEXT, total INT, mean REAL, grade TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, active INT, created_by TEXT, created_at TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, username TEXT, role TEXT, action TEXT, details TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS school_settings (id INT PRIMARY KEY, paybill TEXT, till TEXT, account_name TEXT)")

if pd.read_sql("SELECT * FROM users", conn).empty:
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("admin","Jawabu@2026","DIRECTOR",1,"system",str(datetime.datetime.now())))
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("accountant","Acc@2026","ACCOUNTANT",1,"admin",str(datetime.datetime.now())))
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("teacher","Teach@2026","TEACHER",1,"admin",str(datetime.datetime.now())))
    conn.commit()
if pd.read_sql("SELECT * FROM school_settings", conn).empty:
    cur.execute("INSERT INTO school_settings VALUES (1,'247247','4123456','JAWABU LEARNING CENTRE')")
    conn.commit()

def log_action(username, role, action, details):
    cur.execute("INSERT INTO audit_logs (timestamp,username,role,action,details) VALUES (?,?,?,?,?)", (str(datetime.datetime.now()), username, role, action, details))
    conn.commit()

# GET SETTINGS
settings = pd.read_sql("SELECT * FROM school_settings WHERE id=1", conn).iloc[0]
PAYBILL = settings['paybill']
TILL = settings['till']

if "logged_in" not in st.session_state:
    st.session_state.logged_in=False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center'>🏫 JAWABU LEARNING CENTRE</h1>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#ffe4e9; border:2px dashed #ff85a1; padding:15px; border-radius:15px; text-align:center; margin-bottom:15px;">
        <h2 style="margin:0; color:#e91e63;">💰 LIPA NA M-PESA</h2>
        <p style="font-size:24px; font-weight:bold; margin:5px;">Paybill: {PAYBILL} | Till: {TILL}</p>
        <p style="margin:0;"><b>Account No:</b> Student Reg No e.g JLC/0001/26</p>
        <p style="font-size:12px; color:grey;">M-Pesa > Lipa na M-Pesa > Paybill > Enter {PAYBILL} > Account = Reg No</p>
    </div>
    """, unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            u=st.text_input("Username")
            p=st.text_input("Password", type="password")
            if st.button("LOGIN", use_container_width=True):
                df_user = pd.read_sql(f"SELECT * FROM users WHERE username='{u}' AND password='{p}'", conn)
                if not df_user.empty and df_user.iloc[0]['active']==1:
                    st.session_state.logged_in=True; st.session_state.username=u; st.session_state.role=df_user.iloc[0]['role']
                    log_action(u, df_user.iloc[0]['role'], "LOGIN", "Logged in"); st.rerun()
                elif not df_user.empty and df_user.iloc[0]['active']==0:
                    st.error("Account DISABLED by Director")
                else:
                    st.error("Wrong credentials")
    st.stop()

username = st.session_state.username
role = st.session_state.role
st.sidebar.markdown(f"### 🏫 JAWABU\n**User:** {username}\n**Role:** {role}")

if role=="ACCOUNTANT":
    menu_options = ["Admissions","Finance - Auto STK","Expenses","Fee Defaulters & Reports"]
elif role=="TEACHER":
    menu_options = ["Academics CBC","Report Cards"]
else:
    menu_options = ["Director Dashboard","Admissions","Finance - Auto STK","Expenses","Academics CBC","Report Cards","Fee Defaulters & Reports","School Settings","User Management","Audit Logs"]

menu = st.sidebar.radio("MENU", menu_options)
if st.sidebar.button("Logout"):
    log_action(username, role, "LOGOUT", "Logged out"); st.session_state.logged_in=False; st.rerun()

# PAGES
if menu=="Director Dashboard":
    df_exp = pd.read_sql("SELECT * FROM expenses", conn); df_mp = pd.read_sql("SELECT * FROM mpesa_trans", conn)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Collected", f"Ksh {df_mp['amount'].sum() if not df_mp.empty else 0}")
    c2.metric("Expenses", f"Ksh {df_exp['amount'].sum() if not df_exp.empty else 0}")
    c3.metric("PROFIT", f"Ksh {(df_mp['amount'].sum() if not df_mp.empty else 0)-(df_exp['amount'].sum() if not df_exp.empty else 0)}")
    c4.metric("Students", pd.read_sql("SELECT * FROM students", conn).shape[0])
    st.markdown(f"**Current Paybill:** {PAYBILL} | Till: {TILL}")
    st.dataframe(df_mp, use_container_width=True)

elif menu=="Admissions":
    st.subheader("Admissions")
    with st.form("admit"):
        c1,c2,c3=st.columns(3)
        s_name=c1.text_input("Student Name"); p_name=c2.text_input("Parent Name"); p_phone=c3.text_input("Parent Phone 2547...")
        s_class=c1.selectbox("Class", CLASSES); gender=c2.selectbox("Gender",["Male","Female"]); dob=c3.date_input("DOB")
        if st.form_submit_button("Admit"):
            fee=FEE_STRUCTURE[s_class]; cnt=pd.read_sql("SELECT * FROM students", conn).shape[0]; reg=f"JLC/{cnt+1:04d}/{datetime.date.today().year%100}"
            cur.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (reg,s_name,p_name,p_phone,s_class,gender,str(dob),"","",fee,0,fee,0)); conn.commit()
            log_action(username, role, "ADMISSION", f"Admitted {reg} {s_name}"); st.success(f"Admitted {reg}")
    st.dataframe(pd.read_sql("SELECT reg_no,name,class,parent_phone,balance FROM students", conn), use_container_width=True)

elif menu=="Finance - Auto STK":
    st.subheader("Finance - Auto Reflect Class")
    st.info(f"💰 Parents Pay via Paybill **{PAYBILL}** Account = Reg No | Till **
